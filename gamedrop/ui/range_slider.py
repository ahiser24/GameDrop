"""
Custom range slider component for selecting video clip start and end positions.
This component extends QSlider to create a dual-handle slider that allows users to:
1. Select a range within a video for clipping
2. See the selected range visually highlighted
3. Click anywhere on the timeline to seek to that position
4. Drag either handle to adjust the start or end point of the clip

The slider enforces Discord's 30-second clip limit when enabled and
uses different colors for the start (blue) and end (orange) handles
to make them easily distinguishable.
"""
from PySide6.QtWidgets import QSlider
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QColor


class RangeSlider(QSlider):
    """
    A custom slider widget with two draggable handles for selecting a video range.
    
    Features:
    - Two colored handles (blue for start, orange for end)
    - Highlighted region between handles
    - Click-to-seek functionality outside the handles
    - Automatic handle adjustment to maintain max duration when enabled
    - Precise percentage-based calculations for accurate video positioning
    
    Signals:
    - rangeChanged(start, end): Emitted when either handle moves
    - valueClicked(position): Emitted when clicking the timeline for seeking
    """

    rangeChanged = Signal(int, int)
    valueClicked = Signal(int)  # Signal for timeline clicks

    def __init__(self, orientation, parent=None):
        """
        Initialize the range slider with default settings.
        
        Args:
            orientation: Qt.Horizontal or Qt.Vertical for slider orientation
            parent: Parent widget (optional)
            
        The slider is initialized with:
        - Range from 0 to 100 (representing video position percentage)
        - Two handles at start (0%) and end (100%)
        - Tick marks below the slider for visual reference
        - Single-step increments for precise adjustments
        """
        super().__init__(orientation, parent)
        # Initialize handle positions (as percentages)
        self.lower_value = 0      # Start handle at 0%
        self.upper_value = 100    # End handle at 100%
        self.active_handle = None # Tracks which handle is being dragged
        
        # Configure slider behavior
        self.setRange(0, 100)     # Set percentage range
        self.setOrientation(orientation)
        self.setTickPosition(QSlider.TicksBelow)  # Show tick marks for visual reference
        self.setTickInterval(10)  # Place tick marks every 10%
        self.setSingleStep(1)     # Allow fine-grained 1% adjustments

    def paintEvent(self, event):
        """
        Custom paint event to draw the range slider's visual elements.
        
        This method draws three main components:
        1. Blue highlighted region between the handles
        2. Blue handle on the left (start position)
        3. Orange handle on the right (end position)
        
        The highlighting and handles help users visually identify:
        - The selected portion of the video
        - Which part of the range they're adjusting
        - The current playback position
        """
        super().paintEvent(event)
        painter = QPainter(self)
        rect = self.rect()
        handle_width = 10  # Width of the handle in pixels
        
        # Draw the blue highlighted region between the handles
        # This shows the selected portion of the video
        highlight_rect = QRect(
            int(self.lower_value / 100 * rect.width()),   # Convert percentage to pixels
            rect.y() + 4,  # Offset from top for visual appeal
            int((self.upper_value - self.lower_value) / 100 * rect.width()),  # Width based on handle positions
            rect.height() - 8  # Slightly smaller than slider for visual appeal
        )
        painter.setBrush(QColor(60, 110, 160, 100))  # Semi-transparent blue
        painter.setPen(Qt.NoPen)
        painter.drawRect(highlight_rect)
        
        # Draw handles
        lower_handle_rect = QRect(
            int(self.lower_value / 100 * rect.width()) - handle_width // 2, 
            rect.y(), 
            handle_width, 
            rect.height()
        )
        upper_handle_rect = QRect(
            int(self.upper_value / 100 * rect.width()) - handle_width // 2, 
            rect.y(), 
            handle_width, 
            rect.height()
        )
        
        # Draw lower handle
        painter.setBrush(QColor(135, 206, 235))  # Light blue
        painter.setPen(QColor(100, 100, 100))
        painter.drawRect(lower_handle_rect)
        
        # Draw upper handle
        painter.setBrush(QColor(254, 180, 123))  # Light orange
        painter.setPen(QColor(100, 100, 100))
        painter.drawRect(upper_handle_rect)

    def mousePressEvent(self, event):
        """
        Handle mouse press events for both seeking and handle dragging.
        
        This method determines what action to take when the user clicks:
        1. If clicking on or near a handle, prepare to drag that handle
        2. If clicking elsewhere on the slider, seek to that position
        
        The handle hitbox is intentionally larger than the visual handle
        to make it easier to grab and drag.
        """
        pos = event.position()
        rect = self.rect()
        handle_width = 10
        
        # Convert click position to a percentage (0-100)
        value = max(0, min(100, int(pos.x() / rect.width() * 100)))
        
        # Calculate the pixel positions of both handles
        lower_handle_x = int(self.lower_value / 100 * rect.width())
        upper_handle_x = int(self.upper_value / 100 * rect.width())
        
        # Create larger invisible regions around handles for easier interaction
        lower_handle_rect = QRect(lower_handle_x - handle_width, rect.y(), handle_width * 2, rect.height())
        upper_handle_rect = QRect(upper_handle_x - handle_width, rect.y(), handle_width * 2, rect.height())
        
        # Determine if user clicked on a handle
        if lower_handle_rect.contains(pos.toPoint()) or upper_handle_rect.contains(pos.toPoint()):
            # Select the closest handle to drag
            self.active_handle = 'lower' if abs(value - self.lower_value) <= abs(value - self.upper_value) else 'upper'
        else:
            # Click was not on a handle, so seek to the clicked position
            self.valueClicked.emit(value)
            self.update()

    def mouseMoveEvent(self, event):
        """
        Handle mouse drag events for moving the handles.
        
        This method:
        1. Updates handle positions as the user drags
        2. Enforces the 30-second limit if enabled
        3. Maintains proper ordering (start handle before end handle)
        4. Updates the video position to match the handle being dragged
        
        The positions are calculated with high precision (3 decimal places)
        to ensure accurate video clipping.
        """
        if self.active_handle is None:
            return
            
        pos = event.position()
        # Use 3 decimal places for more precise percentage calculation
        value = max(0, min(100, round(pos.x() / self.rect().width() * 100, 3)))
        
        if self.active_handle == 'lower':
            if value < self.upper_value:
                self.lower_value = value
                # Emit valueClicked to update playback position to the start handle position
                self.valueClicked.emit(self.lower_value)
        elif self.active_handle == 'upper':
            if value > self.lower_value:
                # Check if we need to maintain maximum duration (30 seconds)
                parent = self.parent()
                if hasattr(parent, 'enforce_duration_limit') and parent.enforce_duration_limit and parent.video_duration > 0:
                    # Calculate exact duration in milliseconds
                    duration_ms = round((value - self.lower_value) / 100 * parent.video_duration)
                    # Calculate exact percentage needed for 30 seconds
                    max_duration_percent = round((parent.max_clip_duration / parent.video_duration) * 100, 3)
                    
                    # If the range would exceed max duration, calculate exact lower handle position
                    if duration_ms > parent.max_clip_duration:
                        # Move lower handle to maintain exact max duration
                        self.lower_value = round(value - max_duration_percent, 3)
                        # Also update playback when lower handle is auto-moved
                        self.valueClicked.emit(self.lower_value)
                
                self.upper_value = value
                # Emit valueClicked to update playback position to the end handle position
                self.valueClicked.emit(self.upper_value)
        
        self.rangeChanged.emit(self.lower_value, self.upper_value)
        self.update()
        
    def mouseReleaseEvent(self, event):
        """
        Handle mouse release events.
        
        Simply clears the active handle state, ending any drag operation.
        The next click will start a new interaction.
        """
        self.active_handle = None