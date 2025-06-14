"""
GPU detection utilities for Game Drop

This module handles the automatic detection of graphics hardware and selects
the appropriate video encoder for optimal performance. It supports:

Hardware Types:
- NVIDIA GPUs (using NVENC hardware encoding)
- AMD GPUs (using AMF hardware encoding)
- Intel/AMD integrated graphics (using VA-API on Linux)
- Software fallback when no hardware acceleration is available

Detection Process:
1. First checks for Steam Deck hardware (uses VA-API)
2. On Windows:
   - Checks for NVIDIA using nvidia-smi tool
   - Checks for AMD using PowerShell WMI queries
   - Falls back to software encoding if no GPU detected
3. On Linux:
   - Checks for NVIDIA using nvidia-smi
   - Checks for VA-API support (Intel/AMD)
   - Falls back to software encoding if no acceleration available
"""

import platform
import subprocess
import os
import logging
import shutil
from gamedrop.platform_utils import is_windows, is_linux, is_steam_deck, has_vaapi_support

# Configure logging for GPU detection events
logger = logging.getLogger("GameDrop.GPU")

def get_subprocess_startupinfo():
    """Get startupinfo object to hide console windows on Windows"""
    if is_windows():
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo
    return None

class GPU:
    """
    GPU detection and encoder selection class.
    
    This class handles the detection of available graphics hardware and
    selects the most appropriate video encoder for the system. It automatically
    detects the GPU type and maintains the selected encoder configuration.
    
    Attributes:
        gpu_type (str): The detected GPU type, can be one of:
            - 'NVIDIA': NVIDIA GPU with NVENC support
            - 'AMD': AMD GPU with AMF support
            - 'VA-API': Intel/AMD with VA-API support on Linux
            - 'Software': No hardware acceleration available
    """
    
    def __init__(self):
        """
        Initialize GPU detection.
        
        Sets up the initial state and triggers GPU detection automatically.
        The detected GPU type will be stored in the gpu_type attribute.
        """
        self.gpu_type = None
        self.detect_gpu()
        
    def detect_gpu(self):
        """
        Detect the available GPU and set the appropriate encoder type.
        
        This method performs several checks in order:
        1. Special case for Steam Deck (uses VA-API)
        2. Platform-specific detection:
           - Windows: Checks NVIDIA, then AMD, then falls back to software
           - Linux: Checks NVIDIA, then VA-API, then falls back to software
        3. Fallback to software encoding if no hardware acceleration is found
        
        The detected GPU type is stored in self.gpu_type and logged for debugging.
        """
        try:
            if is_steam_deck():
                # Check for VA-API support on Steam Deck (it should have it)
                vaapi_device = has_vaapi_support()
                if vaapi_device:
                    self.gpu_type = 'VA-API'
                    logger.info("Steam Deck detected with VA-API support - using hardware acceleration")
                else:
                    self.gpu_type = 'Software'
                    logger.info("Steam Deck detected without VA-API support - falling back to software encoding")
                return

            if is_windows():
                startupinfo = get_subprocess_startupinfo()
                # Check for NVIDIA GPU using nvidia-smi
                try:
                    # First check if nvidia-smi exists
                    nvidia_smi_path = shutil.which('nvidia-smi')
                    if nvidia_smi_path:
                        nvidia_smi = subprocess.run(
                            [nvidia_smi_path], 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE, 
                            startupinfo=startupinfo,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        if nvidia_smi.returncode == 0:
                            self.gpu_type = 'NVIDIA'
                            logger.info("NVIDIA GPU detected")
                            return
                except FileNotFoundError:
                    pass
                except Exception as e:
                    logger.warning(f"Error checking for NVIDIA GPU: {str(e)}")

                # Check for AMD GPU using PowerShell
                try:
                    ps_cmd = "Get-WmiObject Win32_VideoController | Select-Object Name"
                    amd_check = subprocess.run(
                        ['powershell', '-Command', ps_cmd], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if amd_check.returncode == 0 and b'AMD' in amd_check.stdout.upper():
                        self.gpu_type = 'AMD'
                        logger.info("AMD GPU detected")
                        return
                except Exception as e:
                    logger.warning(f"Error checking for AMD GPU: {str(e)}")

                # Default to Intel/Software
                self.gpu_type = 'Software'
                logger.info("No dedicated GPU detected, using software encoding")

            elif is_linux():
                # Check for NVIDIA GPU
                try:
                    nvidia_smi = subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if nvidia_smi.returncode == 0:
                        self.gpu_type = 'NVIDIA'
                        logger.info("NVIDIA GPU detected")
                        return
                except FileNotFoundError:
                    pass

                # Check for VA-API support (Intel/AMD)
                if has_vaapi_support():
                    self.gpu_type = 'VA-API'
                    logger.info("VA-API support detected")
                    return

                # Default to software encoding
                self.gpu_type = 'Software'
                logger.info("No GPU acceleration detected, using software encoding")
            else:
                self.gpu_type = 'Software'
                logger.info("Unsupported platform, using software encoding")

        except Exception as e:
            logger.error(f"Error detecting GPU: {str(e)}")
            self.gpu_type = 'Software'
            logger.info("Error during GPU detection, defaulting to software encoding")

    def get_recommended_encoder(self):
        """
        Get the recommended video encoder based on detected GPU.
        
        The encoder is selected based on the detected GPU type to provide
        the best balance of performance and compatibility:
        
        Encoder Mapping:
        - NVIDIA GPUs: 'h264_nvenc' (NVIDIA's hardware encoder, best performance)
        - AMD GPUs: 'h264_amf' (AMD's hardware encoder)
        - VA-API: 'hevc_vaapi' (Linux hardware acceleration)
            * On Steam Deck: Falls back to 'h264_vaapi' for better stability
        - Software: 'h264' (CPU-based encoding, compatible everywhere)
        
        Returns:
            str: The FFmpeg encoder name to use for video processing
        """
        # Map GPU types to their optimal encoders
        encoders = {
            "NVIDIA": "h264_nvenc",  # NVIDIA's NVENC hardware encoder
            "AMD": "h264_amf",       # AMD's Advanced Media Framework encoder
            "VA-API": "hevc_vaapi",  # VA-API hardware acceleration (Linux)
            "Software": "h264"       # Software/CPU encoding (fallback)
        }
        
        # Get the recommended encoder, defaulting to h264 if GPU type is unknown
        encoder = encoders.get(self.gpu_type, "h264")
        
        # Override VA-API encoder for Steam Deck to use h264_vaapi (more stable)
        if self.gpu_type == "VA-API" and is_steam_deck():
            encoder = "h264_vaapi"
            logger.info("Steam Deck detected - using h264_vaapi instead of hevc_vaapi")
            
        logger.info(f"Using encoder: {encoder} for GPU type: {self.gpu_type}")
        return encoder