"""
Platform detection utilities for GameDrop
Handles detecting OS types and hardware capabilities
"""
import sys
import os
import subprocess
import logging
import shutil

logger = logging.getLogger("GameDrop.Platform")

def is_windows():
    """Check if running on Windows"""
    return sys.platform.startswith('win')

def is_linux():
    """Check if running on Linux"""
    return sys.platform.startswith('linux')

def is_steam_deck():
    """Detect if running on Steam Deck"""
    if not is_linux():
        return False
    
    try:
        # Check for Steam Deck identifiers
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                content = f.read().lower()
                if 'steamos' in content:
                    logger.info("Detected SteamOS")
                    return True
        
        # Alternative detection via hardware info
        if os.path.exists('/sys/class/dmi/id/product_name'):
            with open('/sys/class/dmi/id/product_name', 'r') as f:
                if 'Jupiter' in f.read():  # Steam Deck's product name
                    logger.info("Detected Steam Deck hardware")
                    return True
    except Exception as e:
        logger.error(f"Error checking for Steam Deck: {str(e)}")
    
    return False

def get_linux_distro_info():
    """Get Linux distribution information"""
    try:
        if not is_linux():
            return "Not Linux"
            
        # Try lsb_release first
        try:
            return subprocess.check_output(['lsb_release', '-ds']).decode().strip()
        except:
            # Try reading os-release
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            return line.split('=')[1].strip().strip('"\'')
            
            # Fallback
            return "Unknown Linux"
    except Exception as e:
        logger.error(f"Error getting Linux distro info: {str(e)}")
        return "Error detecting Linux distribution"

def has_vaapi_support():
    """
    Check if VA-API (Video Acceleration API) is supported on this system for hardware-accelerated video encoding/decoding.
    Returns:
        str: Path to the VAAPI device (e.g., '/dev/dri/renderD128') if supported, or False if not available.
    """
    if not is_linux():
        # VA-API is only available on Linux systems
        return False
        
    try:
        # List of possible VAAPI device files (most common is renderD128)
        vaapi_devices = [
            "/dev/dri/renderD128",
            "/dev/dri/renderD129"
        ]
        # Check if any VAAPI device exists and is accessible (read/write)
        for device in vaapi_devices:
            if os.path.exists(device) and os.access(device, os.R_OK | os.W_OK):
                logger.info(f"Found VAAPI device: {device}")
                return device
                
        # If device files not found, try using 'vainfo' tool for a deeper check
        if shutil.which("vainfo"):
            try:
                # Run 'vainfo' and look for H.264 decode/encode support in the output
                result = subprocess.check_output(["vainfo"], stderr=subprocess.STDOUT).decode()
                if "VAEntrypointVLD" in result and "VAProfileH264" in result:
                    logger.info("VAAPI encoding support detected via vainfo")
                    return "/dev/dri/renderD128"  # Default device
            except Exception:
                # Ignore errors from vainfo, just means VAAPI is not available
                pass
        # If no device or vainfo support found, return False
        return False
    except Exception as e:
        logger.error(f"Error checking for VAAPI support: {str(e)}")
        return False


def get_display_server():
    """
    Get the current display server type (X11 or Wayland) for Linux systems.
    Returns:
        str: 'Wayland', 'X11', 'Unknown', or a specific session type if detected. Returns 'Not Linux' if not on Linux.
    """
    if not is_linux():
        # Only relevant for Linux systems
        return "Not Linux"
        
    try:
        # Check for common environment variables that indicate the display server
        if "WAYLAND_DISPLAY" in os.environ:
            return "Wayland"
        if "XDG_SESSION_TYPE" in os.environ:
            # This can be 'x11', 'wayland', or other session types
            return os.environ.get('XDG_SESSION_TYPE')
        if "DISPLAY" in os.environ:
            return "X11"
        # If none of the above, unable to determine
        return "Unknown"
    except Exception:
        # If any error occurs, return a generic error string
        return "Error detecting display server"