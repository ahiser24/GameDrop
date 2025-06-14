"""
Main application controller for Game Drop
----------------------------------------
This class acts as the central hub for the Game Drop application.
It coordinates communication between the user interface (UI) and the core video processing logic.

Key responsibilities:
- Initializes and manages the main UI and core components
- Handles video loading, playback, and clipping requests
- Checks for FFmpeg availability (required for video processing)
- Emits status updates to the UI
- Logs system and environment information for debugging
"""

import os
import logging
import sys
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtWidgets import QMessageBox

# Import core components
from gamedrop.core.media_controller import MediaController  # Handles video playback and seeking
from gamedrop.core.video_processor import VideoProcessor    # Handles video clipping and compression
from gamedrop.utils.ffmpeg_wrapper import check_ffmpeg_available  # Checks for FFmpeg
from gamedrop.platform_utils import is_windows, is_linux, is_steam_deck
from gamedrop.platform_utils import get_linux_distro_info, get_display_server
from gamedrop.version import VERSION

# Setup logging for this controller
logger = logging.getLogger("GameDrop.AppController")

class GameDropController(QObject):
    """
    Main application controller that coordinates between UI and services.
    This class is responsible for connecting the UI to the backend logic.
    """
    
    # Signal to update the status bar/message in the UI
    # Args: (message: str, timeout: int in ms)
    status_updated = Signal(str, int)
    
    def __init__(self):
        """
        Initialize the controller and all core components.
        Sets up the media controller (for playback), video processor (for clipping),
        and checks for FFmpeg availability. Also logs system info for debugging.
        """
        super().__init__()
        
        # Create the media controller (handles video playback, seeking, etc.)
        self.media_controller = MediaController()
        # Create the video processor (handles clipping, compression, export)
        self.video_processor = VideoProcessor()
        # Reference to the main window (set later)
        self.main_window = None
        
        # Check if FFmpeg is available (required for all video processing)
        self.ffmpeg_available = self._check_ffmpeg()
        
        # Log system/platform information for debugging
        self._log_system_info()
    
    def set_main_window(self, main_window):
        """
        Set the main window reference and connect all signals between UI and backend.
        This ensures UI updates (like status, playback position, errors) are handled.
        """
        self.main_window = main_window
        
        # Connect status updates to the main window's status bar
        self.status_updated.connect(self.main_window.update_status)
        # Connect media controller signals to UI slots
        self.media_controller.positionChanged.connect(self.main_window.position_changed)
        self.media_controller.durationChanged.connect(self.main_window.duration_changed)
        self.media_controller.stateChanged.connect(self.main_window.media_state_changed)
        self.media_controller.statusChanged.connect(self.main_window.media_status_changed)
        self.media_controller.errorOccurred.connect(self.main_window.handle_error)
    
    def load_video(self, file_path):
        """
        Load a video file for playback and editing.
        Args:
            file_path (str): Path to the video file
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        if not file_path:
            return False
        
        try:
            logger.info(f"Loading video: {file_path}")
            self.video_path = file_path  # Store the path for later use
            self.media_controller.load_video(file_path)  # Load into playback controller
            self.status_updated.emit(f"Loading {os.path.basename(file_path)}...", 0)
            return True
        except Exception as e:
            logger.error(f"Error loading video: {str(e)}")
            self.status_updated.emit(f"Error loading video: {str(e)}", 0)
            return False
    
    def drop_video(self, start_time, end_time, output_path, webhooks=None, 
                  max_size=10*1024*1024, clip_title=None, progress_callback=None):
        """
        Process (clip and compress) the selected video segment.
        Args:
            start_time (float): Start time in seconds
            end_time (float): End time in seconds
            output_path (str): Where to save the output clip
            webhooks (list): List of Discord webhook URLs (optional)
            max_size (int): Max file size in bytes (default 10MB, Discord's current limit)
            clip_title (str): Custom clip name (optional)
            progress_callback (callable): Function to update progress bar (optional)
        Returns:
            dict: Result with 'success' and 'message' keys
        """
        if not self.ffmpeg_available:
            # If FFmpeg is missing, show an error and abort
            QMessageBox.critical(None, "Error", "FFmpeg is not available. Video clipping disabled.")
            return False
        
        try:
            # Call the video processor to create the clip
            result = self.video_processor.compress_clip(
                self.video_path, 
                start_time, 
                end_time, 
                output_path, 
                webhooks, 
                max_size, 
                clip_title, 
                progress_callback
            )
            
            if result["success"]:
                # Notify UI of success
                self.status_updated.emit("Video dropped successfully!", 5000)
                return result
            else:
                # Notify UI of failure with message
                self.status_updated.emit(result["message"], 0)
                return result
        except Exception as e:
            logger.error(f"Error dropping video: {str(e)}")
            self.status_updated.emit(f"Error: {str(e)}", 0)
            return {"success": False, "message": str(e)}
    
    def toggle_play_pause(self):
        """
        Toggle video playback between playing and paused states.
        """
        self.media_controller.toggle_play_pause()
    
    def seek_to_percentage(self, percentage):
        """
        Seek to a position in the video by percentage (0-100).
        Args:
            percentage (float): Percentage of the video duration
        """
        self.media_controller.seek_percentage(percentage)
    
    def _check_ffmpeg(self):
        """
        Check if FFmpeg is available and working.
        Returns:
            bool: True if FFmpeg is found and working, False otherwise
        """
        try:
            logger.info("Checking for FFmpeg availability...")
            if check_ffmpeg_available():
                logger.info("FFmpeg found and verified working")
                return True
            else:
                logger.warning("FFmpeg not found or not working properly")
                return False
        except Exception as e:
            logger.error(f"Error checking FFmpeg: {str(e)}")
            return False
    
    def _log_system_info(self):
        """
        Log system and environment information at startup for debugging purposes.
        This helps diagnose issues on different platforms and setups.
        """
        logger.info(f"Starting GameDrop v{VERSION}")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"OS: {os.name}")
        try:
            logger.info(f"Platform: {sys.platform}")
            if is_linux():
                logger.info(f"Linux Distribution: {get_linux_distro_info()}")
                logger.info(f"Display Server: {get_display_server()}")
                logger.info(f"Steam Deck: {is_steam_deck()}")
            logger.info(f"Working directory: {os.getcwd()}")
            logger.info(f"FFmpeg available: {self.ffmpeg_available}")
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")