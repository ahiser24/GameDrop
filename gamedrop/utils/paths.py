"""
Path and resource management utilities for the Game Drop application.

This module handles all path-related operations across different operating systems
and environments (development vs. frozen/bundled). It provides consistent path
resolution for:
- Application root directory
- Log files storage
- Resource files (assets, etc.)
- FFmpeg binaries
- User configuration files

The module automatically adjusts paths based on:
- Operating system (Windows vs. Linux)
- Runtime environment (development vs. bundled application)
- Application-specific requirements
"""

import os
import sys
import platform


def get_app_root():
    """
    Get the application's root directory based on the runtime environment.
    
    Returns:
        str: The absolute path to the application's root directory.
        
    In PyInstaller bundled mode:
        Returns the directory containing the executable.
    In development mode:
        Returns the 'gamedrop' package directory.
    """
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle - use executable's directory
        return os.path.dirname(sys.executable)
    else:
        # Running in development - use package directory
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_logs_directory():
    """
    Get the path to the logs directory, creating it if necessary.
    
    The location varies by platform and environment:
    - Linux: ~/.config/gamedrop/logs
    - Windows (bundled): %APPDATA%/GameDrop/Logs
    - Development: <app_root>/Logs
    
    Returns:
        str: The absolute path to the logs directory
    """
    if platform.system() == "Linux":
        # Use standard Linux config directory
        logs_dir = os.path.join(os.path.expanduser("~"), '.config', 'gamedrop', 'logs')
    elif getattr(sys, 'frozen', False):
        # For bundled app on other OS (e.g., Windows), use app root or user data area
        # Example for Windows (adjust as needed):
        # if platform.system() == "Windows":
        #     logs_dir = os.path.join(os.getenv('APPDATA'), 'GameDrop', 'Logs')
        # else: # Default for other frozen OS or fallback
        logs_dir = os.path.join(get_app_root(), 'Logs')
    else:
        # Development environment
        logs_dir = os.path.join(get_app_root(), 'Logs')
        
    os.makedirs(logs_dir, exist_ok=True)  # Ensure the directory exists
    return logs_dir


def resource_path(relative_path):
    """
    Get absolute path to resource files, handling both PyInstaller and development environments.
    
    This function ensures resources (like images, config files, etc.) can be accessed 
    regardless of whether the application is running from source or as a bundled executable.
    
    Args:
        relative_path (str): The relative path to the resource from the application root
    
    Returns:
        str: The absolute path to the resource
        
    Note:
        In PyInstaller mode, resources are extracted to a temporary directory (_MEIPASS)
        In development mode, resources are accessed from the application root
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        # Check if 'assets' is already in the path (for icon/logo resources)
        if relative_path.startswith('assets/'):
            # In PyInstaller builds with the updated spec, assets are at the root
            return os.path.join(base_path, relative_path)
    except AttributeError:
        base_path = get_app_root()
    
    # Don't add 'assets' here since it's already included in the calls to this function
    return os.path.join(base_path, relative_path)


def ensure_directory_exists(directory_path):
    """
    Create a directory if it doesn't exist and return its path.
    
    This is a utility function used throughout the application to ensure
    required directories are available before attempting to use them.
    
    Args:
        directory_path (str): The path to the directory to create/verify
        
    Returns:
        str: The input directory path (for method chaining)
        
    Note:
        Uses os.makedirs with exist_ok=True to prevent race conditions
    """
    os.makedirs(directory_path, exist_ok=True)
    return directory_path


def get_ffmpeg_directory():
    """
    Get the directory where FFmpeg binaries should be stored.
    
    The location varies by platform and environment:
    - Linux: ~/.config/GameDrop/ffmpeg (following XDG conventions)
    - Windows (bundled): %APPDATA%/GameDrop/ffmpeg
    - Windows (dev): <app_root>/assets/ffmpeg
    - Other OS: Alongside executable in bundled mode
    
    Returns:
        str: The absolute path to the FFmpeg binaries directory
        
    Note:
        The directory will be created if it doesn't exist
        Different paths are used to respect each OS's conventions
    """
    if platform.system() == "Linux":
        # Use standard Linux config directory for FFmpeg as well
        ffmpeg_dir = os.path.join(os.path.expanduser("~"), '.config', 'GameDrop', 'ffmpeg')
    elif getattr(sys, 'frozen', False):
        # Use AppData for installed application on Windows
        if platform.system() == "Windows":
            ffmpeg_dir = os.path.join(os.getenv('APPDATA'), 'GameDrop', 'ffmpeg')
        else: # Fallback for other frozen OS
            ffmpeg_dir = os.path.join(get_app_root(), 'ffmpeg_bin') # Store alongside executable
    else:
        # For development environment, use assets/ffmpeg folder inside gamedrop package
        ffmpeg_dir = os.path.join(get_app_root(), 'assets', 'ffmpeg')
        
    ensure_directory_exists(ffmpeg_dir) # Ensure the directory exists
    return ffmpeg_dir


def get_webhooks_path():
    """
    Get the path to the webhooks.json configuration file.
    
    The location varies by operating system:
    - Windows: Stored in the application root directory
    - Linux: Stored in the logs directory (especially important for AppImage)
    
    Returns:
        str: The absolute path to the webhooks.json file
        
    Note:
        Different locations are used to ensure file persistence
        across application updates and to follow OS conventions
    """
    import platform
    
    # On Windows, store webhooks.json in the app's root directory
    if platform.system() == "Windows":
        return os.path.join(get_app_root(), 'webhooks.json')
    # On Linux (especially AppImage), store it in the logs directory
    else:
        return os.path.join(get_logs_directory(), 'webhooks.json')