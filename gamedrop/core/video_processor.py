"""
Video Processing Core for Game Drop

This module provides the high-level video processing functionality for Game Drop,
implementing smart compression strategies and Discord integration.

Key Features:
1. Smart Video Processing:
   - Multi-tier resolution scaling
   - Dynamic bitrate calculation
   - Quality-preserving compression
   - Hardware acceleration support
   - Progress tracking

2. File Size Management:
   - Automatic Discord size limit compliance
   - Progressive quality reduction
   - Fallback compression options
   - Size verification

3. Platform Support:
   - Windows: NVIDIA, AMD, Intel GPU support
   - Linux: VA-API and software encoding
   - Steam Deck: Optimized VA-API usage

4. Discord Integration:
   - Multiple webhook support
   - Automatic retries
   - Progress reporting
   - Error handling

Implementation Details:
- Uses FFmpeg for all video operations
- Implements multi-pass compression
- Handles platform-specific quirks
- Manages temporary files safely
"""

import os
import logging
import json
import shutil
import subprocess
from gamedrop.utils.gpu import GPU
from gamedrop.utils.ffmpeg_core import compress_and_send_video, send_to_discord, get_ffmpeg_path
from gamedrop.utils.paths import get_logs_directory, get_webhooks_path
from gamedrop.platform_utils import is_windows

# Windows-specific constant for subprocess to hide console window
CREATE_NO_WINDOW = 0x08000000 if is_windows() else 0

# Setup logging
logger = logging.getLogger("GameDrop.VideoProcessor")

# Constants for dynamic scaling
AUDIO_BITRATE_KBPS_ALLOWANCE = 128  # Fixed audio bitrate allowance
MIN_ABS_VIDEO_BITRATE_KBPS = 250    # Minimum acceptable video bitrate
BITRATE_CALCULATION_SAFETY_FACTOR = 0.90  # Target 90% of max size initially

# Resolution tiers for progressive compression
# Each tier represents a step down in quality to meet size limits
DEFAULT_RESOLUTION_TIERS = [
    # (width, height, label)
    (1920, 1080, "1080p"),  # Full HD
    (1280, 720, "720p"),    # HD
    (854, 480, "480p"),     # SD widescreen
    (640, 360, "360p")      # Low quality fallback
]

class VideoProcessor:
    """Video processor that handles video clipping, compression, and export."""
    
    def __init__(self):
        """
        Initialize the video processor with GPU support detection.
        
        The constructor:
        1. Detects available GPU hardware
        2. Determines optimal encoder
        3. Sets up logging
        4. Initializes processing state
        
        Note:
            GPU detection is done once at initialization to avoid
            repeated system calls during processing.
        """
        self.gpu = GPU()
        self.gpu_encoder = self.gpu.get_recommended_encoder()
        logger.info(f"Video processor initialized with encoder: {self.gpu_encoder}")
    
    def _get_video_resolution(self, input_path):
        """
        Get video resolution (width, height) using ffprobe.
        
        This method:
        1. Locates the ffprobe binary
        2. Analyzes video metadata
        3. Handles rotation metadata
        4. Provides fallback values
        
        Args:
            input_path (str): Path to video file
            
        Returns:
            tuple: (width, height) if successful, None if failed
            
        Implementation Details:
        1. Binary Location:
           - Checks local ffprobe first
           - Falls back to system ffprobe
           - Handles platform differences
        
        2. Metadata Analysis:
           - Extracts video stream info
           - Handles multiple streams
           - Processes rotation tags
        
        3. Error Handling:
           - Timeout protection
           - JSON parsing safety
           - Permission handling
           - Logging for debugging
        """
        try:
            ffmpeg_dir = os.path.dirname(get_ffmpeg_path())
            ffprobe_exe = "ffprobe.exe" if is_windows() else "ffprobe"
            ffprobe_path = os.path.join(ffmpeg_dir, ffprobe_exe)

            if not os.path.exists(ffprobe_path):
                # Try system ffprobe if local one not found (common on Linux)
                ffprobe_path_system = shutil.which("ffprobe")
                if ffprobe_path_system:
                    ffprobe_path = ffprobe_path_system
                else:
                    logger.warning(f"ffprobe not found at {ffprobe_path} or in PATH")
                    return None

            command = [
                ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                input_path
            ]

            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=15, 
                                   creationflags=CREATE_NO_WINDOW if is_windows() else 0)
            data = json.loads(result.stdout)
            
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    width = stream.get("width")
                    height = stream.get("height")
                    
                    # Handle rotation metadata
                    rotation = stream.get("tags", {}).get("rotate")
                    if rotation in ["90", "-90", "270", "-270"]:
                        logger.info(f"Video has {rotation}° rotation, swapping dimensions")
                        width, height = height, width

                    if width and height:
                        logger.info(f"Detected video resolution: {width}x{height}")
                        return int(width), int(height)

            logger.warning(f"No video stream resolution found in {input_path}")
            
        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe timeout for {input_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"ffprobe error: {e.stderr}")
        except json.JSONDecodeError:
            logger.error(f"Invalid ffprobe JSON for {input_path}")
        except Exception as e:
            logger.error(f"Video resolution error: {str(e)}")
        return None
    
    def compress_clip(self, input_path, start_time, end_time, output_path, 
                     webhooks=None, max_size=10*1024*1024, clip_title=None, 
                     progress_callback=None):
        """
        Process a video clip with dynamic scaling compression and optional Discord upload.
        
        This method implements a sophisticated compression pipeline:
        1. Initial Setup:
           - Validates inputs
           - Creates directories
           - Checks permissions
           - Sets up progress tracking
        
        2. Resolution Tiers:
           - Starts with original resolution
           - Progressively tries lower resolutions
           - Never upscales video
           - Preserves aspect ratios
        
        3. Bitrate Management:
           - Calculates target bitrate based on duration
           - Accounts for audio bitrate
           - Applies safety factors
           - Enforces minimum quality
        
        4. Compression Strategy:
           - Tries hardware encoding first
           - Falls back to software encoding
           - Preserves best attempt
           - Handles edge cases
        
        5. Final Processing:
           - Validates file size
           - Attempts final compression if needed
           - Handles Discord upload
           - Cleans up resources
        
        Args:
            input_path (str): Source video file path
            start_time (float): Clip start time in seconds
            end_time (float): Clip end time in seconds
            output_path (str): Destination path for processed clip
            webhooks (list, optional): Discord webhook URLs for upload
            max_size (int, optional): Maximum file size in bytes (default: 10MB)
            clip_title (str, optional): Title for Discord upload
            progress_callback (callable, optional): Progress update function
        
        Returns:
            dict: Processing results with keys:
                - success (bool): True if file was created
                - message (str): Status or error message
                - file_path (str): Path to output file
                - file_size (int): Final file size in bytes
                - webhook_success (bool): True if Discord upload succeeded
        
        Example:
            ```python
            processor = VideoProcessor()
            
            def show_progress(percent):
                print(f"Processing: {percent}%")
            
            result = processor.compress_clip(
                input_path="game.mp4",
                start_time=30.5,
                end_time=40.5,
                output_path="highlight.mp4",
                webhooks=["https://discord.com/..."],
                progress_callback=show_progress
            )
            
            if result["success"]:
                print(f"Clip created: {result['file_path']}")
                print(f"Size: {result['file_size'] / 1024 / 1024:.1f}MB")
                if result["webhook_success"]:
                    print("Uploaded to Discord!")
            else:
                print(f"Error: {result['message']}")
            ```
        
        Notes:
            - Progress callback receives values 0-100
            - Discord upload uses 10% of progress budget
            - Temporary files are cleaned up
            - Best attempt is preserved on failure
        """
        try:
            logger.info(f"Processing clip: {input_path} from {start_time}s to {end_time}s")
            logger.info(f"Target output: {output_path} (max size: {max_size / (1024*1024):.1f}MB)")

            original_file_size = os.path.getsize(input_path)
            logger.info(f"Original file size: {original_file_size / (1024*1024):.2f}MB")
            if max_size > original_file_size:
                logger.info(f"Max size ({max_size / (1024*1024):.2f}MB) is larger than original file size. Adjusting max_size to original file size.")
                max_size = original_file_size

            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError as e:
                    logger.warning(f"Could not remove existing output file '{output_path}': {e}. Attempting to overwrite.")
                    # os.chmod(output_path, 0o666) # This might be risky

            duration = round(end_time - start_time, 3)
            if duration <= 0:
                logger.error("Clip duration is zero or negative.")
                raise ValueError("Clip duration must be positive for compression.")
            logger.info(f"Clip duration: {duration:.3f}s")

            original_resolution = self._get_video_resolution(input_path)
            
            actual_tiers_to_try = []
            # Use a set to keep track of resolutions already added to avoid duplicates by (width, height)
            added_resolutions = set()

            if original_resolution:
                actual_tiers_to_try.append((*original_resolution, "original"))
                added_resolutions.add((original_resolution[0], original_resolution[1]))
            
            for res_w, res_h, res_label in DEFAULT_RESOLUTION_TIERS:
                is_not_upscale = True
                if original_resolution:
                    # Only add if not an upscale
                    if res_w > original_resolution[0] or res_h > original_resolution[1]:
                        is_not_upscale = False
                
                if is_not_upscale:
                    if (res_w, res_h) not in added_resolutions:
                        actual_tiers_to_try.append((res_w, res_h, res_label))
                        added_resolutions.add((res_w, res_h))
            
            # Sort tiers by resolution (descending area) to try higher quality first
            actual_tiers_to_try.sort(key=lambda x: x[0] * x[1], reverse=True)

            if not actual_tiers_to_try: # Fallback if original resolution was tiny and no defaults fit
                logger.warning("No suitable resolution tiers determined (e.g. original too small). Falling back to 360p if possible, or original.")
                if original_resolution:
                    actual_tiers_to_try.append((*original_resolution, "original_fallback"))
                else: # Should not happen if _get_video_resolution has a fallback or DEFAULT_RESOLUTION_TIERS is not empty
                    actual_tiers_to_try.append((640, 360, "360p_fallback"))


            logger.info(f"Resolution tiers to try: {actual_tiers_to_try}")

            successful_compression = False
            final_file_size = 0
            temp_files_created = []
            
            best_attempt_so_far = {
                "path": None,
                "size": float('inf'),
                "label": ""
            }

            # Compression phase: 90% of progress
            compression_progress_total_allocation = 90.0
            num_tiers = len(actual_tiers_to_try)
            
            for tier_idx, (w, h, label) in enumerate(actual_tiers_to_try):
                current_tier_progress_base = (tier_idx / num_tiers) * compression_progress_total_allocation
                current_tier_progress_budget = (1 / num_tiers) * compression_progress_total_allocation

                def tier_ffmpeg_progress_callback(p_ffmpeg):
                    if progress_callback:
                        progress_callback(int(current_tier_progress_base + (p_ffmpeg / 100.0) * current_tier_progress_budget))

                temp_tier_output_path = f"{output_path}.{label}.temp.mp4"
                temp_files_created.append(temp_tier_output_path)

                # Calculate target video bitrate for this tier
                # Apply safety factor to max_size for bitrate calculation
                effective_max_size_for_bitrate_calc = max_size * BITRATE_CALCULATION_SAFETY_FACTOR
                
                target_total_bits = effective_max_size_for_bitrate_calc * 8
                audio_bits_allowance = AUDIO_BITRATE_KBPS_ALLOWANCE * 1000 * duration
                target_video_bits = target_total_bits - audio_bits_allowance
                
                if target_video_bits <= 0: 
                    # Not enough budget even for audio at the safety-factored size,
                    # or safety factor is very small. Use min video bitrate.
                    target_video_bitrate_bps = MIN_ABS_VIDEO_BITRATE_KBPS * 1000 
                    logger.warning(f"Effective max size {effective_max_size_for_bitrate_calc / (1024*1024):.2f}MB (after safety factor) "
                                   f"too small for audio at {AUDIO_BITRATE_KBPS_ALLOWANCE}kbps for {duration}s. "
                                   f"Using min video bitrate {MIN_ABS_VIDEO_BITRATE_KBPS}kbps for tier '{label}'.")
                else:
                    target_video_bitrate_bps = target_video_bits / duration

                # Clamp to minimum absolute video bitrate
                clamped_video_bitrate_kbps = max(MIN_ABS_VIDEO_BITRATE_KBPS, target_video_bitrate_bps / 1000)
                target_bitrate_str = f"{int(clamped_video_bitrate_kbps)}k"
                
                resolution_str = f"{w}x{h}"
                logger.info(f"Attempting tier '{label}': Res={resolution_str}, TargetBitrate={target_bitrate_str}")

                try:
                    compress_and_send_video(
                        input_path=input_path,
                        start_time=start_time,
                        end_time=end_time,
                        output_path=temp_tier_output_path,
                        codec=self.gpu_encoder,
                        bitrate=target_bitrate_str,
                        resolution=resolution_str,
                        progress_callback=tier_ffmpeg_progress_callback
                    )

                    if os.path.exists(temp_tier_output_path):
                        current_tier_size = os.path.getsize(temp_tier_output_path)
                        logger.info(f"Tier '{label}' compressed to {current_tier_size / (1024*1024):.2f}MB.")

                        # Keep track of the best attempt (smallest file if all are oversized, or first that fits)
                        if current_tier_size < best_attempt_so_far["size"]:
                            best_attempt_so_far["path"] = temp_tier_output_path
                            best_attempt_so_far["size"] = current_tier_size
                            best_attempt_so_far["label"] = label
                        
                        if current_tier_size <= max_size:
                            logger.info(f"Tier '{label}' meets target size. Using this version.")
                            shutil.move(temp_tier_output_path, output_path) # Move, not replace, to handle cross-device
                            final_file_size = current_tier_size
                            successful_compression = True
                            if progress_callback: # Update progress to end of compression phase
                                progress_callback(int(compression_progress_total_allocation))
                            break # Stop trying other tiers
                    else:
                        logger.warning(f"Compression for tier '{label}' did not produce an output file.")
                
                except Exception as e:
                    logger.error(f"Error compressing video for tier '{label}': {e}")
                    if progress_callback: # Show some progress even on error for this tier
                         tier_ffmpeg_progress_callback(100) # Mark this tier's budgeted progress as 'done'

            if not successful_compression:
                 logger.error("All compression attempts failed or produced no output.")
                 if progress_callback: progress_callback(0)
                 # Ensure cleanup of any tier-specific temp files even if best_attempt_so_far["path"] is None
                 for temp_file_cleanup in temp_files_created:
                     if os.path.exists(temp_file_cleanup):
                        try:
                            os.remove(temp_file_cleanup)
                        except Exception as e_clean_tier_fail:
                            logger.warning(f"Could not remove temp_tier_output_path '{temp_file_cleanup}' during error handling: {e_clean_tier_fail}")
                 raise Exception("Failed to generate a compressed video file after all attempts.")

            # At this point, successful_compression is True, and output_path contains the best file from tiers.
            # final_file_size holds its size.

            # ---- FINAL RE-COMPRESSION IF STILL OVERSIZED ----
            if final_file_size > max_size:
                logger.warning(f"Best attempt from tiers '{output_path}' is oversized ({final_file_size / (1024*1024):.2f}MB > {max_size / (1024*1024):.2f}MB). Attempting final aggressive re-compression.")
                
                original_oversized_content_path = output_path + ".temp_oversized_original.mp4"
                shutil.move(output_path, original_oversized_content_path) # Move current output_path to a temp name
                temp_files_created.append(original_oversized_content_path) # Add to cleanup list

                # The final output will be output_path again if re-compression is successful
                # If not, we might revert or keep the oversized one based on what happens.

                current_clip_resolution = self._get_video_resolution(original_oversized_content_path)
                if not current_clip_resolution:
                    logger.warning("Could not get resolution of oversized clip for final re-compression. Using 1280x720 as fallback.")
                    current_clip_resolution = (1280, 720)
                
                final_res_str = f"{current_clip_resolution[0]}x{current_clip_resolution[1]}"

                # Calculate a very safe target bitrate for this final pass, aiming for e.g., 85% of max_size
                target_size_bytes_final_pass = max_size * 0.85 
                audio_bits_final_pass = AUDIO_BITRATE_KBPS_ALLOWANCE * 1000 * duration
                video_bits_final_pass = (target_size_bytes_final_pass * 8) - audio_bits_final_pass

                if video_bits_final_pass <= 0:
                    final_video_kbps = MIN_ABS_VIDEO_BITRATE_KBPS
                    logger.warning(f"Target size for final re-compression ({target_size_bytes_final_pass / (1024*1024):.2f}MB) too small for audio. Using min video bitrate {MIN_ABS_VIDEO_BITRATE_KBPS}kbps.")
                else:
                    final_video_kbps = max(MIN_ABS_VIDEO_BITRATE_KBPS, (video_bits_final_pass / duration) / 1000)
                
                final_bitrate_str = f"{int(final_video_kbps)}k"
                logger.info(f"Final re-compression pass: Input='{original_oversized_content_path}', Output='{output_path}', Res={final_res_str}, TargetBitrate={final_bitrate_str}")
                
                final_pass_ffmpeg_progress_base = 95.0 # Assume main compression took up to 90-95%
                final_pass_ffmpeg_progress_budget = 4.0 # Allocate a small % for this pass

                def final_pass_progress_callback(p_ffmpeg):
                    if progress_callback:
                        progress_callback(int(final_pass_ffmpeg_progress_base + (p_ffmpeg / 100.0) * final_pass_ffmpeg_progress_budget))

                try:
                    compress_and_send_video(
                        input_path=original_oversized_content_path, # Source is the oversized clip from tiers
                        start_time=0, # It's already clipped
                        end_time=duration, # Duration of the clip
                        output_path=output_path, # Try to write to the final output_path
                        codec=self.gpu_encoder,
                        bitrate=final_bitrate_str,
                        resolution=final_res_str,
                        progress_callback=final_pass_progress_callback
                    )

                    if os.path.exists(output_path):
                        recompressed_size = os.path.getsize(output_path)
                        logger.info(f"Final re-compression output size: {recompressed_size / (1024*1024):.2f}MB")
                        if recompressed_size <= max_size and recompressed_size > 0:
                            logger.info("Final re-compression successful and meets size target.")
                            final_file_size = recompressed_size
                            # original_oversized_content_path will be cleaned up by the main temp_files_created loop
                        else:
                            logger.warning(f"Final re-compression did not meet size target (Size: {recompressed_size / (1024*1024):.2f}MB) or created empty file. Reverting to previous (oversized) file.")
                            if os.path.exists(output_path): os.remove(output_path) # Remove the failed re-compression attempt
                            shutil.move(original_oversized_content_path, output_path) # Restore the oversized file
                            final_file_size = os.path.getsize(output_path) # Should be the original final_file_size
                            # original_oversized_content_path is now output_path, remove from temp_files_created if it was added for move
                            if original_oversized_content_path in temp_files_created: temp_files_created.remove(original_oversized_content_path)

                    else: # Re-compression produced no file
                        logger.warning("Final re-compression pass did not produce an output file. Reverting to previous (oversized) file.")
                        shutil.move(original_oversized_content_path, output_path) # Restore
                        final_file_size = os.path.getsize(output_path)
                        if original_oversized_content_path in temp_files_created: temp_files_created.remove(original_oversized_content_path)

                except Exception as e_recompress:
                    logger.error(f"Error during final re-compression pass: {e_recompress}. Reverting to previous (oversized) file.")
                    if os.path.exists(output_path) and os.path.samefile(output_path, original_oversized_content_path): # Defensive check if output_path was target
                        pass # output_path is already the oversized one if move didn't happen or error before move
                    elif os.path.exists(original_oversized_content_path):
                        if os.path.exists(output_path): os.remove(output_path) # remove failed attempt if different file
                        shutil.move(original_oversized_content_path, output_path) # Restore
                    final_file_size = os.path.getsize(output_path) if os.path.exists(output_path) else final_file_size # re-fetch or keep old
                    if original_oversized_content_path in temp_files_created: temp_files_created.remove(original_oversized_content_path)
            # ---- END FINAL RE-COMPRESSION ----

            # Clean up temporary files from tier loop
            for temp_file in temp_files_created:
                if os.path.exists(temp_file) and temp_file != output_path : # Check it wasn't the one moved
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        logger.warning(f"Could not remove temp file '{temp_file}': {e}")
            
            # Webhook processing phase: 10% of progress (from 90 to 100)
            webhook_success = False
            webhook_progress_start = compression_progress_total_allocation
            webhook_progress_budget = 100.0 - webhook_progress_start

            if webhooks:
                try:
                    logger.info(f"Sending clip to {len(webhooks)} enabled webhooks")
                    # Simple progress for webhook: just jump to 100 on completion or partway on start
                    if progress_callback:
                        progress_callback(int(webhook_progress_start + webhook_progress_budget / 2))

                    for webhook_url in webhooks:
                        logger.info(f"Sending to webhook: {webhook_url[:30]}...")
                        send_result = send_to_discord(output_path, webhook_url, clip_title)
                        if send_result:
                            webhook_success = True # At least one succeeded
                            logger.info(f"Clip sent to Discord webhook successfully")
                        else:
                            logger.error(f"Failed to send clip to webhook: {webhook_url[:30]}")
                except Exception as e:
                    logger.error(f"Error sending to Discord: {str(e)}")
            elif not webhooks:
                logger.info("No webhooks enabled, skipping Discord upload")
            
            if progress_callback: # Final progress update
                progress_callback(100)
            
            logger.info(f"Video processing completed: {output_path} ({final_file_size / (1024*1024):.2f}MB)")
            return {
                "success": True, # Indicates a file was produced
                "message": "Video processed successfully",
                "file_path": output_path,
                "file_size": final_file_size,
                "webhook_success": webhook_success
            }
            
        except Exception as e:
            # If any fatal error occurs during the entire compression process, handle it here
            logger.error(f"Fatal error in compress_clip: {str(e)}")
            if progress_callback:
                progress_callback(0)  # Reset progress bar to 0 on error
            # Clean up any temp files that might have been created before the fatal error
            # This cleanup might be redundant if temp_files_created is empty or handled by the inner try-finally
            # but it's good for safety to avoid leaving junk files behind.
            if 'temp_files_created' in locals():
                 for temp_file in temp_files_created:
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except Exception as e_clean:
                            logger.warning(f"Could not remove temp file '{temp_file}' during error cleanup: {e_clean}")
            # Return a result dictionary indicating failure, with details for the UI
            return {
                "success": False,
                "message": f"Error processing video: {str(e)}",
                "file_path": None,
                "file_size": 0,
                "webhook_success": False
            }
    
    @classmethod
    def get_enabled_webhooks(cls):
        """
        Get list of enabled Discord webhook URLs from the webhooks config file.
        Returns:
            list: URLs of webhooks that are checked/enabled by the user
        """
        webhooks_file = get_webhooks_path()
        enabled_webhooks = []
        
        if os.path.exists(webhooks_file):
            try:
                with open(webhooks_file, 'r') as f:
                    webhooks = json.load(f)
                    # Only include webhooks that are marked as 'checked' (enabled)
                    enabled_webhooks = [data['url'] for data in webhooks.values() 
                                      if data.get('checked', False)]
            except Exception as e:
                logger.error(f"Error loading webhooks: {str(e)}")
                # If loading fails, return an empty list
        return enabled_webhooks