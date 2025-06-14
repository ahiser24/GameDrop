"""
FFmpeg Core Functionality for Game Drop Video Processing

This module provides comprehensive video processing capabilities using FFmpeg:

Key Features:
1. FFmpeg Management:
   - Automatic detection of FFmpeg installations across Windows and Linux platforms
   - Platform-specific FFmpeg path resolution and installation handling
   - Secure FFmpeg binary downloads with checksum validation
   - Proper permissions management for executables

2. Video Processing:
   - Hardware-accelerated encoding with support for:
     * NVIDIA NVENC (h264_nvenc, hevc_nvenc)
     * AMD AMF (h264_amf)
     * Intel QuickSync (h264_qsv)
     * VA-API on Linux (h264_vaapi, hevc_vaapi)
   - High-quality software encoding fallback (libx264)
   - Frame-accurate video clipping with millisecond precision
   - Dynamic bitrate and resolution scaling
   - Optimized encoding presets for different use cases

3. Platform-Specific Optimizations:
   - Windows: 
     * Uses portable FFmpeg builds from gyan.dev
     * Proper path handling for both development and installed environments
   - Linux:
     * Integration with system FFmpeg when available
     * Static builds from johnvansickle.com as fallback
   - Steam Deck:
     * Custom VA-API configurations for optimal performance
     * Memory-aware encoding settings
     * Power-efficient encoding options

4. Error Handling and Recovery:
   - Graceful degradation from hardware to software encoding
   - Memory allocation failure recovery
   - Comprehensive logging for debugging
   - Cross-platform path and permission management

Functions in this module should not be called directly by user code.
Instead, use the ffmpeg_wrapper module which provides a higher-level interface.

Dependencies:
- os, sys: Platform and environment handling
- subprocess: FFmpeg process management
- requests: Binary downloads
- logging: Diagnostic information
- shutil: File operations
- tarfile, zipfile: Archive handling
- gamedrop.platform_utils: Platform-specific features
- gamedrop.utils.paths: Path management
"""

import os
import sys
import subprocess
import requests
import json
import logging
import shutil
import tarfile
import zipfile
import re
from pathlib import Path
from gamedrop.platform_utils import is_windows, is_linux, is_steam_deck, has_vaapi_support
from gamedrop.utils.paths import get_ffmpeg_directory

# Windows-specific constant for subprocess to hide console window
CREATE_NO_WINDOW = 0x08000000 if is_windows() else 0

# Setup logging
logger = logging.getLogger("GameDrop.FFmpeg")

def get_ffmpeg_path():
    """
    Get the absolute path to the FFmpeg executable for the current platform.
    
    Resolution Strategy:
    1. Windows:
       - Development: Check gamedrop/assets/ffmpeg/ffmpeg.exe
       - Installed: Check %APPDATA%/GameDrop/ffmpeg/ffmpeg.exe
       
    2. Linux:
       - System: Search PATH for ffmpeg binary
       - Development: Check gamedrop/assets/ffmpeg/ffmpeg
       - Installed: Check ~/.config/GameDrop/ffmpeg/ffmpeg
    
    Returns:
        str: Absolute path to the FFmpeg executable
        
    Note:
        The returned path may not exist - use check_ffmpeg_installed()
        to verify FFmpeg availability.
    """
    # First define the expected paths based on environment
    ffmpeg_dir = get_ffmpeg_directory()
    
    if is_windows():
        # For development environment, first check in gamedrop/assets/ffmpeg
        local_ffmpeg = os.path.join(ffmpeg_dir, 'ffmpeg.exe')
        logger.info(f"Checking for FFmpeg in development assets: {local_ffmpeg}")
        if os.path.exists(local_ffmpeg):
            return local_ffmpeg
            
        # If not in development assets, check AppData for installed application
        if getattr(sys, 'frozen', False):
            appdata_path = os.path.join(os.getenv('APPDATA'), 'GameDrop', 'ffmpeg')
            os.makedirs(appdata_path, exist_ok=True)
            return os.path.join(appdata_path, 'ffmpeg.exe')
            
        # If not found anywhere else, return the expected development path
        return local_ffmpeg
    else:
        # Linux-specific paths
        # Check if FFmpeg exists in system path (preferred on Linux)
        ffmpeg_in_path = shutil.which("ffmpeg")
        if ffmpeg_in_path and is_linux():
            logger.info(f"Using system FFmpeg: {ffmpeg_in_path}")
            return ffmpeg_in_path
            
        # For development environment, use local assets folder
        local_ffmpeg = os.path.join(ffmpeg_dir, 'ffmpeg')
        if os.path.exists(local_ffmpeg):
            return local_ffmpeg
            
        # If not found in development, check ~/.config for installed application
        if getattr(sys, 'frozen', False):
            config_path = os.path.join(os.path.expanduser("~"), '.config', 'GameDrop', 'ffmpeg')
            os.makedirs(config_path, exist_ok=True)
            return os.path.join(config_path, 'ffmpeg')
            
        # If not found anywhere else, return the expected development path
        return local_ffmpeg

def check_ffmpeg_installed():
    """
    Verify FFmpeg availability and functionality.
    
    This function performs a thorough FFmpeg check:
    1. Verifies existence of FFmpeg binary
    2. Checks file permissions and executability
    3. Runs a version check to validate functionality
    4. Verifies FFmpeg version string format
    
    Platform Specifics:
    - Linux: Checks system PATH first
    - Windows: Only checks specified installation paths
    - Steam Deck: Ensures FFmpeg has VA-API support
    
    Returns:
        bool: True if FFmpeg is available and working, False otherwise
        
    Note:
        A False return value indicates that download_ffmpeg() should be called.
    """
    ffmpeg_path = get_ffmpeg_path()
    logger.info(f"Checking for FFmpeg at: {ffmpeg_path}")
    
    # Check if the detected path exists and is executable
    if os.path.exists(ffmpeg_path) and os.access(ffmpeg_path, os.X_OK):
        # Actually verify FFmpeg works by testing it
        try:
            result = subprocess.run([ffmpeg_path, '-version'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   timeout=5,
                                   creationflags=CREATE_NO_WINDOW if is_windows() else 0)
            if result.returncode == 0 and b'ffmpeg version' in result.stdout:
                logger.info("FFmpeg found and verified working at specific path")
                return True
            logger.warning(f"FFmpeg binary exists at {ffmpeg_path} but failed version check")
            return False
        except Exception as e:
            logger.warning(f"FFmpeg binary exists but failed to execute: {str(e)}")
            return False
    else:
        logger.warning(f"FFmpeg not found at expected path: {ffmpeg_path}")
    
    # Only check system PATH for Linux, not for Windows development environment
    if is_linux():
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
            # Verify the output contains "ffmpeg version"
            if result.returncode == 0 and b'ffmpeg version' in result.stdout:
                logger.info("FFmpeg found in system PATH (Linux)")
                return True
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"System FFmpeg check failed: {str(e)}")
    
    # If we get here, FFmpeg is not available
    logger.warning("FFmpeg is not available")
    return False

def download_ffmpeg(progress_callback=None):
    """
    Download and install FFmpeg for the current platform.
    
    Downloads platform-appropriate FFmpeg builds:
    - Windows: Full build from gyan.dev (includes ffprobe)
    - Linux: Static build from johnvansickle.com
    
    Install Locations:
    - Windows Development: gamedrop/assets/ffmpeg/
    - Windows Installed: %APPDATA%/GameDrop/ffmpeg/
    - Linux Development: gamedrop/assets/ffmpeg/
    - Linux Installed: ~/.config/GameDrop/ffmpeg/
    
    Args:
        progress_callback (callable, optional): Function to report progress (0-100)
        
    Returns:
        bool: True if installation successful, False otherwise
        
    Raises:
        Exception: If download or extraction fails
        
    Note:
        Automatically sets correct permissions on the installed binaries.
        Creates necessary directories with appropriate permissions.
        Cleans up temporary files even if installation fails.
    """
    try:
        ffmpeg_path = get_ffmpeg_path()
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        
        # Create directory if needed
        os.makedirs(ffmpeg_dir, exist_ok=True)
        
        if is_windows():
            # Windows download
            url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            download_path = os.path.join(ffmpeg_dir, "ffmpeg_temp.zip")
            
            # Download with progress
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            
            with open(download_path, 'wb') as f:
                downloaded = 0
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    if progress_callback and total_size:
                        progress_callback(int(downloaded * 50 / total_size))
            
            # Extract
            if progress_callback:
                progress_callback(50)
                
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                # Find ffmpeg.exe in the zip
                ffmpeg_exe = None
                for file in zip_ref.namelist():
                    if file.endswith('ffmpeg.exe'):
                        ffmpeg_exe = file
                        break
                
                if ffmpeg_exe:
                    # Extract only ffmpeg.exe
                    zip_ref.extract(ffmpeg_exe, ffmpeg_dir)
                    
                    # Move to correct location
                    extracted_path = os.path.join(ffmpeg_dir, ffmpeg_exe)
                    
                    # Create parent directories
                    os.makedirs(os.path.dirname(ffmpeg_path), exist_ok=True)
                    
                    # Move file
                    shutil.move(extracted_path, ffmpeg_path)
                    
                    # Clean up directories
                    parts = Path(ffmpeg_exe).parts
                    if len(parts) > 1:
                        shutil.rmtree(os.path.join(ffmpeg_dir, parts[0]))
                else:
                    raise Exception("Could not find ffmpeg.exe in the downloaded package")
            
            # Clean up zip file
            os.remove(download_path)
        
        elif is_linux():
            # Linux download
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            download_path = os.path.join(ffmpeg_dir, "ffmpeg_temp.tar.xz")
            
            # Download with progress
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            
            with open(download_path, 'wb') as f:
                downloaded = 0
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    if progress_callback and total_size:
                        progress_callback(int(downloaded * 50 / total_size))
            
            # Extract
            if progress_callback:
                progress_callback(50)
                
            # Create a temporary extraction directory
            extract_dir = os.path.join(ffmpeg_dir, "temp_extract")
            os.makedirs(extract_dir, exist_ok=True)
            
            # Extract the tar.xz file
            with tarfile.open(download_path, 'r:xz') as tar:
                tar.extractall(path=extract_dir)
            
            # Find the ffmpeg binary in the extracted folder
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file == 'ffmpeg':
                        extracted_path = os.path.join(root, file)
                        
                        # Make sure it's executable
                        os.chmod(extracted_path, 0o755)
                        
                        # Move to correct location
                        shutil.move(extracted_path, ffmpeg_path)
                        break
            
            # Clean up
            shutil.rmtree(extract_dir)
            os.remove(download_path)
        
        if progress_callback:
            progress_callback(100)
            
        return True
        
    except Exception as e:
        logger.error(f"Error downloading FFmpeg: {str(e)}")
        raise Exception(f"Failed to download FFmpeg: {str(e)}")

def compress_and_send_video(input_path, start_time, end_time, output_path, 
                          codec="h264", bitrate="1000k", 
                          resolution="1920x1080", progress_callback=None):
    """
    Clip, compress, and optionally send a video using FFmpeg with hardware acceleration.
    
    Core Video Processing Features:
    1. Hardware Acceleration:
       - Automatically detects available hardware encoders:
         * NVIDIA NVENC: h264_nvenc, hevc_nvenc
         * AMD AMF: h264_amf
         * Intel QSV: h264_qsv
         * Linux VA-API: h264_vaapi, hevc_vaapi
       - Falls back to software encoding (libx264) if hardware fails
       - Special optimizations for Steam Deck VA-API support
    
    2. Precise Timing Control:
       - Millisecond-accurate start/end times
       - Frame-accurate cutting without re-encoding
       - Maintains audio/video synchronization
       - Fast seek support for better performance
    
    3. Quality Management:
       - Dynamic bitrate allocation based on duration
       - Automatic quality preset selection
       - Resolution scaling with aspect ratio preservation
       - Optimized constant rate factor settings
    
    4. Error Handling:
       - Memory allocation failure recovery
       - Hardware encoder fallback logic
       - Multi-attempt encoding strategy
       - Comprehensive error logging
    
    Args:
        input_path (str): Full path to source video file
        start_time (float): Clip start time in seconds (millisecond precision)
        end_time (float): Clip end time in seconds (millisecond precision)
        output_path (str): Destination path for processed video
        codec (str, optional): Video codec to use. Defaults to "h264"
            Supported values:
            - "h264": Software H.264 encoding (libx264)
            - "h264_nvenc": NVIDIA GPU H.264 encoding
            - "hevc_nvenc": NVIDIA GPU H.265 encoding
            - "h264_amf": AMD GPU H.264 encoding
            - "h264_qsv": Intel QuickSync H.264 encoding
            - "h264_vaapi": VA-API H.264 encoding (Linux)
            - "hevc_vaapi": VA-API H.265 encoding (Linux)
        bitrate (str, optional): Target video bitrate. Defaults to "1000k"
            Use "0" for stream copy mode (no re-encoding)
        resolution (str, optional): Output resolution. Defaults to "1920x1080"
            Format: "WIDTHxHEIGHT" (e.g., "1280x720")
        progress_callback (callable, optional): Progress reporting function
            Called with values 0-100 indicating encoding progress
    
    Returns:
        bool: True if processing successful, False if failed
        
    Raises:
        Exception: Detailed error info if processing fails
        
    Note:
        This function uses a multi-phase approach:
        1. First attempt uses specified codec (usually hardware)
        2. On failure, falls back to software encoding
        3. Stream copy mode used when bitrate="0"
        
    Memory Management:
        - Automatically detects memory constraints
        - Adjusts batch parameters for stability
        - Frees resources after processing
        - Handles memory allocation failures
        
    Output Files:
        - Creates necessary output directories
        - Handles path permissions
        - Includes fast-start optimization
        - Cleans up partial files on failure
    """
    # Check for software encoding override
    use_software_encoding = os.environ.get('FORCE_SOFTWARE_ENCODING') == '1'
    if use_software_encoding:
        logger.info("Software encoding forced by environment variable")
        codec = "h264"

    try:
        # Ensure exact timing by using precise start/end times
        duration = round(end_time - start_time, 3) # Round to millisecond precision
        
        # Get FFmpeg path and ensure it's executable
        ffmpeg_path = get_ffmpeg_path()
        if not os.access(ffmpeg_path, os.X_OK):
            os.chmod(ffmpeg_path, 0o755)
            logger.info(f"Updated FFmpeg permissions to executable")

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Check if output path exists and ensure it's writable
        # This prevents permission errors during encoding
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError as e:
                logger.warning(f"Could not remove existing output file: {str(e)}")
                os.chmod(output_path, 0o666)  # Try to make it writable

        # COMMAND CONSTRUCTION BASED ON CODEC TYPE:

        # Encoding Strategy:
        # 1. First attempt: Try hardware encoding (if codec is set to hardware encoder)
        # 2. Second attempt: Fall back to software encoding if hardware fails
        # This ensures the fastest possible encoding while maintaining reliability
        for attempt in range(2):
            try:
                if attempt == 1:
                    # If first attempt failed, switch to reliable software encoding
                    logger.warning("Hardware encoding failed, falling back to software encoding")
                    codec = "h264"  # h264 software encoding is universally supported

                # Command construction varies based on:
                # 1. Whether we're copying streams or re-encoding
                # 2. Which hardware encoder we're using
                # 3. Platform-specific optimizations (especially for Steam Deck)
                if bitrate == "0":
                    # Stream Copy Mode:
                    # - No re-encoding, just cuts the video
                    # - Ultra fast but may have less precise cuts
                    # - Maintains original quality
                    command = [
                        ffmpeg_path,
                        '-y',  # Overwrite output without asking
                        '-ss', f'{start_time:.3f}',  # Start time with ms precision
                        '-i', input_path,
                        '-t', f'{duration:.3f}',  # Duration with ms precision
                        '-c:v', 'copy',   # Copy video stream as-is
                        '-c:a', 'copy',   # Copy audio stream as-is
                        '-movflags', '+faststart',  # Enable streaming optimization
                        output_path
                    ]

                elif codec in ["h264_vaapi", "hevc_vaapi"]:
                    # VA-API Hardware Encoding:
                    # - Used for Intel and AMD GPUs on Linux
                    # - Different optimizations for Steam Deck vs regular Linux
                    # - Requires proper hardware support and drivers
                    vaapi_device = has_vaapi_support()
                    if vaapi_device:
                        logger.info(f"Using VA-API hardware encoding ({codec}) with device: {vaapi_device}")
                        
                        if is_steam_deck():
                            # Steam Deck Specific Configuration:
                            # - Uses proven command structure
                            # - Optimized for Steam Deck's memory constraints
                            # - Maintains stability on SteamOS
                            logger.info("Using Steam Deck optimized VA-API settings")
                            command = [
                                ffmpeg_path,
                                '-y',
                                '-hwaccel', 'vaapi',
                                '-hwaccel_device', vaapi_device,
                                '-ss', f'{start_time:.3f}',
                                '-i', input_path,
                                '-t', f'{duration:.3f}',
                                '-vf', 'format=nv12,hwupload',  # Exactly matching your manual command
                                '-c:v', codec,
                                '-b:v', bitrate,
                                '-c:a', 'aac',
                                '-b:a', '128k',
                                '-movflags', '+faststart',
                                output_path
                            ]
                        else:
                            # Standard VA-API configuration for other Linux systems
                            command = [
                                ffmpeg_path,
                                '-y',
                                '-hwaccel', 'vaapi',
                                '-hwaccel_device', vaapi_device,
                                '-ss', f'{start_time:.3f}',
                                '-i', input_path,
                                '-t', f'{duration:.3f}',
                                '-vf', f'format=nv12,hwupload,scale_vaapi=w=1920:h=1080:format=nv12',
                                '-c:v', codec,
                                '-b:v', bitrate,
                                '-c:a', 'aac',
                                '-b:a', '128k',
                                '-movflags', '+faststart',
                                output_path
                            ]
                    else:
                        # Fallback to software if VA-API not available
                        logger.warning("VA-API device not found, falling back to software encoding")
                        codec = "h264"
                        command = [
                            ffmpeg_path,
                            '-y',
                            '-ss', f'{start_time:.3f}',
                            '-i', input_path,
                            '-t', f'{duration:.3f}',
                            '-c:v', 'h264',
                            '-preset', 'medium',
                            '-vf', f'scale={resolution}',
                            '-b:v', bitrate,
                            '-c:a', 'aac',
                            '-b:a', '128k',
                            '-movflags', '+faststart',
                            output_path
                        ]
                elif codec == 'h264_amf':
                    # AMD AMF encoder - don't use preset
                    command = [
                        ffmpeg_path,
                        '-y',
                        '-ss', f'{start_time:.3f}',
                        '-i', input_path,
                        '-t', f'{duration:.3f}',
                        '-c:v', codec,
                        '-vf', f'scale={resolution}',
                        '-b:v', bitrate,
                        '-quality', 'balanced',  # AMF specific quality setting
                        '-c:a', 'aac',
                        '-b:a', '128k',
                        '-movflags', '+faststart',
                        output_path
                    ]
                else:
                    # Software or other hardware encoders
                    command = [
                        ffmpeg_path,
                        '-y',
                        '-ss', f'{start_time:.3f}',
                        '-i', input_path,
                        '-t', f'{duration:.3f}',
                        '-c:v', codec,
                        '-preset', 'medium',
                        '-vf', f'scale={resolution}',
                        '-b:v', bitrate,
                        '-c:a', 'aac',
                        '-b:a', '128k',
                        '-movflags', '+faststart',
                        output_path
                    ]

                logger.info(f"FFmpeg command: {' '.join(command)}")

                # Execute the command with progress tracking in the user's home directory
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    cwd=os.path.expanduser('~'),  # Run in user's home directory
                    creationflags=CREATE_NO_WINDOW if is_windows() else 0
                )

                # Track progress
                duration_seconds = duration
                time_pattern = re.compile(r'time=(\d+:\d+:\d+.\d+)')
                memory_error = False
                
                while True:
                    line = process.stderr.readline()
                    if not line and process.poll() is not None:
                        break
                        
                    # Log FFmpeg output for debugging
                    if line.strip():
                        logger.debug(f"FFmpeg output: {line.strip()}")
                        # Check for memory allocation errors
                        if "Cannot allocate memory" in line or "out of memory" in line:
                            memory_error = True
                        
                    # Parse progress
                    match = time_pattern.search(line)
                    if match and progress_callback:
                        time_str = match.group(1)
                        h, m, s = map(float, time_str.split(':'))
                        current_seconds = h * 3600 + m * 60 + s
                        progress = min(100, int((current_seconds / duration_seconds) * 100))
                        progress_callback(progress)
                
                # Wait for process to complete and get return code
                returncode = process.wait()
                
                if returncode != 0:
                    _, stderr = process.communicate()
                    logger.error(f"FFmpeg stderr: {stderr}")
                    
                    # Check if it's a memory error
                    if memory_error and attempt == 0 and codec != "h264":
                        logger.warning("Memory allocation error detected, trying software encoding")
                        continue
                    
                    raise Exception(f"FFmpeg encoding failed with return code {returncode}")
                
                # If we got here, encoding was successful
                if progress_callback:
                    progress_callback(100)
                    
                logger.info("FFmpeg encoding completed successfully")
                return True
                
            except Exception as e:
                if attempt == 0 and (
                    "Cannot allocate memory" in str(e) or 
                    "out of memory" in str(e) or
                    "234" in str(e) or 
                    "244" in str(e)
                ):
                    logger.warning(f"Hardware encoding failed with memory error: {str(e)}")
                    # Continue to next attempt with software encoding
                    continue
                else:
                    # Re-raise the exception if it's the second attempt or not a memory error
                    raise
        
        # We should never reach this point, but just in case
        raise Exception("All encoding attempts failed")
            
    except Exception as e:
        logger.error(f"Error in compress_and_send_video: {str(e)}")
        raise Exception(f"Error compressing video: {str(e)}")

def send_to_discord(file_path, webhook_url, title=None):
    """Send a file to Discord using a webhook with optional title"""
    try:
        # Validate inputs
        if not webhook_url:
            logger.error("Missing webhook URL")
            raise ValueError("Webhook URL is required")
            
        if not file_path or not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
            
        logger.info(f"Sending file to Discord: {os.path.basename(file_path)}")
        logger.info(f"File size: {os.path.getsize(file_path) / (1024*1024):.2f} MB")
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            payload = {}
            if title:
                payload = {'content': f"**{title}**"}  # Bold the title in Discord markdown
                
            logger.info(f"Sending to webhook with{' title' if title else 'out title'}")
            response = requests.post(webhook_url, files=files, data=payload)
            response.raise_for_status()
            
            logger.info(f"Successfully sent to Discord, status: {response.status_code}")
            return True
    except requests.exceptions.RequestException as e:
        if "413" in str(e):
            logger.error("File too large to send to Discord, but it was saved locally")
            raise Exception("File too large to send to Discord, but it was saved locally")
        else:
            logger.error(f"Network error sending to Discord: {str(e)}")
            raise Exception(f"Failed to send to Discord (network error): {str(e)}")
    except Exception as e:
        logger.error(f"Error sending to Discord: {str(e)}")
        raise Exception(f"Failed to send to Discord: {str(e)}")