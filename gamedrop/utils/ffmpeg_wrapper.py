"""
High-Level FFmpeg Interface for Game Drop Application

This module provides a simplified interface to FFmpeg video processing operations,
abstracting away the complexity of direct FFmpeg usage. It's designed to be
the primary interface for all video operations in Game Drop.

Core Features:
1. FFmpeg Management:
   - Automatic FFmpeg detection and installation
   - Platform-specific path handling
   - Version compatibility checking
   - Binary download and update handling

2. Video Processing:
   - Simple clip extraction API
   - Smart video compression
   - Hardware acceleration support
   - Progress tracking
   - Quality preservation
   - File size control

3. Discord Integration:
   - Automatic file size validation
   - Direct webhook uploading
   - Progress reporting
   - Error handling

Usage Examples:
1. Basic FFmpeg Check:
   ```python
   if check_ffmpeg_available():
       print("FFmpeg ready to use")
   else:
       print("FFmpeg needs to be downloaded")
   ```

2. Video Compression:
   ```python
   success = compress_video(
       input_path="input.mp4",
       start_time=10.5,   # Start 10.5 seconds in
       end_time=20.5,     # End at 20.5 seconds
       output_path="output.mp4",
       codec="h264",      # Use H.264 codec
       bitrate="2000k",   # Target 2Mbps
       resolution="720p",  # Scale to 720p
       progress_callback=lambda p: print(f"{p}% complete")
   )
   ```

3. Discord Upload:
   ```python
   success = send_to_discord(
       file_path="clip.mp4",
       webhook_url="https://discord.com/api/webhooks/...",
       clip_title="My Gaming Highlight"
   )
   ```

Error Handling:
- All functions include comprehensive error reporting
- Failed operations raise descriptive exceptions
- Progress callbacks provide real-time status
- Automatic cleanup of temporary files

Notes:
- This module should be the primary interface for video operations
- Don't use ffmpeg_core directly unless absolutely necessary
- All file paths should be absolute
- Progress callbacks are optional but recommended for UI feedback
"""

import os
import sys
import logging
from gamedrop.utils.paths import get_ffmpeg_directory, ensure_directory_exists
from gamedrop.utils.ffmpeg_core import (
    check_ffmpeg_installed,
    download_ffmpeg as ffmpeg_downloader,
    compress_and_send_video,
    send_to_discord as discord_sender
)

# Setup logging
logger = logging.getLogger("GameDrop.FFmpeg")

def check_ffmpeg_available():
    """
    Check if FFmpeg is available and properly functioning.
    
    This function verifies that:
    1. FFmpeg is installed and accessible
    2. The binary has correct permissions
    3. Basic FFmpeg operations work
    
    Returns:
        bool: True if FFmpeg is ready to use, False if it needs to be installed
        
    Example:
        ```python
        if not check_ffmpeg_available():
            if not download_ffmpeg():
                print("Failed to setup FFmpeg")
        ```
    """
    try:
        return check_ffmpeg_installed()
    except Exception as e:
        logger.error(f"Error checking FFmpeg: {str(e)}")
        return False

def download_ffmpeg(progress_callback=None):
    """
    Download and install FFmpeg for the current platform.
    
    Handles the complete FFmpeg installation process:
    1. Downloads the appropriate FFmpeg build
    2. Extracts and installs the binaries
    3. Sets correct permissions
    4. Verifies the installation
    
    Args:
        progress_callback (callable, optional): Function to track download progress
            Called with an integer 0-100 indicating percent complete
    
    Returns:
        bool: True if installation succeeded, False if it failed
        
    Example:
        ```python
        def show_progress(percent):
            print(f"FFmpeg download: {percent}%")
            
        success = download_ffmpeg(progress_callback=show_progress)
        ```
        
    Notes:
        - Downloads are verified for integrity
        - Temporary files are cleaned up
        - Installation is platform-specific
    """
    try:
        # Make sure FFmpeg directory exists
        ffmpeg_dir = get_ffmpeg_directory()
        logger.info(f"Creating FFmpeg directory: {ffmpeg_dir}")
        
        # Create the directory if it doesn't exist
        os.makedirs(ffmpeg_dir, exist_ok=True)
        
        # Ensure assets directory exists too for development environment
        if ffmpeg_dir.endswith(os.path.join('assets', 'ffmpeg')):
            assets_dir = os.path.dirname(ffmpeg_dir)
            os.makedirs(assets_dir, exist_ok=True)
            logger.info(f"Created assets directory: {assets_dir}")
        
        # Download FFmpeg
        logger.info(f"Downloading FFmpeg to {ffmpeg_dir}")
        result = ffmpeg_downloader(progress_callback)
        
        if result:
            logger.info("FFmpeg download completed successfully")
        else:
            logger.error("FFmpeg download failed")
            
        return result
    except Exception as e:
        logger.error(f"Error downloading FFmpeg: {str(e)}")
        raise RuntimeError(f"Failed to download FFmpeg: {str(e)}")

def compress_video(input_path, start_time, end_time, output_path, codec="h264", 
                 bitrate="0", resolution="1920x1080", progress_callback=None):
    """
    Extract and compress a portion of a video file.
    
    This is the main video processing function that handles:
    1. Frame-accurate clip extraction
    2. Video compression with quality control
    3. Resolution scaling while preserving aspect ratio
    4. Hardware acceleration when available
    
    The function automatically:
    - Chooses optimal encoding settings
    - Handles hardware encoder fallback
    - Preserves video quality
    - Manages temporary files
    
    Args:
        input_path (str): Full path to source video
        start_time (float): Clip start time in seconds (with millisecond precision)
        end_time (float): Clip end time in seconds (with millisecond precision)
        output_path (str): Path where processed video will be saved
        codec (str, optional): Video codec to use. Defaults to "h264"
            Common values:
            - "h264": Standard H.264 encoding (software)
            - "h264_nvenc": NVIDIA GPU encoding
            - "h264_amf": AMD GPU encoding
            - "hevc_vaapi": VA-API encoding on Linux
        bitrate (str, optional): Target video bitrate. Defaults to "0"
            - "0": Copy video stream without re-encoding
            - "1000k": Target 1Mbps bitrate
            - "2M": Target 2Mbps bitrate
        resolution (str, optional): Output resolution. Defaults to "1920x1080"
            Format: "WIDTHxHEIGHT" or common names:
            - "1920x1080" or "1080p"
            - "1280x720" or "720p"
            - "854x480" or "480p"
        progress_callback (callable, optional): Progress reporting function
            Called with integer 0-100 indicating percent complete
    
    Returns:
        bool: True if processing succeeded, False if it failed
        
    Example:
        ```python
        def update_progress(percent):
            print(f"Processing: {percent}%")
            
        success = compress_video(
            input_path="game_recording.mp4",
            start_time=30.5,    # Start 30.5 seconds in
            end_time=40.5,      # End at 40.5 seconds
            output_path="highlight_clip.mp4",
            codec="h264_nvenc",  # Use NVIDIA encoding
            bitrate="2000k",     # Target 2Mbps
            resolution="720p",    # Scale to 720p
            progress_callback=update_progress
        )
        ```
        
    Notes:
        - Output directory is created if needed
        - Existing files are safely overwritten
        - Progress is reported in realtime
        - Hardware encoding is used when available
        - Falls back to software encoding if needed
    """
    try:
        return compress_and_send_video(
            input_path=input_path,
            start_time=start_time,
            end_time=end_time,
            output_path=output_path,
            codec=codec,
            bitrate=bitrate,
            resolution=resolution,
            progress_callback=progress_callback
        )
    except Exception as e:
        logger.error(f"Error compressing video: {str(e)}")
        return False

def send_to_discord(file_path, webhook_url, clip_title=None):
    """
    Upload a video file to Discord via webhook.
    
    Handles the complete Discord upload process:
    1. File size validation (max 10MB)
    2. Webhook URL validation
    3. Upload with progress tracking
    4. Error handling and retries
    
    Args:
        file_path (str): Path to the video file to upload
        webhook_url (str): Discord webhook URL for upload
        clip_title (str, optional): Title to attach to the upload
    
    Returns:
        bool: True if upload succeeded, False if it failed
        
    Example:
        ```python
        success = send_to_discord(
            file_path="game_clip.mp4",
            webhook_url="https://discord.com/api/webhooks/...",
            clip_title="Amazing Headshot!"
        )
        ```
        
    Notes:
        - Files over 10MB will fail to upload
        - Invalid webhook URLs will fail quickly
        - Network errors are handled gracefully
        - Progress is logged for debugging
    """
    try:
        logger.info(f"Preparing to send clip to Discord webhook: {file_path}")
        
        # Validate file size before sending
        if os.path.exists(file_path):
            size_mb = os.path.getsize(file_path) / (1024*1024)
            if size_mb > 10:
                logger.warning(f"File size ({size_mb:.2f} MB) exceeds Discord 10MB limit")
                return False

        # Send to Discord
        result = discord_sender(file_path, webhook_url, clip_title)
        if result:
            logger.info("Successfully sent clip to Discord")
        return result
    except Exception as e:
        logger.error(f"Error sending to Discord: {str(e)}")
        return False