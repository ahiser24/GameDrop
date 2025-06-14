"""
Main window for the Game Drop application.
"""

import sys
import os
import logging
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QProgressBar, QCheckBox,
    QSizePolicy, QComboBox, QLineEdit, QDialog
)
from PySide6.QtCore import Qt, QTimer, QUrl, Signal, Slot, QSize, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter # QPainter re-added
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtMultimediaWidgets import QVideoWidget

from gamedrop.ui.range_slider import RangeSlider
from gamedrop.ui.dialogs import WebhookDialog, LogViewerDialog, FFmpegDownloadDialog
from gamedrop.utils.ffmpeg_wrapper import download_ffmpeg
from gamedrop.utils.paths import resource_path, get_logs_directory, get_webhooks_path
from gamedrop.platform_utils import is_windows, is_linux, is_steam_deck
from gamedrop.version import VERSION

# Configure logging
logger = logging.getLogger("GameDrop.MainWindow")

# Constants
WEBHOOKS_FILE = get_webhooks_path()

class MainWindow(QWidget):
    """
    Main application window for Game Drop with video playback and clipping controls.
    """
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.logger = logging.getLogger("GameDrop.MainWindow")
        
        # Initialize UI variables
        self.video_path = None
        self.video_duration = 0  # in milliseconds
        self.max_clip_duration = 30000  # 30 seconds in milliseconds
        self.is_media_loaded = False
        self.enforce_duration_limit = True
        self.detected_gpu = self.controller.video_processor.gpu.gpu_type
        
        self.init_ui()
        
        # Check FFmpeg and show download dialog if needed
        if not self.controller.ffmpeg_available:
            QTimer.singleShot(500, self.show_ffmpeg_download_dialog)

    def init_ui(self):
        """Initialize the user interface"""
        # Main layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(12)

        # Set window properties
        self.setWindowTitle(f"Game Drop v{VERSION}")

        # Create a square pixmap with the logo rendered with aspect ratio preservation
        icon_size = 32  # Standard icon size
        svg_path = resource_path('assets/logo.svg')

        renderer = QSvgRenderer(svg_path)
        if not renderer.isValid():
            self.logger.error(f"Failed to load SVG for window icon: {svg_path}")
            # Fallback to original method if renderer is invalid, though it will still be squished
            app_icon = QIcon(svg_path)
        else:
            renderer.setAspectRatioMode(Qt.KeepAspectRatio)

            icon_pixmap = QPixmap(icon_size, icon_size)
            icon_pixmap.fill(Qt.transparent)  # Fill with transparency

            painter = QPainter(icon_pixmap)
            renderer.render(painter, QRectF(icon_pixmap.rect()))
            painter.end()

            app_icon = QIcon(icon_pixmap)

        # Set the window icon using the processed icon
        self.setWindowIcon(app_icon)
        # Adjust initial size and set a minimum size for better scaling
        self.setGeometry(50, 50, 800, 600)  # Smaller default size
        # Increase minimum window size to prevent UI elements from overlapping
        self.setMinimumSize(640, 580) # Set a larger minimum height to prevent overlap

        # Top header with logo and GPU info
        header_layout = QHBoxLayout()
        
        # Logo
        svg_path = resource_path('assets/logo.svg')
        self.logo_widget = QSvgWidget() # Create QSvgWidget instance
        
        # Need a temporary renderer to get aspect ratio correctly before loading into widget
        temp_renderer = QSvgRenderer(svg_path)

        if temp_renderer.isValid():
            default_size = temp_renderer.defaultSize()
            target_height = 40
            
            if default_size.height() > 0:
                aspect_ratio = default_size.width() / default_size.height()
                target_width = int(target_height * aspect_ratio)
            else: # Fallback if default size is invalid
                target_width = 60 # A default width
                # target_height is already 40

            self.logo_widget.setFixedSize(QSize(target_width, target_height))
            self.logo_widget.load(svg_path) # Load SVG into the widget
        else:
            # Fallback: if SVG fails to load or is invalid.
            self.logger.error(f"Failed to load SVG for QSvgWidget: {svg_path}. Widget will be empty or hidden.")
            self.logo_widget.setVisible(False) 
        
        # App title with version
        title_label = QLabel(f"Game Drop")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #d3d3d3;")
        
        header_layout.addWidget(self.logo_widget)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        
        # Add GPU info label
        gpu_info = f"GPU: {self.detected_gpu}"
        gpu_label = QLabel(gpu_info)
        gpu_label.setStyleSheet("color: #8a8a8a; font-size: 12px;")
        header_layout.addWidget(gpu_label)
        
        self.layout.addLayout(header_layout)

        # Create a black container for the video widget
        self.video_container = QWidget()
        self.video_container.setObjectName("videoContainer")
        self.video_container.setStyleSheet("background-color: black; border: none;")
        self.video_container.setAutoFillBackground(True)
        
        # Create layout for the video container with zero margins
        video_container_layout = QVBoxLayout(self.video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)
        video_container_layout.setSpacing(0)
        
        # Create video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(256, 144)
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        self.video_widget.setAttribute(Qt.WA_OpaquePaintEvent)
        self.video_widget.setStyleSheet("background: black; border: none; padding: 10; margin: 0;")
        
        # Set up media controller with video output
        self.controller.media_controller.set_video_output(self.video_widget)
        
        # Add video widget to the container
        video_container_layout.addWidget(self.video_widget)
        
        # Set a more appropriate minimum height that will prevent overlap with slider
        # but still allow reasonable scaling
        self.video_container.setMinimumHeight(150)  # Ensure video container doesn't shrink too much
        
        # Use a different size policy that will force the video container to shrink first
        # when window is resized, protecting the UI controls below it
        self.video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.layout.addWidget(self.video_container)

        # Time indicator and slider
        time_layout = QHBoxLayout()
        
        # Create a container for time controls to ensure they have a minimum height
        time_controls_container = QWidget()
        time_controls_container.setMinimumHeight(50)  # Ensure time controls remain visible
        time_controls_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Make sure this container cannot be overlapped/hidden
        time_controls_container.setMinimumSize(200, 50)
        
        # Use the container's layout
        time_controls_layout = QHBoxLayout(time_controls_container)
        time_controls_layout.setContentsMargins(0, 8, 0, 8)  # Add some vertical padding
        
        # Current time / Total time
        self.time_label = QLabel('00:00:00 / 00:00:00')
        self.time_label.setStyleSheet("font-family: monospace;")
        time_controls_layout.addWidget(self.time_label)
        
        # Range slider
        self.range_slider = RangeSlider(Qt.Horizontal)
        self.range_slider.setMinimumHeight(24)
        self.range_slider.rangeChanged.connect(self.update_range)
        self.range_slider.valueClicked.connect(self.seek_to_time)
        # Give it a higher z-order to make sure it stays on top
        self.range_slider.raise_()
        time_controls_layout.addWidget(self.range_slider, 1)
        
        # Add the container to the main layout
        self.layout.addWidget(time_controls_container)

        # Define Video Options Widgets
        self.duration_limit_checkbox = QCheckBox("Optimize for Discord (30s / 10MB)")
        self.duration_limit_checkbox.setChecked(True)
        self.duration_limit_checkbox.stateChanged.connect(self.toggle_duration_limit)

        self.filesize_container = QWidget()
        filesize_layout = QHBoxLayout(self.filesize_container)
        filesize_layout.setContentsMargins(0,0,0,0)
        filesize_layout.setSpacing(10)  # Add spacing between elements
        filesize_label = QLabel("Max Filesize:")
        filesize_label.setMinimumWidth(100)  # Ensure label has minimum width
        self.filesize_combo = QComboBox()
        self.filesize_combo.addItems(["10 MB", "25 MB", "50 MB", "100 MB", "500 MB", "Custom..."])
        self.filesize_combo.setCurrentIndex(0)
        self.filesize_combo.setMinimumWidth(120)  # Ensure combo box has minimum width
        self.filesize_combo.setEnabled(False) # Disabled by default
        # Connection for filesize_combo.currentIndexChanged is already at the end of init_ui
        filesize_layout.addWidget(filesize_label)
        filesize_layout.addWidget(self.filesize_combo)
        self.filesize_container.setMinimumHeight(30)  # Set minimum height
        self.filesize_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.custom_filesize_container = QWidget()
        custom_filesize_layout = QHBoxLayout(self.custom_filesize_container)
        custom_filesize_layout.setContentsMargins(0,0,0,0)
        custom_filesize_layout.setSpacing(10)  # Add spacing between elements
        custom_filesize_label = QLabel("Custom Size (MB):")
        custom_filesize_label.setMinimumWidth(120)  # Ensure label has minimum width
        self.custom_filesize_input = QLineEdit()
        self.custom_filesize_input.setPlaceholderText("e.g., 10")
        self.custom_filesize_input.setMinimumWidth(120)  # Ensure input has minimum width
        self.custom_filesize_input.setEnabled(False) # Disabled by default
        custom_filesize_layout.addWidget(custom_filesize_label)
        custom_filesize_layout.addWidget(self.custom_filesize_input)
        self.custom_filesize_container.setMinimumHeight(30)  # Set minimum height
        self.custom_filesize_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.custom_filesize_container.setVisible(False)

        self.clip_name_container = QWidget()
        clip_name_layout = QHBoxLayout(self.clip_name_container)
        clip_name_layout.setContentsMargins(0,0,0,0)
        clip_name_layout.setSpacing(10)  # Add spacing between elements
        clip_name_label = QLabel("Clip name (optional):")
        clip_name_label.setMinimumWidth(120)  # Ensure label has minimum width
        self.clip_name_input = QLineEdit()
        self.clip_name_input.setPlaceholderText("Defaults to Filename_clip")
        self.clip_name_input.setMinimumWidth(200)  # Ensure input has minimum width
        clip_name_layout.addWidget(clip_name_label)
        clip_name_layout.addWidget(self.clip_name_input)
        self.clip_name_container.setMinimumHeight(30)  # Set minimum height
        self.clip_name_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.clip_name_container.setVisible(True)  # Initially hidden, will show when duration limit is disabled

        self.duration_warning_label = QLabel("⚠️ Longer clips may have reduced quality.")
        self.duration_warning_label.setStyleSheet("color: #FFA500; font-style: italic;")
        self.duration_warning_label.setMinimumHeight(24)  # Ensure minimum height
        self.duration_warning_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Prevent vertical shrinking
        self.duration_warning_label.hide()

        # Video options layout
        video_layout = QVBoxLayout()
        
        # ----------------------------------------------------------------------
        # VIDEO OPTIONS SECTION
        # ----------------------------------------------------------------------
        # This section contains all widgets that let the user control how video
        # clips are created and saved. These options are grouped together for
        # clarity and easy access. Each widget is described below:
        #
        # 1. self.duration_limit_checkbox:
        #    - Checkbox to enforce Discord's 30s/10MB clip limit.
        #    - When checked, clips are always 30 seconds and <= 10MB.
        #    - When unchecked, user can set custom duration and file size.
        # 2. self.filesize_container:
        #    - Dropdown to select the maximum allowed file size for the clip.
        #    - Only visible if duration limit is OFF.
        # 3. self.custom_filesize_container:
        #    - Input box for a custom file size (in MB).
        #    - Only visible if "Custom..." is selected in the dropdown.
        # 4. self.clip_name_container:
        #    - Input box for a custom clip name (optional).
        # 5. self.duration_warning_label:
        #    - Warning label shown if duration limit is OFF, reminding the user
        #      that longer clips may have reduced quality.
        #
        # The widgets are added to the layout in the order above, with spacing
        # for readability. DO NOT add any "Drop It" button or unrelated controls
        # here—those are handled in a separate section below.
        # ----------------------------------------------------------------------
        video_layout.addWidget(self.duration_limit_checkbox)  # 1. Enforce 30s/10MB checkbox
        video_layout.addSpacing(5)  # Space between checkbox and file size options
        video_layout.addWidget(self.filesize_container)       # 2. File size dropdown
        video_layout.addWidget(self.custom_filesize_container) # 3. Custom file size input
        video_layout.addWidget(self.clip_name_container)      # 4. Custom clip name input
        video_layout.addSpacing(5)  # Space before warning label
        # video_layout.addWidget(self.duration_warning_label)   # 5. Quality warning label - REMOVED FROM HERE
        
        self.layout.addLayout(video_layout) # Add Video options section to the main layout FIRST.

        # ----------------------------------------------------------------------
        # CENTERED CONTROLS ROW (Play, Load Video, Manage Webhooks)
        # ----------------------------------------------------------------------
        # This row contains the main video control buttons, centered horizontally:
        #   - Play/Pause: Toggles video playback (disabled until a video is loaded)
        #   - Load Video: Opens a file dialog to select a video file
        #   - Manage Webhooks: Opens a dialog to manage Discord webhooks
        #
        # ----------------------------------------------------------------------
        centered_controls_layout = QHBoxLayout()
        centered_controls_layout.setAlignment(Qt.AlignHCenter)
        self.play_pause_button = QPushButton('Play')
        self.play_pause_button.setEnabled(False)
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        centered_controls_layout.addWidget(self.play_pause_button)
        self.load_button = QPushButton('Load Video')
        self.load_button.clicked.connect(self.load_video)
        centered_controls_layout.addWidget(self.load_button)
        self.webhook_button = QPushButton('Manage Webhooks')
        self.webhook_button.clicked.connect(self.show_webhook_dialog)
        centered_controls_layout.addWidget(self.webhook_button)
        self.layout.addLayout(centered_controls_layout) # Add this controls row SECOND.

        # ----------------------------------------------------------------------
        # CENTERED "DROP IT" BUTTON ROW
        # ----------------------------------------------------------------------
        # This is the ONLY place where the "Drop It" button is defined and added.
        # It is centered and placed below the main controls for clear separation.
        # The button is disabled until a video is loaded and a valid range is set.
        # ----------------------------------------------------------------------
        drop_button_layout = QHBoxLayout()
        drop_button_layout.setAlignment(Qt.AlignHCenter)
        self.drop_button = QPushButton('Drop It') # Define and configure the one true self.drop_button here.
        self.drop_button.setEnabled(False)
        self.drop_button.clicked.connect(self.drop_video)
        drop_button_layout.addWidget(self.drop_button)
        self.layout.addLayout(drop_button_layout) # Add the Drop It button row THIRD.

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        self.layout.addWidget(self.progress_bar)

        # Status layout with log button
        status_layout = QHBoxLayout()
        
        # Status label
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("color: #8a8a8a;")
        status_layout.addWidget(self.status_label) # Let it take available space on left initially

        # Add duration warning label (initially hidden)
        # self.duration_warning_label is already created and styled
        self.duration_warning_label.setAlignment(Qt.AlignCenter) # Attempt to center its text
        status_layout.addWidget(self.duration_warning_label, 1) # Add with stretch factor to push others
        
        # Add log button
        self.log_button = QPushButton('View Logs')
        self.log_button.setFixedWidth(100)
        self.log_button.clicked.connect(self.view_logs)
        status_layout.addWidget(self.log_button)
        
        self.layout.addLayout(status_layout)

        self.setLayout(self.layout)

        # Apply custom styles
        self.apply_styles()
        
        # Connect custom file size option
        self.filesize_combo.currentIndexChanged.connect(self.handle_filesize_option)
        # self.clip_name_input.textChanged.connect(self.handle_clip_name_input) # Connect if specific logic is needed

    def apply_styles(self):
        """Apply custom styling to the application"""
        self.setStyleSheet("""        
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #5d5d5d;
            }
            QPushButton:pressed {
                background-color: #4d4d4d;
            }
            QPushButton:disabled {
                background-color: #1d1d1d;
                color: #5d5d5d;
                border: 1px solid #3d3d3d;
            }
            QLabel {
                padding: 4px;
                color: #e0e0e0;
            }
            QSlider::groove:horizontal {
                border: 1px solid #4d4d4d;
                height: 8px;
                background: #2d2d2d;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #5d5d5d;
                border: 1px solid #6d6d6d;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QProgressBar {
                border: 1px solid #4d4d4d;
                border-radius: 4px;
                background: #2d2d2d;
                text-align: center;
                padding: 2px;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3d85c6;
                border-radius: 3px;
            }
            QVideoWidget, QGraphicsView {
                background: none !important;
                border: none !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                color: #e0e0e0;
            }
            QLineEdit:disabled {
                background-color: #282828; /* Slightly different or same as enabled for dark theme */
                color: #6a6a6a;           /* Greyed-out text */
                border: 1px solid #3a3a3a; /* Slightly different or same border */
            }
            QComboBox:disabled {
                background-color: #282828; /* Similar to QLineEdit disabled */
                color: #6a6a6a;           /* Greyed-out text */
                border: 1px solid #3a3a3a; /* Consistent border */
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #3d3d3d;
                background: #2d2d2d;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #3d85c6;
                background: #3d85c6;
                border-radius: 3px;
            }
        """)

    @Slot(str, int)
    def update_status(self, message, timeout=5000):
        """Updates status message with optional timeout"""
        try:
            self.status_label.setText(f"Status: {message}")
            self.logger.info(f"Status update: {message}")
            
            # Optional: reset after timeout
            if timeout > 0:
                QTimer.singleShot(timeout, lambda: self.status_label.setText("Status: Ready"))
        except Exception as e:
            self.logger.error(f"Error updating status: {str(e)}")

    def load_video(self):
        """Open file dialog to load a video file"""
        try:
            self.logger.info("Opening file dialog to load video")
            options = QFileDialog.Options()
            options |= QFileDialog.ReadOnly
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Video",
                "",
                "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)",
                options=options
            )
            
            if not file_path:
                self.logger.info("User cancelled video selection")
                return
                
            # Store path and load through controller
            self.video_path = file_path
            self.controller.load_video(file_path)
            
            # Reset range slider values but don't calculate percentages yet
            self.range_slider.lower_value = 0
            self.range_slider.upper_value = 100
            self.range_slider.update()
            
        except Exception as e:
            self.logger.error(f"Error loading video: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error loading video: {str(e)}")

    def drop_video(self):
        """Process the selected video clip"""
        if not self.video_path:
            return
            
        try:
            # Calculate exact start and end times in seconds with 3 decimal precision
            start_time = round((self.range_slider.lower_value / 100) * (self.video_duration / 1000), 3)
            end_time = round((self.range_slider.upper_value / 100) * (self.video_duration / 1000), 3)
            duration = round(end_time - start_time, 3)
            
            # Double check duration is exactly 30 seconds when enforced
            if self.enforce_duration_limit and abs(duration - 30) > 0.001:
                end_time = start_time + 30
                duration = 30.0
            
            # Get output path
            input_dir = os.path.dirname(self.video_path)
            input_filename = os.path.splitext(os.path.basename(self.video_path))[0]
            
            # Only use custom name if the clip name container is visible or has text
            custom_name = ""
            if not self.enforce_duration_limit or self.clip_name_input.text().strip():
                custom_name = self.clip_name_input.text().strip()
                
            output_filename = f"{custom_name if custom_name else input_filename}_clip.mp4"
            output_path = os.path.join(input_dir, output_filename)
            
            # Show progress dialog
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            
            # Get enabled webhooks
            enabled_webhooks = self.get_enabled_webhooks()
            
            # Determine max file size based on settings
            max_size = 10 * 1024 * 1024  # Default Discord 10MB
            if not self.enforce_duration_limit:
                max_size = self.get_selected_filesize()
            
            # Process the video
            result = self.controller.drop_video(
                start_time, 
                end_time, 
                output_path, 
                enabled_webhooks, 
                max_size, 
                custom_name, 
                self.update_progress
            )
            
            if result and result.get("success"):
                file_size = result.get("file_size", 0)
                file_message = f"Clip saved to:\n{output_path}\nSize: {file_size / (1024 * 1024):.2f}MB"
                
                # Show appropriate messages based on file size and webhooks
                if enabled_webhooks:
                    webhook_success = result.get("webhook_success", False)
                    
                    if not webhook_success and file_size > (10 * 1024 * 1024):
                        QMessageBox.warning(self, "Warning", 
                                       f"The clip exceeds Discord's limit ({file_size / (1024 * 1024):.2f}MB).\n"
                                       f"It has been created locally, but cannot be sent to Discord.")
                    elif not webhook_success:
                        QMessageBox.warning(self, "Warning",
                                       "Failed to send to Discord webhook, but clip was created successfully.")
                        QMessageBox.information(self, "Clip Created", file_message)
                else:
                    # No webhooks enabled, just notify about the file
                    QMessageBox.information(self, "Clip Created", file_message)
            
        except Exception as e:
            self.logger.error(f"Error dropping video: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error dropping video: {str(e)}")
            self.progress_bar.hide()

    def get_enabled_webhooks(self):
        """Get list of enabled Discord webhook URLs"""
        enabled_webhooks = []
        if os.path.exists(WEBHOOKS_FILE):
            try:
                with open(WEBHOOKS_FILE, 'r') as f:
                    webhooks = json.load(f)
                    enabled_webhooks = [data['url'] for data in webhooks.values() 
                                       if data.get('checked', False)]
            except Exception as e:
                self.logger.error(f"Error loading webhooks: {str(e)}")
        return enabled_webhooks

    def toggle_play_pause(self):
        """Toggle video playback between playing and paused states"""
        self.controller.toggle_play_pause()

    def show_webhook_dialog(self):
        """Show the webhook management dialog"""
        dialog = WebhookDialog(self)
        dialog.exec()

    def update_progress(self, progress):
        """Update progress bar with current progress"""
        self.progress_bar.setValue(int(progress))
        if progress >= 100:
            self.progress_bar.hide()

    def position_changed(self, position):
        """Handle changes in playback position"""
        if self.video_duration > 0:
            # Update time display
            current_time = self.controller.media_controller.format_time(position)
            total_time = self.controller.media_controller.format_time(self.video_duration)
            clip_duration = (self.range_slider.upper_value - self.range_slider.lower_value) / 100 * (self.video_duration / 1000)
            self.time_label.setText(f"{current_time} / {total_time} (Duration: {clip_duration:.1f}s)")
            
            # Update the slider value to match the playback position
            self.set_slider_value(position)

    def duration_changed(self, duration):
        """Handle changes to media duration"""
        if duration <= 0:
            return
            
        self.video_duration = duration
        
        # Update time display
        current_time = self.controller.media_controller.format_time(0)
        total_time = self.controller.media_controller.format_time(duration)
        self.time_label.setText(f"{current_time} / {total_time}")
        
        # Set initial range with 30 seconds between handles
        if self.enforce_duration_limit:
            # Calculate the percentage that represents 30 seconds
            thirty_seconds_percent = (30000 / float(duration)) * 100
            
            # Start at 0 and span 30 seconds
            self.range_slider.lower_value = 0
            self.range_slider.upper_value = min(100, int(thirty_seconds_percent + 0.5))
        else:
            # If duration limit is not enforced, just show full range
            self.range_slider.lower_value = 0
            self.range_slider.upper_value = 100
            
        self.range_slider.update()
        
        # Force an update of the range display
        self.update_range(self.range_slider.lower_value, self.range_slider.upper_value)
        
        # Enable UI controls now that media is loaded
        self.play_pause_button.setEnabled(True)
        self.drop_button.setEnabled(True)

    def media_state_changed(self, state):
        """Handle media state changes (playing/paused/stopped)"""
        from PySide6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_button.setText("Pause")
        else:
            self.play_pause_button.setText("Play")

    def media_status_changed(self, status):
        """Handle media status changes"""
        from PySide6.QtMultimedia import QMediaPlayer
        
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            self.is_media_loaded = True
            self.play_pause_button.setEnabled(True)
            self.drop_button.setEnabled(True)
            self.update_status("Video loaded successfully")
            
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.is_media_loaded = False
            self.play_pause_button.setEnabled(False)
            self.drop_button.setEnabled(False)
            self.update_status("Error: Invalid media")
            QMessageBox.critical(self, "Error", f"Could not load video: format not supported or file is corrupted")

    def handle_error(self, error_str):
        """Handle media player errors"""
        self.logger.error(f"Media player error: {error_str}")
        self.update_status(f"Error: {error_str}")
        QMessageBox.critical(self, "Media Error", f"An error occurred: {error_str}")

    def update_range(self, lower, upper):
        """Handle range slider value changes"""
        if self.video_duration > 0:
            if self.enforce_duration_limit:
                # Calculate duration in exact milliseconds
                duration_ms = round((upper - lower) / 100 * self.video_duration)
                
                # If duration exceeds limit, adjust the upper value precisely
                if duration_ms > self.max_clip_duration:
                    # Calculate new upper value that gives exactly 30 seconds
                    new_upper = lower + round((self.max_clip_duration / self.video_duration) * 100, 3)
                    self.range_slider.upper_value = min(100, new_upper)
                    upper = self.range_slider.upper_value
                    self.range_slider.update()
            
            # Convert percentage to milliseconds with proper rounding
            start_time = round(lower / 100 * self.video_duration)
            end_time = round(upper / 100 * self.video_duration)
            
            # Update time display with more precision
            start_str = self.controller.media_controller.format_time(start_time)
            end_str = self.controller.media_controller.format_time(end_time)
            clip_duration = (end_time - start_time) / 1000  # Convert to seconds
            self.time_label.setText(f"{start_str} / {end_str} (Duration: {clip_duration:.3f}s)")

    def seek_to_time(self, value):
        """Seek to a specific time in the video by percentage"""
        self.controller.seek_to_percentage(value)

    def set_slider_value(self, position):
        """Update the slider value to match the current playback position"""
        if self.video_duration <= 0:
            return
            
        # Convert position to a percentage (0-100)
        value = int((position / self.video_duration) * 100)
        
        # Set the value directly on the base QSlider
        self.range_slider.setValue(value)

    def toggle_duration_limit(self, state):
        """Handle duration limit checkbox state change"""
        self.enforce_duration_limit = bool(state)
        self.duration_warning_label.setVisible(not self.enforce_duration_limit)
        
        # Enable/disable file size controls based on checkbox state
        self.filesize_combo.setEnabled(not self.enforce_duration_limit)
        # self.clip_name_input.setEnabled(not self.enforce_duration_limit) # Clip name is always editable.
        # self.filesize_container.setVisible is NOT called here, it's always visible.

        if self.enforce_duration_limit:
            # If limit is ON, disable and hide custom input
            self.custom_filesize_input.setEnabled(False)
            self.custom_filesize_container.setVisible(False)
        else:
            # If limit is OFF, re-evaluate custom filesize input visibility and enabled state
            # based on the current selection of filesize_combo
            is_custom = self.filesize_combo.currentIndex() == 5 # "Custom..."
            self.custom_filesize_container.setVisible(is_custom)
            self.custom_filesize_input.setEnabled(is_custom)
        
        if self.video_duration > 0:
            if self.enforce_duration_limit:
                # If enabling limit and current selection is too long, adjust it
                current_duration = (self.range_slider.upper_value - self.range_slider.lower_value) / 100 * self.video_duration
                if current_duration > self.max_clip_duration:
                    # Keep the start point and adjust the end point
                    new_upper = self.range_slider.lower_value + (self.max_clip_duration / self.video_duration * 100)
                    self.range_slider.upper_value = min(100, int(new_upper))
                    self.range_slider.update()
            self.update_range(self.range_slider.lower_value, self.range_slider.upper_value)

    def handle_filesize_option(self, index):
        """Handle selection of file size option
        This block shows/hides the custom file size input depending on the
        selected option in the file size dropdown and whether the duration
        limit is enforced. If "Custom..." is selected and the duration limit
        is OFF, the custom input is shown. Otherwise, it is hidden.
        """
        # ----------------------------------------------------------------------
        # This block shows/hides the custom file size input depending on the
        # selected option in the file size dropdown and whether the duration
        # limit is enforced. If "Custom..." is selected and the duration limit
        # is OFF, the custom input is shown. Otherwise, it is hidden.
        # ----------------------------------------------------------------------
        is_custom_selected = (index == 5)  # "Custom..." is at index 5

        # Only show and enable custom input if "Custom..." is selected
        # AND the duration limit is NOT enforced.
        should_show_custom = is_custom_selected and not self.enforce_duration_limit

        self.custom_filesize_container.setVisible(should_show_custom)
        self.custom_filesize_input.setEnabled(should_show_custom)

    def get_selected_filesize(self):
        """Get the selected file size limit in bytes
        Returns the file size limit (in bytes) based on the user's selection in
        the file size dropdown or the custom input. If the input is invalid or
        not set, defaults to 10MB. This ensures the app never tries to use an
        invalid file size for video export.
        """
        index = self.filesize_combo.currentIndex()
        if index == 0:  # 10 MB
            return 10 * 1024 * 1024
        elif index == 1:  # 25 MB
            return 25 * 1024 * 1024
        elif index == 2:  # 50 MB
            return 50 * 1024 * 1024
        elif index == 3:  # 100 MB
            return 100 * 1024 * 1024
        elif index == 4:  # 500 MB
            return 500 * 1024 * 1024
        elif index == 5:  # Custom
            try:
                # Try to read the custom value (in MB) and convert to bytes.
                # If the value is invalid (not a number or <= 0), default to 10MB.
                custom_mb = float(self.custom_filesize_input.text())
                if custom_mb <= 0:
                    return 10 * 1024 * 1024  # Default to 10MB if invalid
                return int(custom_mb * 1024 * 1024)
            except ValueError:
                return 10 * 1024 * 1024  # Default to 10MB if parsing fails
        
        return 10 * 1024 * 1024  # Default fallback if something unexpected happens
        # ----------------------------------------------------------------------
        # End of file size selection logic
        # ----------------------------------------------------------------------
        # ...existing code...

    def view_logs(self):
        """Open the log file for viewing"""
        try:
            log_path = os.path.join(get_logs_directory(), 'game_drop_debug.log')
            self.logger.info(f"Opening log file: {log_path}")
            
            # Prepare system info for the log viewer
            system_info = f"GameDrop v{VERSION}\n"
            system_info += f"Python: {sys.version}\n"
            system_info += f"OS: {os.name} ({sys.platform})\n"
            system_info += f"GPU Encoder: {self.detected_gpu}\n"
            system_info += "-" * 80 + "\n\n"
            
            # Create and show log viewer dialog
            dialog = LogViewerDialog(self, log_path, system_info)
            dialog.exec()
            
        except Exception as e:
            self.logger.error(f"Error viewing logs: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not open log file: {str(e)}")

    def show_ffmpeg_download_dialog(self):
        """Prompt the user to download FFmpeg if not found"""
        def download_progress_callback(value):
            dialog.progress.setValue(value)
        
        def download_ffmpeg_callback():
            try:
                download_ffmpeg(progress_callback=download_progress_callback)
                self.controller.ffmpeg_available = True
                return True
            except Exception as e:
                self.logger.error(f"Error downloading FFmpeg: {str(e)}")
                return False
        
        # Create and show the FFmpeg download dialog
        dialog = FFmpegDownloadDialog(self, download_ffmpeg_callback)
        result = dialog.exec()
        
        if not self.controller.ffmpeg_available:
            self.drop_button.setEnabled(False)
            self.update_status("FFmpeg not available. Video clipping disabled.", 0)