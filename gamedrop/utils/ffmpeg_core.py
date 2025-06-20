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
   - 2-pass encoding for optimized quality and file size.

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


def _ffmpeg_run_pass(input_path, start_time, end_time, output_path_or_null, codec, bitrate,
                     resolution, ffmpeg_path, pass_num,
                     passlog_file, single_pass_progress_callback=None,
                     hwaccel_args=None, current_codec_for_pass=None):
    """
    Executes a single FFmpeg encoding pass.
    For pass 1, output_path_or_null should be the system's null device path.
    For pass 2 or single pass, it's the actual output file path.
    """
    original_duration = round(end_time - start_time, 3)
    if original_duration <= 0:
        original_duration = 0.001
        logger.warning(f"Calculated duration is {original_duration}, setting to 0.001 to avoid errors.")

    command = [ffmpeg_path, '-y']

    active_codec = current_codec_for_pass if current_codec_for_pass else codec

    if hwaccel_args: # Should be a list of strings
        command.extend(hwaccel_args)

    command.extend([
        '-ss', f'{start_time:.3f}',
        '-i', input_path,
        '-t', f'{original_duration:.3f}',
        '-c:v', active_codec,
    ])

    if bitrate != "0":
        command.extend(['-b:v', bitrate])
        # The -pass and -passlogfile flags are only for true 2-pass encoding
        # Don't use them for single-pass operations (pass_num == 1 and it's not the first pass of a 2-pass)
        # We can detect true 2-pass by checking if output is null device for pass 1
        is_true_two_pass = pass_num == 1 and output_path_or_null in ['NUL', '/dev/null']
        if is_true_two_pass or pass_num == 2:
            command.extend(['-pass', str(pass_num)])
            command.extend(['-passlogfile', passlog_file])


    # Video filter configuration
    vf_options = []
    existing_vf_value = None
    vf_index_in_command = -1
    for i, arg in enumerate(command): # Check if -vf is already in command (e.g. from hwaccel_args)
        if arg == '-vf' and i + 1 < len(command):
            existing_vf_value = command[i+1]
            vf_index_in_command = i + 1
            if existing_vf_value: vf_options.append(existing_vf_value)
            break

    if active_codec in ["h264_vaapi", "hevc_vaapi"]:
        # All VA-API encoders need the proper hardware upload pipeline
        if not any('format=nv12' in opt for opt in vf_options): 
            vf_options.append('format=nv12')
        if not any('hwupload' in opt for opt in vf_options): 
            vf_options.append('hwupload')
        
        if resolution: # VA-API scaling
            if is_steam_deck():
                # Steam Deck: use simpler scale_vaapi without explicit format parameter
                vf_options.append(f'scale_vaapi=w={resolution.split("x")[0]}:h={resolution.split("x")[1]}')
            else:
                # Other Linux systems: use full scale_vaapi with format
                vf_options.append(f'scale_vaapi=w={resolution.split("x")[0]}:h={resolution.split("x")[1]}:format=nv12')
    elif resolution: # Non-VAAPI scaling
        vf_options.append(f'scale={resolution}')

    if vf_options: # Apply collected vf options
        final_vf_string = ','.join(filter(None, vf_options))
        if vf_index_in_command != -1: command[vf_index_in_command] = final_vf_string # Update existing
        else: command.extend(['-vf', final_vf_string]) # Add new

    # Pass specific output and audio settings
    if pass_num == 1 and bitrate != "0" and output_path_or_null in ['NUL', '/dev/null']: # Check if it's a first pass of a 2-pass
        command.extend(['-an', '-f', 'null', output_path_or_null])
    else: # This covers pass 2 of 2-pass, single re-encode pass, or stream copy
        if bitrate != "0": # Re-encoding (pass 2 or single re-encode)
            command.extend(['-c:a', 'aac', '-b:a', '128k'])
        else: # Stream copy
            command.extend(['-c:a', 'copy'])
        command.extend(['-movflags', '+faststart', output_path_or_null]) # Actual output file for these cases

    # Preset and quality settings for re-encoding passes (bitrate != "0")
    if bitrate != "0":
        # Default preset for libx264 and other standard encoders
        if active_codec not in ['h264_amf', 'hevc_amf', 'h264_vaapi', 'hevc_vaapi', 'h264_qsv', 'hevc_qsv']:
            if '-preset' not in command: command.extend(['-preset', 'medium'])
        elif 'amf' in active_codec: # AMD AMF
            if '-quality' not in command: command.extend(['-quality', 'balanced'])
        elif 'qsv' in active_codec: # Intel QSV
            if '-preset' not in command: command.extend(['-preset', 'medium']) # QSV also uses presets
            # Consider adding QSV specific options like -look_ahead 0 if beneficial and not in hwaccel_args
        elif 'vaapi' in active_codec and is_steam_deck():
            # Steam Deck VA-API doesn't need special presets - keep it simple like original
            pass

    logger.info(f"FFmpeg Pass {pass_num} command: {' '.join(command)}")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, cwd=os.path.expanduser('~'),
        creationflags=CREATE_NO_WINDOW
    )

    time_pattern = re.compile(r'time=(\d+:\d+:\d+.\d+)')
    memory_error = False
    while True:
        line = process.stderr.readline()
        if not line and process.poll() is not None: break
        if line.strip():
            logger.debug(f"FFmpeg Pass {pass_num} output: {line.strip()}")
            if "Cannot allocate memory" in line or "out of memory" in line: memory_error = True
        match = time_pattern.search(line)
        if match and single_pass_progress_callback:
            time_str = match.group(1); parts = time_str.split(':'); h = int(parts[0]); m = int(parts[1]); s_parts = parts[2].split('.')
            s = int(s_parts[0]); ms_str = s_parts[1] if len(s_parts) > 1 else "0"; ms = int(ms_str) if ms_str.isdigit() else 0
            current_seconds = h * 3600 + m * 60 + s + ms / (10 ** len(ms_str))
            progress = min(100, int((current_seconds / original_duration) * 100)) if original_duration > 0 else (100 if current_seconds > 0 else 0)
            single_pass_progress_callback(progress)

    returncode = process.wait()
    full_stderr = process.stderr.read() if process.stderr else ""
    if returncode != 0:
        err_msg = f"FFmpeg Pass {pass_num} failed. RC: {returncode}. Stderr: {full_stderr}"
        if memory_error or "Cannot allocate memory" in full_stderr or "out of memory" in full_stderr:
            logger.error(f"Memory error in {err_msg}")
            raise Exception(f"FFmpeg Pass {pass_num} memory error. RC: {returncode}. Stderr: {full_stderr}")
        logger.error(err_msg)
        raise Exception(err_msg)
    if single_pass_progress_callback: single_pass_progress_callback(100)
    logger.info(f"FFmpeg Pass {pass_num} completed successfully.")
    return True

def get_ffmpeg_path():
    ffmpeg_dir = get_ffmpeg_directory()
    if is_windows():
        local_ffmpeg = os.path.join(ffmpeg_dir, 'ffmpeg.exe')
        if os.path.exists(local_ffmpeg): return local_ffmpeg
        if getattr(sys, 'frozen', False):
            appdata_path = os.path.join(os.getenv('APPDATA'), 'GameDrop', 'ffmpeg')
            os.makedirs(appdata_path, exist_ok=True)
            return os.path.join(appdata_path, 'ffmpeg.exe')
        return local_ffmpeg
    else: # Linux
        ffmpeg_in_path = shutil.which("ffmpeg")
        if ffmpeg_in_path and is_linux(): return ffmpeg_in_path
        local_ffmpeg = os.path.join(ffmpeg_dir, 'ffmpeg')
        if os.path.exists(local_ffmpeg): return local_ffmpeg
        if getattr(sys, 'frozen', False):
            config_path = os.path.join(os.path.expanduser("~"), '.config', 'GameDrop', 'ffmpeg')
            os.makedirs(config_path, exist_ok=True)
            return os.path.join(config_path, 'ffmpeg')
        return local_ffmpeg

def check_ffmpeg_installed():
    ffmpeg_path = get_ffmpeg_path()
    if os.path.exists(ffmpeg_path) and os.access(ffmpeg_path, os.X_OK):
        try:
            result = subprocess.run([ffmpeg_path, '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, creationflags=CREATE_NO_WINDOW)
            if result.returncode == 0 and b'ffmpeg version' in result.stdout: return True
        except Exception as e: logger.warning(f"FFmpeg at {ffmpeg_path} failed execution: {e}")
    if is_linux():
        try:
            result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            if result.returncode == 0 and b'ffmpeg version' in result.stdout: return True
        except Exception as e: logger.warning(f"System FFmpeg check failed: {e}")
    logger.warning(f"FFmpeg not available or not functional at {ffmpeg_path}.")
    return False

def download_ffmpeg(progress_callback=None):
    ffmpeg_path = get_ffmpeg_path()
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    os.makedirs(ffmpeg_dir, exist_ok=True)
    if is_windows(): url, dl_name, bin_name = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip", "ffmpeg.zip", "ffmpeg.exe"
    elif is_linux(): url, dl_name, bin_name = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz", "ffmpeg.tar.xz", "ffmpeg"
    else: raise Exception("Unsupported platform for FFmpeg download.")
    download_path = os.path.join(ffmpeg_dir, dl_name)
    try:
        r = requests.get(url, stream=True); r.raise_for_status(); total_size = int(r.headers.get('content-length',0)); downloaded_size = 0
        with open(download_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk); downloaded_size += len(chunk)
                if progress_callback and total_size: progress_callback(int(downloaded_size * 50 / total_size))
        if progress_callback: progress_callback(50)
        if dl_name.endswith(".zip"):
            with zipfile.ZipFile(download_path, 'r') as zf:
                member = next((m for m in zf.namelist() if m.endswith(f'/{bin_name}') or m == bin_name), None)
                if not member: raise Exception(f"{bin_name} not found in archive.")
                zf.extract(member, ffmpeg_dir)
                extracted_path = os.path.join(ffmpeg_dir, member)
                if ffmpeg_path != extracted_path : shutil.move(extracted_path, ffmpeg_path)
                if os.path.dirname(extracted_path) != ffmpeg_dir : shutil.rmtree(os.path.dirname(extracted_path))
        elif dl_name.endswith(".tar.xz"):
            with tarfile.open(download_path, 'r:xz') as tf:
                member = next((m for m in tf.getmembers() if m.name.endswith(f'/{bin_name}') or m.name == bin_name), None)
                if not member: raise Exception(f"{bin_name} not found in archive.")
                tf.extract(member, ffmpeg_dir) # Extracts to full path member.name
                extracted_path = os.path.join(ffmpeg_dir, member.name)
                if ffmpeg_path != extracted_path: shutil.move(extracted_path, ffmpeg_path) # Ensure it's at the target path
                if os.path.dirname(extracted_path) != ffmpeg_dir : shutil.rmtree(os.path.dirname(extracted_path))

        os.chmod(ffmpeg_path, 0o755)
        if progress_callback: progress_callback(100)
        return True
    except Exception as e: logger.error(f"FFmpeg download/extract error: {e}"); raise
    finally:
        if os.path.exists(download_path): os.remove(download_path)

def compress_and_send_video(input_path, start_time, end_time, output_path,
                          codec="h264", bitrate="1000k",
                          resolution="1920x1080", progress_callback=None):

    ffmpeg_path = get_ffmpeg_path()
    if not os.access(ffmpeg_path, os.X_OK):
        try: os.chmod(ffmpeg_path, 0o755); logger.info(f"Made FFmpeg executable: {ffmpeg_path}")
        except Exception as e: logger.error(f"Failed to make FFmpeg executable: {e}"); raise

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(output_path):
        try: os.remove(output_path)
        except OSError as e: logger.warning(f"Could not remove existing output file {output_path}: {e}")

    passlog_file = output_path + ".ffpass"

    # Initial codec and encoding properties
    is_stream_copy = bitrate == "0"

    # Determine effective codec considering FORCE_SOFTWARE_ENCODING
    force_software_env = os.environ.get('FORCE_SOFTWARE_ENCODING') == '1'
    # If VAAPI/QSV/NVENC/AMF is chosen and force_software_env is true, switch to h264.
    # Otherwise, use the chosen codec. If chosen codec is already h264, it remains h264.
    is_hw_codec = any(c in codec for c in ["vaapi", "qsv", "nvenc", "amf"])
    effective_codec = "h264" if force_software_env and is_hw_codec else codec

    if force_software_env and is_hw_codec:
        logger.info(f"Software encoding forced by environment variable. Original codec {codec} switched to {effective_codec}.")
    elif force_software_env and not is_hw_codec: # e.g. codec was already h264
         logger.info(f"Software encoding forced by environment variable. Codec {effective_codec} will be used.")

    is_vaapi_effective = "vaapi" in effective_codec

    hwaccel_params_initial = []
    if is_vaapi_effective: # Only prepare VAAPI params if effective codec is VAAPI
        vaapi_device = has_vaapi_support()
        if vaapi_device:
            if is_steam_deck():
                logger.info("Using Steam Deck optimized VA-API configuration")
                # Steam Deck needs hardware acceleration but with simpler parameters
                hwaccel_params_initial.extend(['-hwaccel', 'vaapi', '-hwaccel_device', vaapi_device])
            else:
                # For other Linux systems, use the full hwaccel setup
                hwaccel_params_initial.extend(['-hwaccel', 'vaapi', '-hwaccel_device', vaapi_device, '-hwaccel_output_format', 'vaapi'])
        else: # VAAPI was chosen/effective but not supported
            logger.warning(f"VAAPI codec {effective_codec} requested but no VAAPI device found. Switching to software h264.")
            effective_codec = "h264" # Fallback to software for this attempt
            is_vaapi_effective = False # Update effective VAAPI status
            # hwaccel_params_initial remains empty for software

    # Main encoding attempt
    try:
        # Determine if 2-pass should be used for the current effective_codec
        # Not for VAAPI, not for stream copy, and not for Steam Deck (which worked best with single-pass)
        should_use_two_pass_initial = not is_vaapi_effective and not is_stream_copy and not is_steam_deck()

        if should_use_two_pass_initial:
            logger.info(f"Attempting 2-pass encoding with codec {effective_codec}.")
            def pass1_prog_cb(p): progress_callback(int(p * 0.5)) if progress_callback else None
            null_dev = 'NUL' if is_windows() else '/dev/null'
            _ffmpeg_run_pass(input_path, start_time, end_time, null_dev,
                             effective_codec, bitrate, resolution, ffmpeg_path, 1, passlog_file,
                             pass1_prog_cb, hwaccel_params_initial, effective_codec)

            def pass2_prog_cb(p): progress_callback(int(50 + p * 0.5)) if progress_callback else None
            _ffmpeg_run_pass(input_path, start_time, end_time, output_path,
                             effective_codec, bitrate, resolution, ffmpeg_path, 2, passlog_file,
                             pass2_prog_cb, hwaccel_params_initial, effective_codec)
        else: # Single-pass (VAAPI, stream copy, or other non-2-pass codecs like potentially some HW encoders if not libx264/x265)
            logger.info(f"Attempting single-pass encoding with codec {effective_codec}.")
            _ffmpeg_run_pass(input_path, start_time, end_time, output_path,
                             effective_codec, bitrate, resolution, ffmpeg_path, 1, passlog_file, # Pass 1 signifies a complete single operation here
                             progress_callback, hwaccel_params_initial, effective_codec)

        if progress_callback: progress_callback(100)
        return True # Initial attempt successful

    except Exception as e_initial:
        logger.error(f"Initial encoding attempt with {effective_codec} failed: {e_initial}")

        # Fallback to software (libx264) if the initial attempt was not already h264 software
        if effective_codec != "h264":
            logger.warning("Falling back to software h264 encoding.")
            current_codec_for_fallback = "h264"
            # For software fallback, hwaccel_params should be empty or None
            hwaccel_params_fallback = []

            # Decide if 2-pass should be used for the software fallback
            should_use_two_pass_for_fallback = not is_stream_copy # 2-pass for s/w unless stream copy

            try:
                if os.path.exists(passlog_file): os.remove(passlog_file) # Clean before new attempt

                if should_use_two_pass_for_fallback:
                    logger.info("Attempting 2-pass software fallback encoding.")
                    def fb_p1_prog_cb(p): progress_callback(int(p*0.5)) if progress_callback else None
                    null_dev = 'NUL' if is_windows() else '/dev/null'
                    _ffmpeg_run_pass(input_path, start_time, end_time, null_dev,
                                     current_codec_for_fallback, bitrate, resolution, ffmpeg_path, 1, passlog_file,
                                     fb_p1_prog_cb, hwaccel_params_fallback, current_codec_for_fallback)

                    def fb_p2_prog_cb(p): progress_callback(int(50+p*0.5)) if progress_callback else None
                    _ffmpeg_run_pass(input_path, start_time, end_time, output_path,
                                     current_codec_for_fallback, bitrate, resolution, ffmpeg_path, 2, passlog_file,
                                     fb_p2_prog_cb, hwaccel_params_fallback, current_codec_for_fallback)
                else: # Single-pass software fallback (likely for stream copy, though unusual to reach here for stream copy fail)
                    logger.info("Attempting single-pass software fallback encoding.")
                    _ffmpeg_run_pass(input_path, start_time, end_time, output_path,
                                     current_codec_for_fallback, bitrate, resolution, ffmpeg_path, 1, passlog_file,
                                     progress_callback, hwaccel_params_fallback, current_codec_for_fallback)

                if progress_callback: progress_callback(100)
                return True # Fallback successful
            except Exception as e_fallback:
                logger.error(f"Software fallback encoding failed: {e_fallback}")
                raise Exception(f"All encoding attempts failed. Initial: {e_initial}. Fallback: {e_fallback}")
        else: # Initial attempt was already h264 software and failed
            raise e_initial # Re-raise the exception from the initial h264 attempt
    finally:
        # Clean up all ffmpeg 2-pass log files
        for ext in ["", "-0.log", "-0.log.mbtree"]:
            log_path = passlog_file + ext
            if os.path.exists(log_path):
                try:
                    os.remove(log_path)
                    logger.info(f"Cleaned up passlog file: {log_path}")
                except OSError as ex:
                    logger.warning(f"Could not delete passlog file {log_path}: {ex}")

def send_to_discord(file_path, webhook_url, title=None):
    try:
        if not webhook_url: raise ValueError("Webhook URL is required")
        if not os.path.exists(file_path): raise FileNotFoundError(f"File not found: {file_path}")
        logger.info(f"Sending {os.path.basename(file_path)} to Discord ({os.path.getsize(file_path)/(1024*1024):.2f} MB)")
        with open(file_path, 'rb') as f:
            payload = {'content': f"**{title}**"} if title else {}
            r = requests.post(webhook_url, files={'file': f}, data=payload); r.raise_for_status()
        logger.info(f"Successfully sent to Discord, status: {r.status_code}")
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 413: logger.error("File too large for Discord, saved locally."); raise Exception("File too large for Discord.")
        else: logger.error(f"HTTP error sending to Discord: {e}"); raise Exception(f"Failed to send (HTTP {e.response.status_code}): {e}")
    except Exception as e: logger.error(f"Error sending to Discord: {e}"); raise Exception(f"Failed to send: {e}")
