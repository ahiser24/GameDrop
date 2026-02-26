"""
Media controller for handling video playback
------------------------------------------
This class manages all video playback functionality in Game Drop.
It wraps around QMediaPlayer and QAudioOutput to provide a simple interface
for loading, playing, pausing, seeking, and monitoring video files.

Key responsibilities:
- Load video files for playback
- Control play/pause and seeking
- Forward playback state, position, and error signals to the UI
- Format time for display
"""

import logging
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

# Setup logging for this controller
logger = logging.getLogger("GameDrop.MediaController")

class MediaController(QObject):
    """
    Media controller that handles video playback functionality.
    This class acts as a bridge between the UI and the underlying Qt media player.
    """
    
    # Signals that notify the UI of playback changes or errors
    positionChanged = Signal(int)      # Emitted when playback position changes (ms)
    durationChanged = Signal(int)      # Emitted when media duration changes (ms)
    stateChanged = Signal(object)      # Emitted when play/pause/stop state changes
    statusChanged = Signal(object)     # Emitted when media status changes (loading, loaded, etc.)
    errorOccurred = Signal(str)        # Emitted when an error occurs (error message)
    
    def __init__(self):
        """
        Initialize the media controller.
        Media player creation is deferred to avoid PipeWire hangs on Linux.
        """
        super().__init__()
        
        # Defer these to avoid PipeWire timeout during app init
        self.media_player = None
        self.audio_output = None
        self.video_output = None
        self._initialized = False
        
        logger.info("Media controller created (media player deferred)")
    
    def _ensure_initialized(self):
        """
        Lazily initialize the Qt media components.
        This defers PipeWire/audio system initialization until actually needed.
        """
        if self._initialized:
            return
            
        logger.info("Initializing media player...")
        
        # Create the Qt media player (handles video playback)
        self.media_player = QMediaPlayer()
        # Create the audio output (for controlling volume)
        self.audio_output = QAudioOutput()
        
        # Configure audio output (set to full volume by default)
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        
        # Connect QMediaPlayer signals to internal handlers
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.media_player.errorOccurred.connect(self._on_error)
        
        # Set video output if it was configured before initialization
        if self.video_output:
            self.media_player.setVideoOutput(self.video_output)
        
        self._initialized = True
        logger.info("Media controller fully initialized")
    
    def set_video_output(self, video_widget):
        """
        Set the video widget (QVideoWidget) where video will be displayed.
        Args:
            video_widget: The widget to use for video output
        """
        self.video_output = video_widget
        if self._initialized and self.media_player:
            self.media_player.setVideoOutput(video_widget)
        logger.debug("Video output set")
    
    def load_video(self, file_path):
        """
        Load a video file into the media player for playback.
        Args:
            file_path (str): Path to the video file
        """
        self._ensure_initialized()
        try:
            url = QUrl.fromLocalFile(file_path)
            logger.info(f"Attempting to set media source with URL: {url.toString()}")
            self.media_player.setSource(url)
            
            # Re-apply video output after setting source to ensure display works
            if self.video_output:
                self.media_player.setVideoOutput(self.video_output)
                logger.debug("Video output re-applied after source set")
            
            # Start playback briefly and pause to show first frame
            # This is needed because QVideoWidget won't show anything until frames are decoded
            self.media_player.play()
            self.media_player.pause()
            self.media_player.setPosition(0)
            logger.debug("Video positioned at start and paused")
            
            logger.info(f"Media source set: {file_path}")
        except Exception as e:
            logger.error(f"Error loading video: {str(e)}")
            self.errorOccurred.emit(f"Error loading video: {str(e)}")
    
    def toggle_play_pause(self):
        """
        Toggle between play and pause states.
        If currently playing, pause. If paused or stopped, start playing.
        """
        self._ensure_initialized()
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            logger.debug("Playback paused")
        else:
            self.media_player.play()
            logger.debug("Playback started")
    
    def seek_percentage(self, percentage):
        """
        Seek to a position in the video by percentage (0-100).
        Args:
            percentage (float): Percentage of the video duration to seek to
        """
        self._ensure_initialized()
        if not 0 <= percentage <= 100:
            logger.warning(f"Invalid seek percentage: {percentage}")
            return
        
        duration = self.media_player.duration()
        if duration > 0:
            position = int(duration * percentage / 100)
            self.media_player.setPosition(position)
            logger.debug(f"Seek to position: {position} ms ({percentage}%)")
    
    def get_position(self):
        """
        Get the current playback position in milliseconds.
        Returns:
            int: Current position in ms
        """
        if not self._initialized:
            return 0
        return self.media_player.position()
    
    def get_duration(self):
        """
        Get the total duration of the loaded media in milliseconds.
        Returns:
            int: Duration in ms
        """
        if not self._initialized:
            return 0
        return self.media_player.duration()
    
    def format_time(self, milliseconds):
        """
        Convert a time in milliseconds to a string in HH:MM:SS format.
        Args:
            milliseconds (int): Time in milliseconds
        Returns:
            str: Formatted time string
        """
        seconds = milliseconds / 1000
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    # --- Internal signal handlers ---
    def _on_position_changed(self, position):
        """
        Handle position changed events from QMediaPlayer.
        Forwards the new position to the UI.
        """
        self.positionChanged.emit(position)
    
    def _on_duration_changed(self, duration):
        """
        Handle duration changed events from QMediaPlayer.
        Forwards the new duration to the UI.
        """
        self.durationChanged.emit(duration)
    
    def _on_playback_state_changed(self, state):
        """
        Handle playback state changed events from QMediaPlayer.
        Forwards the new state to the UI.
        """
        self.stateChanged.emit(state)
    
    def _on_media_status_changed(self, status):
        """
        Handle media status changed events from QMediaPlayer.
        Forwards the new status to the UI.
        """
        self.statusChanged.emit(status)
    
    def _on_error(self, error, error_string):
        """
        Handle error events from QMediaPlayer.
        Logs the error and notifies the UI.
        """
        logger.error(f"Media player error: {error} - {error_string}")
        self.errorOccurred.emit(error_string)