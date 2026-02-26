"""
Main window for the Game Drop application.
Redesigned with frameless window, two-column layout, and modern styling.
"""

import sys
import os
import logging
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QProgressBar, QCheckBox,
    QSizePolicy, QComboBox, QLineEdit, QDialog, QFrame,
    QSpacerItem, QApplication
)
from PySide6.QtCore import Qt, QTimer, QUrl, Signal, Slot, QSize, QRectF, QPoint, QMimeData, QEvent, QThread
from PySide6.QtGui import QIcon, QPixmap, QPainter, QMouseEvent, QDragEnterEvent, QDropEvent, QCursor, QDesktopServices
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtMultimediaWidgets import QVideoWidget

from gamedrop.ui.range_slider import RangeSlider
from gamedrop.ui.dialogs import WebhookDialog, LogViewerDialog, FFmpegDownloadDialog
from gamedrop.utils.ffmpeg_wrapper import download_ffmpeg
from gamedrop.utils.paths import resource_path, get_logs_directory, get_webhooks_path
from gamedrop.platform_utils import is_windows, is_linux, is_steam_deck
from gamedrop.version import VERSION
from gamedrop.utils.updater import check_for_updates
from gamedrop.utils.discord_oauth import DiscordOAuth

# Configure logging
logger = logging.getLogger("GameDrop.MainWindow")

# Constants
WEBHOOKS_FILE = get_webhooks_path()


class DropZone(QLabel):
    """
    A dedicated drop zone widget for drag-and-drop file operations.
    Works reliably on Wayland/KDE Plasma with Qt6.
    """
    fileDropped = Signal(str)  # Emits file path when a video file is dropped
    clicked = Signal()         # Emits when clicked (for play/pause toggle)
    
    SUPPORTED_EXTENSIONS = ('.mp4', '.avi', '.mkv', '.mov', '.webm', '.wmv', '.flv', '.m4v')
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger("GameDrop.DropZone")
        self.is_overlay = False
        self.setText("📁 Drag & Drop Video Here\nor click Load Video")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)  # Critical for Wayland!
        self.setWordWrap(True)
        self._apply_default_style()
    
    def set_overlay_mode(self, enabled: bool):
        """Toggle overlay mode (transparent for video overlay)"""
        self.is_overlay = enabled
        if enabled:
            self.setText("")
            self._apply_overlay_style()
            self.show()
        else:
            self.setText("📁 Drag & Drop Video Here\nor click Load Video")
            self._apply_default_style()
            self.show()

    def _apply_default_style(self):
        """Apply the default (not hovering) style"""
        self.setStyleSheet("""
            QLabel {
                border: 3px dashed rgba(124, 77, 255, 0.6);
                border-radius: 12px;
                background: #141423;
                color: rgba(255, 255, 255, 0.7);
                font-size: 16px;
                font-weight: 500;
                padding: 20px;
            }
        """)
        
    def _apply_overlay_style(self):
        """Apply the overlay style (transparent)"""
        self.setStyleSheet("QLabel { background: transparent; border: none; }")
        
    def _apply_hover_style(self):
        """Apply the hover/drag-active style"""
        self.setStyleSheet("""
            QLabel {
                border: 3px solid #7c4dff;
                border-radius: 12px;
                background: rgba(124, 77, 255, 0.2);
                color: white;
                font-size: 16px;
                font-weight: 600;
                padding: 20px;
            }
        """)
        
    def _is_valid_video_file(self, file_path: str) -> bool:
        """Check if the file path is a supported video format"""
        return file_path.lower().endswith(self.SUPPORTED_EXTENSIONS)
    
    def _extract_file_paths(self, mime_data: QMimeData) -> list:
        """Extract file paths from mime data with multiple fallback methods"""
        paths = []
        
        # Method 1: Standard URL extraction
        if mime_data.hasUrls():
            for url in mime_data.urls():
                file_path = url.toLocalFile()
                # Fallback for Wayland where toLocalFile() might be empty
                if not file_path and url.scheme() == 'file':
                    file_path = url.path()
                if file_path:
                    paths.append(file_path)
                    
        # Method 2: Manual text/uri-list parsing as fallback
        if not paths and mime_data.hasFormat('text/uri-list'):
            try:
                data = bytes(mime_data.data('text/uri-list')).decode('utf-8')
                for line in data.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith('file://'):
                        paths.append(QUrl(line).toLocalFile() or line[7:])
                    else:
                        paths.append(line)
            except Exception as e:
                self.logger.error(f"Error parsing uri-list: {e}")
                
        return paths

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse click to toggle play/pause"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter with visual feedback"""
        mime_data = event.mimeData()
        self.logger.debug(f"Drag enter. Formats: {mime_data.formats()}")
        
        if mime_data.hasUrls() or mime_data.hasFormat('text/uri-list'):
            # Check if any dropped files are valid videos
            paths = self._extract_file_paths(mime_data)
            for path in paths:
                if self._is_valid_video_file(path):
                    event.acceptProposedAction()
                    self._apply_hover_style()
                    self.setText("🎬 Drop to Load Video")
                    return
                    
            # Has URLs but no valid video files
            self.logger.debug(f"No valid video files in drop: {paths}")
            
        event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move - required for Wayland"""
        if event.mimeData().hasUrls() or event.mimeData().hasFormat('text/uri-list'):
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Reset style when drag leaves"""
        if self.is_overlay:
            self._apply_overlay_style()
            self.setText("")
        else:
            self._apply_default_style()
            self.setText("📁 Drag & Drop Video Here\nor click Load Video")
        event.accept()

    def dropEvent(self, event: QDropEvent):
        """Handle the drop and emit the file path"""
        self.logger.debug("Drop event received")
        if self.is_overlay:
            self._apply_overlay_style()
            self.setText("")
        else:
            self._apply_default_style()
            self.setText("📁 Drag & Drop Video Here\nor click Load Video")
        
        paths = self._extract_file_paths(event.mimeData())
        self.logger.info(f"Drop candidates: {paths}")
        
        for file_path in paths:
            if self._is_valid_video_file(file_path):
                self.logger.info(f"Valid video dropped: {file_path}")
                self.fileDropped.emit(file_path)
                event.acceptProposedAction()
                return
                
        self.logger.warning("Drop ignored - no valid video files")
        event.ignore()


class TitleBar(QWidget):
    """Custom frameless title bar widget with window controls."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._drag_pos = None
        self._dragging = False
        self._is_maximized = False
        self.setObjectName("titleBar")
        self.setFixedHeight(48)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)
        
        # Logo
        self.logo_widget = QSvgWidget()
        svg_path = resource_path('assets/logo.svg')
        temp_renderer = QSvgRenderer(svg_path)
        if temp_renderer.isValid():
            default_size = temp_renderer.defaultSize()
            target_height = 28
            if default_size.height() > 0:
                aspect_ratio = default_size.width() / default_size.height()
                target_width = int(target_height * aspect_ratio)
            else:
                target_width = 42
            self.logo_widget.setFixedSize(QSize(target_width, target_height))
            self.logo_widget.load(svg_path)
        layout.addWidget(self.logo_widget)
        
        # Title
        title_label = QLabel(f"Game Drop")
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label)
        
        # Version
        version_label = QLabel(f"v{VERSION}")
        version_label.setObjectName("versionLabel")
        layout.addWidget(version_label)

        # Check for update button
        self.check_update_btn = QPushButton("Check for Update")
        self.check_update_btn.setCursor(Qt.PointingHandCursor)
        self.check_update_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8a8a8a;
                border: none;
                font-size: 11px;
                text-decoration: underline;
                padding: 0px;
                margin-left: 5px;
            }
            QPushButton:hover {
                color: #7c4dff;
            }
        """)
        self.check_update_btn.clicked.connect(self.check_for_updates)
        layout.addWidget(self.check_update_btn)
        
        layout.addStretch(1)
        
        # GPU info
        self.gpu_label = QLabel("GPU: Detecting...")
        self.gpu_label.setObjectName("gpuLabel")
        layout.addWidget(self.gpu_label)
        
        # GPU indicator dot
        gpu_indicator = QLabel("●")
        gpu_indicator.setObjectName("gpuIndicator")
        layout.addWidget(gpu_indicator)
        
        layout.addSpacing(20)
        
        # Window controls
        self.min_btn = QPushButton("─")
        self.min_btn.setObjectName("titleBarButton")
        self.min_btn.clicked.connect(self.minimize_window)
        layout.addWidget(self.min_btn)
        
        self.max_btn = QPushButton("□")
        self.max_btn.setObjectName("titleBarButton")
        self.max_btn.clicked.connect(self.toggle_maximize)
        layout.addWidget(self.max_btn)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("closeButton")
        self.close_btn.clicked.connect(self.close_window)
        layout.addWidget(self.close_btn)
        
    def set_gpu_info(self, gpu_type):
        self.gpu_label.setText(f"GPU: {gpu_type}")

    def check_for_updates(self):
        """Check for updates and notify user"""
        self.check_update_btn.setEnabled(False)
        self.check_update_btn.setText("Checking...")
        
        # In a real app, this should be threaded to avoid UI freeze
        # But for simplicity we'll do it here as requested
        # Since requests is synchronous, force a repaint first
        QApplication.processEvents()
        
        try:
            is_avail, new_ver, url = check_for_updates(VERSION)
            
            if is_avail:
                msg = QMessageBox(self)
                msg.setWindowTitle("Update Available")
                msg.setText(f"A new version of Game Drop is available!\n\nCurrent: {VERSION}\nLatest: {new_ver}")
                msg.setIcon(QMessageBox.Information)
                download_btn = msg.addButton("Download", QMessageBox.AcceptRole)
                msg.addButton("Later", QMessageBox.RejectRole)
                msg.exec()
                
                if msg.clickedButton() == download_btn:
                    QDesktopServices.openUrl(QUrl(url))
            else:
                QMessageBox.information(
                    self,
                    "Up to Date",
                    f"You are using the latest version of Game Drop (v{VERSION})."
                )
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to check for updates: {e}")
            
        finally:
            self.check_update_btn.setEnabled(True)
            self.check_update_btn.setText("Check for Update")
        
    def minimize_window(self):
        if self.parent_window:
            self.parent_window.showMinimized()
            
    def toggle_maximize(self):
        if self.parent_window:
            if self._is_maximized:
                self.parent_window.showNormal()
                self.max_btn.setText("□")
            else:
                self.parent_window.showMaximized()
                self.max_btn.setText("❐")
            self._is_maximized = not self._is_maximized
            
    def close_window(self):
        if self.parent_window:
            self.parent_window.close()
            
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # Check if the click is near a resize edge/corner of the parent window.
            # Without this, clicks in the top-left/top-right corners would start
            # a window drag instead of a resize.
            if self.parent_window:
                # Map click position to the parent window's coordinate space
                parent_pos = self.mapTo(self.parent_window, event.pos())
                edges = self.parent_window._get_resize_edge(parent_pos)
                if edges:
                    window = self.parent_window.windowHandle()
                    if window:
                        window.startSystemResize(edges)
                    event.accept()
                    return
            
            # Not near a resize edge — start a normal window drag
            window = self.parent_window.windowHandle()
            if window:
                window.startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event: QMouseEvent):
        """Update cursor to show resize affordance at corners/top edge."""
        if self.parent_window:
            parent_pos = self.mapTo(self.parent_window, event.pos())
            edges = self.parent_window._get_resize_edge(parent_pos)

            if edges == (Qt.LeftEdge | Qt.TopEdge) or edges == (Qt.RightEdge | Qt.BottomEdge):
                self.setCursor(QCursor(Qt.SizeFDiagCursor))
            elif edges == (Qt.RightEdge | Qt.TopEdge) or edges == (Qt.LeftEdge | Qt.BottomEdge):
                self.setCursor(QCursor(Qt.SizeBDiagCursor))
            elif edges & (Qt.LeftEdge | Qt.RightEdge):
                self.setCursor(QCursor(Qt.SizeHorCursor))
            elif edges & (Qt.TopEdge | Qt.BottomEdge):
                self.setCursor(QCursor(Qt.SizeVerCursor))
            else:
                self.unsetCursor()  # Let title bar show its default arrow
        super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        super().mouseReleaseEvent(event)
            
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()
            event.accept()


class DiscordAuthThread(QThread):
    auth_finished = Signal(bool)
    
    def __init__(self, oauth_client, parent=None):
        super().__init__(parent)
        self.oauth_client = oauth_client
        
    def run(self):
        success = self.oauth_client.start_auth()
        self.auth_finished.emit(success)


class MainWindow(QWidget):
    """
    Main application window for Game Drop with video playback and clipping controls.
    Redesigned with frameless window and two-column layout.
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
        self.enforce_duration_limit = False
        self.detected_gpu = self.controller.video_processor.gpu.gpu_type
        self.discord_oauth = DiscordOAuth()
        
        # Enable frameless window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        # Enable drag-drop and mouse tracking for resize
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self._resize_margin = 12  # Pixels from edge to trigger resize (increased for usability)
        
        self.init_ui()
        self.apply_styles()
        
        # Update title bar with GPU info
        self.title_bar.set_gpu_info(self.detected_gpu)
        
        # Check FFmpeg and show download dialog if needed
        if not self.controller.ffmpeg_available:
            QTimer.singleShot(500, self.show_ffmpeg_download_dialog)

    def init_ui(self):
        """Initialize the user interface with two-column layout"""
        # Set window properties
        self.setWindowTitle(f"Game Drop v{VERSION}")
        self.set_window_icon()
        self.setGeometry(50, 50, 1024, 640)
        self.setMinimumSize(900, 600)
        
        # Main container layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Custom title bar
        self.title_bar = TitleBar(self)
        main_layout.addWidget(self.title_bar)
        
        # Content area
        content_widget = QWidget()
        content_widget.setObjectName("mainContainer")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 12, 16, 8)
        content_layout.setSpacing(12)
        
        # Two-column layout
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(16)
        
        # ============================================
        # LEFT COLUMN - Video Player
        # ============================================
        left_panel = QWidget()
        left_panel.setObjectName("videoPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)
        
        # Video container with play button overlay
        self.video_container = QWidget()
        self.video_container.setObjectName("videoContainer")
        video_container_layout = QVBoxLayout(self.video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)
        video_container_layout.setSpacing(0)
        
        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(400, 280)
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        self.video_widget.setAttribute(Qt.WA_OpaquePaintEvent)
        # Enable drops on video widget and install event filter to handle them
        self.video_widget.setAcceptDrops(True)
        self.video_widget.installEventFilter(self)
        
        # Set up media controller with video output (deferred init - won't hang here)
        self.controller.media_controller.set_video_output(self.video_widget)
        
        video_container_layout.addWidget(self.video_widget)
        
        # Play/Pause overlay button (centered on video, hidden until video loads)
        self.play_overlay_btn = QPushButton("▶")
        self.play_overlay_btn.setObjectName("playOverlayButton")
        self.play_overlay_btn.setFixedSize(64, 64)
        self.play_overlay_btn.clicked.connect(self.toggle_play_pause)
        self.play_overlay_btn.setStyleSheet("""
            QPushButton#playOverlayButton {
                background-color: rgba(0, 0, 0, 0.6);
                border: 2px solid rgba(255, 255, 255, 0.8);
                border-radius: 32px;
                color: white;
                font-size: 28px;
                font-weight: bold;
            }
            QPushButton#playOverlayButton:hover {
                background-color: rgba(124, 77, 255, 0.8);
                border: 2px solid white;
            }
        """)
        # Position the button in the center of the video container
        self.play_overlay_btn.setParent(self.video_container)
        self.play_overlay_btn.raise_()
        self.play_overlay_btn.hide()  # Hidden until video loads
        
        # Make video widget clickable for play/pause
        self.video_widget.mousePressEvent = self._video_clicked
        
        # Drop zone overlay for drag-and-drop (Wayland compatible)
        self.drop_zone = DropZone(self.video_container)
        self.drop_zone.fileDropped.connect(self._on_file_dropped)
        self.drop_zone.clicked.connect(self.toggle_play_pause)
        self.drop_zone.setMinimumSize(200, 150)
        # Will be positioned in resizeEvent
        
        left_layout.addWidget(self.video_container, 1)
        
        # Timeline container
        timeline_container = QWidget()
        timeline_container.setObjectName("timelineContainer")
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.setContentsMargins(12, 8, 12, 8)
        timeline_layout.setSpacing(8)
        
        # Time labels row
        time_labels_layout = QHBoxLayout()
        time_labels_layout.setSpacing(0)
        
        self.start_time_label = QLabel("00:00:00")
        self.start_time_label.setObjectName("timeLabel")
        time_labels_layout.addWidget(self.start_time_label)
        
        time_labels_layout.addStretch(1)
        
        self.clip_start_label = QLabel("00:00:04")
        self.clip_start_label.setObjectName("timeLabelActive")
        time_labels_layout.addWidget(self.clip_start_label)
        
        time_labels_layout.addStretch(2)
        
        self.clip_end_label = QLabel("00:00:07")
        self.clip_end_label.setObjectName("timeLabelActive")
        time_labels_layout.addWidget(self.clip_end_label)
        
        time_labels_layout.addStretch(1)
        
        self.end_time_label = QLabel("00:00:13")
        self.end_time_label.setObjectName("timeLabel")
        time_labels_layout.addWidget(self.end_time_label)
        
        timeline_layout.addLayout(time_labels_layout)
        
        # Range slider
        self.range_slider = RangeSlider(Qt.Horizontal)
        self.range_slider.setMinimumHeight(32)
        self.range_slider.rangeChanged.connect(self.update_range)
        self.range_slider.valueClicked.connect(self.seek_to_time)
        timeline_layout.addWidget(self.range_slider)
        
        # Legacy time label (hidden but kept for compatibility)
        self.time_label = QLabel('00:00:00 / 00:00:00')
        self.time_label.setVisible(False)
        
        left_layout.addWidget(timeline_container)
        
        columns_layout.addWidget(left_panel, 65)
        
        # ============================================
        # RIGHT COLUMN - Options Panel
        # ============================================
        right_panel = QFrame()
        right_panel.setObjectName("optionsPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(16)
        
        # Discord optimization checkbox row
        discord_row = QHBoxLayout()
        discord_row.setSpacing(12)
        
        self.duration_limit_checkbox = QCheckBox("Send to Discord\n(30s / 10MB)")
        self.duration_limit_checkbox.setChecked(False)
        self.duration_limit_checkbox.setEnabled(False)
        self.duration_limit_checkbox.setToolTip("Connect to Discord first to enable sending")
        self.duration_limit_checkbox.stateChanged.connect(self.toggle_duration_limit)
        discord_row.addWidget(self.duration_limit_checkbox)
        
        discord_row.addStretch(1)
        
        # Extra quality checkbox
        self.extra_quality_checkbox = QCheckBox("Extra quality\n(Slower)")
        self.extra_quality_checkbox.setChecked(False)
        discord_row.addWidget(self.extra_quality_checkbox)
        
        right_layout.addLayout(discord_row)
        
        # Max filesize row
        filesize_row = QHBoxLayout()
        filesize_row.setSpacing(12)
        
        filesize_label = QLabel("Max Filesize:")
        filesize_label.setObjectName("sectionLabel")
        filesize_row.addWidget(filesize_label)
        
        self.filesize_combo = QComboBox()
        self.filesize_combo.addItems(["10 MB", "25 MB", "50 MB", "100 MB", "500 MB", "Custom..."])
        self.filesize_combo.setCurrentIndex(0)
        self.filesize_combo.setEnabled(False)
        self.filesize_combo.currentIndexChanged.connect(self.handle_filesize_option)
        filesize_row.addWidget(self.filesize_combo, 1)
        
        right_layout.addLayout(filesize_row)
        
        # Custom filesize (hidden by default)
        self.custom_filesize_container = QWidget()
        custom_filesize_layout = QHBoxLayout(self.custom_filesize_container)
        custom_filesize_layout.setContentsMargins(0, 0, 0, 0)
        custom_filesize_layout.setSpacing(12)
        
        custom_filesize_label = QLabel("Custom Size (MB):")
        custom_filesize_label.setObjectName("sectionLabel")
        custom_filesize_layout.addWidget(custom_filesize_label)
        
        self.custom_filesize_input = QLineEdit()
        self.custom_filesize_input.setPlaceholderText("e.g., 10")
        self.custom_filesize_input.setEnabled(False)
        custom_filesize_layout.addWidget(self.custom_filesize_input, 1)
        self.custom_filesize_input.textChanged.connect(lambda: self.handle_filesize_option(self.filesize_combo.currentIndex()))
        
        self.custom_filesize_container.setVisible(False)
        right_layout.addWidget(self.custom_filesize_container)
        
        # Discord limit warning label
        self.discord_limit_label = QLabel("⚠️ L.")
        self.discord_limit_label.setStyleSheet("color: #FFA500; font-weight: bold; font-size: 13px;")
        self.discord_limit_label.setVisible(False)
        self.discord_limit_label.setWordWrap(True)
        right_layout.addWidget(self.discord_limit_label)
        
        # Output format row
        output_format_row = QHBoxLayout()
        output_format_row.setSpacing(12)
        
        output_format_label = QLabel("Output Format:")
        output_format_label.setObjectName("sectionLabel")
        output_format_row.addWidget(output_format_label)
        
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(["Original", "Landscape (16:9)", "Vertical (9:16)"])
        self.output_format_combo.setCurrentIndex(0)
        output_format_row.addWidget(self.output_format_combo, 1)
        
        right_layout.addLayout(output_format_row)
        
        # Clip name row
        clip_name_row = QHBoxLayout()
        clip_name_row.setSpacing(12)
        
        clip_name_label = QLabel("Clip name\n(optional):")
        clip_name_label.setObjectName("sectionLabel")
        clip_name_row.addWidget(clip_name_label)
        
        self.clip_name_input = QLineEdit()
        self.clip_name_input.setPlaceholderText("batter_up_clip_clip")
        clip_name_row.addWidget(self.clip_name_input, 1)
        
        right_layout.addLayout(clip_name_row)
        
        right_layout.addSpacing(8)
        
        # Buttons row 1: Load Video & Webhooks
        buttons_row1 = QHBoxLayout()
        buttons_row1.setSpacing(12)
        
        self.load_button = QPushButton('📁 Load Video')
        self.load_button.clicked.connect(self.load_video)
        buttons_row1.addWidget(self.load_button)
        
        self.webhook_button = QPushButton('⚙ Webhooks')
        self.webhook_button.clicked.connect(self.show_webhook_dialog)
        self.webhook_button.setEnabled(False)
        self.webhook_button.setToolTip("Connect to Discord first")
        buttons_row1.addWidget(self.webhook_button)
        
        right_layout.addLayout(buttons_row1)
        
        # Connect to Discord button
        self.discord_connect_button = QPushButton()
        self.discord_connect_button.setObjectName("discordButton")
        self.discord_connect_button.clicked.connect(self.handle_discord_button)
        self.update_discord_btn_state()
        # If user has a cached valid auth, enable the Send to Discord checkbox and Webhooks
        if self.discord_oauth.is_authenticated():
            self.duration_limit_checkbox.setEnabled(True)
            self.duration_limit_checkbox.setToolTip("")
            self.duration_limit_checkbox.setChecked(True)
            self.webhook_button.setEnabled(True)
            self.webhook_button.setToolTip("")
        right_layout.addWidget(self.discord_connect_button)
        
        # Drop It button
        self.drop_button = QPushButton('💧 Drop It')
        self.drop_button.setObjectName("primaryButton")
        self.drop_button.setEnabled(False)
        self.drop_button.clicked.connect(self.drop_video)
        right_layout.addWidget(self.drop_button)
        
        # Play/Pause button (hidden, controlled via video click)
        self.play_pause_button = QPushButton('Play')
        self.play_pause_button.setEnabled(False)
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.play_pause_button.setVisible(False)
        
        right_layout.addStretch(1)
        
        # Duration warning label
        self.duration_warning_label = QLabel("⚠️ Clips will be saved locally.")
        self.duration_warning_label.setStyleSheet("color: #FFA500; font-style: italic;")
        self.duration_warning_label.setVisible(False)
        right_layout.addWidget(self.duration_warning_label)
        
        columns_layout.addWidget(right_panel, 35)
        
        content_layout.addLayout(columns_layout, 1)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        content_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(content_widget, 1)
        
        # Status bar
        status_bar = QWidget()
        status_bar.setObjectName("statusBar")
        status_bar.setFixedHeight(36)
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 0, 16, 0)
        status_layout.setSpacing(8)
        
        status_indicator = QLabel("●")
        status_indicator.setObjectName("statusIndicator")
        status_layout.addWidget(status_indicator)
        
        self.status_label = QLabel("Status: Ready")
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch(1)
        
        self.log_button = QPushButton('📋 View Logs')
        self.log_button.setObjectName("logButton")
        self.log_button.clicked.connect(self.view_logs)
        status_layout.addWidget(self.log_button)
        
        main_layout.addWidget(status_bar)
        
        # Legacy containers for compatibility
        self.filesize_container = QWidget()
        self.clip_name_container = QWidget()

        # Enable drag and drop on all main containers to cover the "sides" and other dead zones
        accessable_containers = [
            content_widget,
            left_panel,
            self.video_container,
            timeline_container,
            right_panel,
            status_bar
        ]
        
        for container in accessable_containers:
            container.setAcceptDrops(True)
            container.installEventFilter(self)
        
    def set_window_icon(self):
        """Set the window icon from SVG"""
        icon_size = 32
        svg_path = resource_path('assets/logo.svg')
        renderer = QSvgRenderer(svg_path)
        
        if renderer.isValid():
            renderer.setAspectRatioMode(Qt.KeepAspectRatio)
            icon_pixmap = QPixmap(icon_size, icon_size)
            icon_pixmap.fill(Qt.transparent)
            painter = QPainter(icon_pixmap)
            renderer.render(painter, QRectF(icon_pixmap.rect()))
            painter.end()
            self.setWindowIcon(QIcon(icon_pixmap))
        else:
            self.setWindowIcon(QIcon(svg_path))

    def apply_styles(self):
        """Apply custom styling from external QSS file"""
        qss_path = resource_path('ui/styles.qss')
        try:
            with open(qss_path, 'r') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            self.logger.warning(f"Could not find styles.qss at {qss_path}, using fallback styles")
            self.apply_fallback_styles()
            
    def apply_fallback_styles(self):
        """Fallback styles if QSS file not found"""
        self.setStyleSheet("""        
            QWidget {
                background-color: #12121a;
                color: #e0e0e0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QPushButton {
                background-color: #2a2a3e;
                border: 1px solid #3a3a4e;
                padding: 10px 20px;
                border-radius: 8px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3a3a4e;
            }
            QPushButton#primaryButton {
                background-color: #38bdf8;
                color: #0a0a12;
                font-weight: 600;
            }
            QPushButton#discordButton {
                background-color: #7c4dff;
                color: #ffffff;
            }
            QLineEdit, QComboBox {
                background-color: #22223a;
                border: 1px solid #3a3a4e;
                border-radius: 6px;
                padding: 10px;
            }
            QCheckBox::indicator:checked {
                background-color: #7c4dff;
            }
        """)

    @Slot(str, int)
    def update_status(self, message, timeout=5000):
        """Updates status message with optional timeout"""
        try:
            self.status_label.setText(f"Status: {message}")
            self.logger.info(f"Status update: {message}")
            
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
                
            self.video_path = file_path
            self.controller.load_video(file_path)
            
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
            start_time = round((self.range_slider.lower_value / 100) * (self.video_duration / 1000), 3)
            end_time = round((self.range_slider.upper_value / 100) * (self.video_duration / 1000), 3)
            duration = round(end_time - start_time, 3)
            
            if self.enforce_duration_limit and abs(duration - 30) > 0.001:
                end_time = start_time + 30
                duration = 30.0
            
            input_dir = os.path.dirname(self.video_path)
            input_filename = os.path.splitext(os.path.basename(self.video_path))[0]
            
            custom_name = ""
            if not self.enforce_duration_limit or self.clip_name_input.text().strip():
                custom_name = self.clip_name_input.text().strip()
                
            output_filename = f"{custom_name if custom_name else input_filename}_clip.mp4"
            output_path = os.path.normpath(os.path.join(input_dir, output_filename))
            
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            
            enabled_webhooks = self.get_enabled_webhooks()
            
            # SAFEGUARD: Never send to Discord if not authenticated or checkbox is unchecked
            if not self.discord_oauth.is_authenticated() or not self.enforce_duration_limit:
                enabled_webhooks = []
            
            max_size = 10 * 1024 * 1024
            if not self.enforce_duration_limit:
                max_size = self.get_selected_filesize()

            # Pre-flight check for Discord limit
            if max_size > 10 * 1024 * 1024 and enabled_webhooks:
                # Disable webhooks for this drop since user explicitly asked for > 10MB
                self.logger.info(f"Target size {max_size} > 10MB, disabling webhooks for this drop.")
                enabled_webhooks = [] 
                
                # Visual feedback is handled by handle_filesize_option, but we double check here
                # to prevent upload. The user should already see the warning label.
            
            output_format = self.output_format_combo.currentText()
            discord_user = self.discord_oauth.get_cached_user() if self.discord_oauth.is_authenticated() else None
            extra_quality = self.extra_quality_checkbox.isChecked()
            
            result = self.controller.drop_video(
                start_time, 
                end_time, 
                output_path, 
                enabled_webhooks, 
                max_size, 
                custom_name, 
                self.update_progress,
                output_format,
                discord_user,
                extra_quality
            )
            
            # Warn if webhooks were requested but size limit prevented it (Backend check backup)
            # This logic might need adjustment if we stripped webhooks beforehand
            if result and result.get("success"):
                file_size = result.get("file_size", 0)
                file_message = f"Clip saved to:\n{output_path}\nSize: {file_size / (1024 * 1024):.2f}MB"
                
                if enabled_webhooks:
                    webhook_success = result.get("webhook_success", False)
                    
                    if not webhook_success and file_size > (10 * 1024 * 1024):
                        # Use a more specific message if we know we skipped it due to size
                        if max_size > 10 * 1024 * 1024:
                             QMessageBox.warning(self, "Discord Limit", 
                                       f"The clip is {file_size / (1024 * 1024):.2f}MB, which exceeds Discord's 10MB limit.\n"
                                       f"It has been saved locally.")
                        else:
                             QMessageBox.warning(self, "Warning", 
                                       f"The clip exceeds Discord's limit ({file_size / (1024 * 1024):.2f}MB).\n"
                                       f"It has been created locally, but cannot be sent to Discord.")

                    elif not webhook_success:
                        QMessageBox.warning(self, "Warning",
                                       "Failed to send to Discord webhook, but clip was created successfully.")
                        QMessageBox.information(self, "Clip Created", file_message)
                else:
                     # Check if we stripped webhooks due to size limit
                     if len(self.get_enabled_webhooks()) > 0 and max_size > 10 * 1024 * 1024:
                          QMessageBox.information(self, "Clip Created (Local Only)", 
                                                f"Clip saved locally (Too large for Discord).\n\n"
                                                f"Path: {output_path}\n"
                                                f"Size: {file_size / (1024 * 1024):.2f}MB")
                     else:
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
        if not self.is_media_loaded:
            self.load_video()
            return
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
    
    def _video_clicked(self, event):
        """Handle clicks on the video widget to toggle play/pause"""
        if self.is_media_loaded:
            self.toggle_play_pause()
    
    def _on_file_dropped(self, file_path: str):
        """Handle file dropped from the DropZone widget"""
        self.logger.info(f"File dropped via DropZone: {file_path}")
        self.video_path = file_path
        self.controller.load_video(file_path)
        self.range_slider.lower_value = 0
        self.range_slider.upper_value = 100
        self.range_slider.update()

    def update_discord_btn_state(self):
        if self.discord_oauth.is_authenticated():
            user = self.discord_oauth.get_cached_user()
            name = user['username'] if user else "Discord"
            self.discord_connect_button.setText(f'✓ Connected as {name}')
            self.discord_connect_button.setStyleSheet("background-color: #4CAF50; color: white; border: none; padding: 10px; border-radius: 6px; font-weight: bold;")
        else:
            self.discord_connect_button.setText('🔗 Connect to Discord')
            self.discord_connect_button.setStyleSheet("")

    def handle_discord_button(self):
        if self.discord_oauth.is_authenticated():
            reply = QMessageBox.question(self, 'Disconnect Discord', 
                                         "Are you sure you want to disconnect your Discord account?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.discord_oauth.logout()
                self.update_discord_btn_state()
                self.update_status("Disconnected from Discord")
                # Disable the Send to Discord checkbox and Webhooks button
                self.duration_limit_checkbox.setChecked(False)
                self.duration_limit_checkbox.setEnabled(False)
                self.duration_limit_checkbox.setToolTip("Connect to Discord first to enable sending")
                self.webhook_button.setEnabled(False)
                self.webhook_button.setToolTip("Connect to Discord first")
        else:
            self.update_status("Waiting for Discord authentication...")
            self.discord_connect_button.setEnabled(False)
            self.discord_connect_button.setText("⏳ Authenticating...")
            
            # Start auth in background thread
            self.auth_thread = DiscordAuthThread(self.discord_oauth, self)
            self.auth_thread.auth_finished.connect(self.on_auth_finished)
            self.auth_thread.start()

    def on_auth_finished(self, success):
        self.discord_connect_button.setEnabled(True)
        if success:
            self.update_discord_btn_state()
            self.update_status("Successfully connected to Discord!")
            # Enable and check the Send to Discord checkbox now that user is authed
            self.duration_limit_checkbox.setEnabled(True)
            self.duration_limit_checkbox.setToolTip("")
            self.duration_limit_checkbox.setChecked(True)
            self.webhook_button.setEnabled(True)
            self.webhook_button.setToolTip("")
        else:
            self.update_discord_btn_state()
            self.update_status("Discord authentication failed or timed out.")
            QMessageBox.warning(self, "Authentication Failed", "Could not authenticate with Discord. The request may have timed out or been cancelled.")

    def position_changed(self, position):
        """Handle changes in playback position"""
        if self.video_duration > 0:
            current_time = self.controller.media_controller.format_time(position)
            total_time = self.controller.media_controller.format_time(self.video_duration)
            clip_duration = (self.range_slider.upper_value - self.range_slider.lower_value) / 100 * (self.video_duration / 1000)
            self.time_label.setText(f"{current_time} / {total_time} (Duration: {clip_duration:.1f}s)")
            self.set_slider_value(position)

    def duration_changed(self, duration):
        """Handle changes to media duration"""
        if duration <= 0:
            return
            
        self.video_duration = duration
        
        # Update time labels
        total_time = self.controller.media_controller.format_time(duration)
        self.end_time_label.setText(total_time)
        self.start_time_label.setText("00:00:00")
        
        if self.enforce_duration_limit:
            thirty_seconds_percent = (30000 / float(duration)) * 100
            self.range_slider.lower_value = 0
            self.range_slider.upper_value = min(100, int(thirty_seconds_percent + 0.5))
        else:
            self.range_slider.lower_value = 0
            self.range_slider.upper_value = 100
            
        self.range_slider.update()
        self.update_range(self.range_slider.lower_value, self.range_slider.upper_value)
        
        self.play_pause_button.setEnabled(True)
        self.drop_button.setEnabled(True)

    def media_state_changed(self, state):
        """Handle media state changes (playing/paused/stopped)"""
        from PySide6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_button.setText("Pause")
            self.play_overlay_btn.setText("⏸")
        else:
            self.play_pause_button.setText("Play")
            self.play_overlay_btn.setText("▶")

    def media_status_changed(self, status):
        """Handle media status changes"""
        from PySide6.QtMultimedia import QMediaPlayer
        
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            self.is_media_loaded = True
            self.play_pause_button.setEnabled(True)
            self.drop_button.setEnabled(True)
            self.play_overlay_btn.show()  # Show play button now that video is loaded
            self.drop_zone.set_overlay_mode(True)  # Switch drop zone to overlay mode
            self.update_status("Video loaded successfully")
            
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.is_media_loaded = False
            self.play_pause_button.setEnabled(False)
            self.drop_button.setEnabled(False)
            self.play_overlay_btn.hide()
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
                duration_ms = round((upper - lower) / 100 * self.video_duration)
                
                if duration_ms > self.max_clip_duration:
                    new_upper = lower + round((self.max_clip_duration / self.video_duration) * 100, 3)
                    self.range_slider.upper_value = min(100, new_upper)
                    upper = self.range_slider.upper_value
                    self.range_slider.update()
            
            start_time = round(lower / 100 * self.video_duration)
            end_time = round(upper / 100 * self.video_duration)
            
            # Update time labels
            start_str = self.controller.media_controller.format_time(start_time)
            end_str = self.controller.media_controller.format_time(end_time)
            clip_duration = (end_time - start_time) / 1000
            
            self.clip_start_label.setText(start_str)
            self.clip_end_label.setText(end_str)
            self.time_label.setText(f"{start_str} / {end_str} (Duration: {clip_duration:.3f}s)")

    def seek_to_time(self, value):
        """Seek to a specific time in the video by percentage"""
        self.controller.seek_to_percentage(value)

    def set_slider_value(self, position):
        """Update the slider value to match the current playback position"""
        if self.video_duration <= 0:
            return
        value = int((position / self.video_duration) * 100)
        self.range_slider.setValue(value)

    def toggle_duration_limit(self, state):
        """Handle duration limit checkbox state change"""
        self.enforce_duration_limit = bool(state)
        if hasattr(self, 'duration_warning_label'):
            self.duration_warning_label.setVisible(not self.enforce_duration_limit)
        if hasattr(self, 'filesize_combo'):
            self.filesize_combo.setEnabled(not self.enforce_duration_limit)

        if self.enforce_duration_limit:
            self.custom_filesize_input.setEnabled(False)
            self.custom_filesize_container.setVisible(False)
        else:
            is_custom = self.filesize_combo.currentIndex() == 5
            self.custom_filesize_container.setVisible(is_custom)
            self.custom_filesize_input.setEnabled(is_custom)
        
        if self.video_duration > 0:
            if self.enforce_duration_limit:
                current_duration = (self.range_slider.upper_value - self.range_slider.lower_value) / 100 * self.video_duration
                if current_duration > self.max_clip_duration:
                    new_upper = self.range_slider.lower_value + (self.max_clip_duration / self.video_duration * 100)
                    self.range_slider.upper_value = min(100, int(new_upper))
                    self.range_slider.update()
                    self.range_slider.update()
            self.update_range(self.range_slider.lower_value, self.range_slider.upper_value)
            
        self._update_discord_limit_ui()

    def _update_discord_limit_ui(self):
        """Update the Discord limit UI warning based on current settings"""
        should_show_warning = False
        
        if not self.enforce_duration_limit:
            current_size_limit = self.get_selected_filesize()
            if current_size_limit > 10 * 1024 * 1024:
                should_show_warning = True
                
        if should_show_warning:
            self.discord_limit_label.setVisible(True)
            self.webhook_button.setEnabled(False)
            self.webhook_button.setToolTip("Disabled: File size limit > 10MB")
            self.discord_connect_button.setEnabled(False)
            self.discord_connect_button.setToolTip("Disabled: File size limit > 10MB")
            self.webhook_button.setStyleSheet("background-color: #3a3a4e; color: #666;") # Grey out style
        else:
            self.discord_limit_label.setVisible(False)
            self.webhook_button.setEnabled(self.discord_oauth.is_authenticated())
            self.webhook_button.setToolTip("" if self.discord_oauth.is_authenticated() else "Connect to Discord first")
            self.discord_connect_button.setEnabled(True)
            self.discord_connect_button.setToolTip("")
            self.webhook_button.setStyleSheet("") # Reset style
            
    def handle_filesize_option(self, index):
        """Handle selection of file size option"""
        is_custom_selected = (index == 5)
        should_show_custom = is_custom_selected and not self.enforce_duration_limit
        self.custom_filesize_container.setVisible(should_show_custom)
        self.custom_filesize_input.setEnabled(should_show_custom)
        
        self._update_discord_limit_ui()

    def get_selected_filesize(self):
        """Get the selected file size limit in bytes"""
        index = self.filesize_combo.currentIndex()
        if index == 0:
            return 10 * 1024 * 1024
        elif index == 1:
            return 25 * 1024 * 1024
        elif index == 2:
            return 50 * 1024 * 1024
        elif index == 3:
            return 100 * 1024 * 1024
        elif index == 4:
            return 500 * 1024 * 1024
        elif index == 5:
            try:
                text = self.custom_filesize_input.text().strip()
                if not text:
                    return 10 * 1024 * 1024
                custom_mb = float(text)
                if custom_mb <= 0:
                    return 10 * 1024 * 1024
                return int(custom_mb * 1024 * 1024)
            except ValueError:
                return 10 * 1024 * 1024
        
        return 10 * 1024 * 1024

    def view_logs(self):
        """Open the log file for viewing"""
        try:
            log_path = os.path.join(get_logs_directory(), 'game_drop_debug.log')
            self.logger.info(f"Opening log file: {log_path}")
            
            system_info = f"GameDrop v{VERSION}\n"
            system_info += f"Python: {sys.version}\n"
            system_info += f"OS: {os.name} ({sys.platform})\n"
            system_info += f"GPU Encoder: {self.detected_gpu}\n"
            system_info += "-" * 80 + "\n\n"
            
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
        
        dialog = FFmpegDownloadDialog(self, download_ffmpeg_callback)
        result = dialog.exec()
        
        if not self.controller.ffmpeg_available:
            self.drop_button.setEnabled(False)
            self.update_status("FFmpeg not available. Video clipping disabled.", 0)

    def resizeEvent(self, event):
        """Reposition play button and drop zone overlays when window resizes"""
        super().resizeEvent(event)
        # Center the play button on the video container
        if hasattr(self, 'play_overlay_btn') and hasattr(self, 'video_container'):
            container_rect = self.video_container.rect()
            btn_x = (container_rect.width() - self.play_overlay_btn.width()) // 2
            btn_y = (container_rect.height() - self.play_overlay_btn.height()) // 2
            self.play_overlay_btn.move(btn_x, btn_y)
        
        # Size and position the drop zone to fill the video container
        if hasattr(self, 'drop_zone') and hasattr(self, 'video_container'):
            container_rect = self.video_container.rect()
            margin = 20
            self.drop_zone.setGeometry(
                margin,
                margin,
                container_rect.width() - 2 * margin,
                container_rect.height() - 2 * margin
            )
            self.drop_zone.raise_()  # Keep on top
            
            # Ensure play button stays on top of drop zone
            if hasattr(self, 'play_overlay_btn'):
                self.play_overlay_btn.raise_()
    
    def showEvent(self, event):
        """Position play button when window first shows"""
        super().showEvent(event)
        # Trigger resize to position the play button
        QTimer.singleShot(100, lambda: self.resizeEvent(None))

    # ============================================
    # DRAG AND DROP SUPPORT
    # ============================================
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events for video file drops"""
        mime_data = event.mimeData()
        formats = mime_data.formats()
        self.logger.debug(f"Drag enter event. Formats: {formats}")
        
        if mime_data.hasUrls():
            self.logger.debug(f"URLs found: {[u.toString() for u in mime_data.urls()]}")
            for url in mime_data.urls():
                file_path = url.toLocalFile()
                # Fallback: sometimes toLocalFile() is empty on Wayland/Qt6 for some paths
                if not file_path and url.scheme() == 'file':
                    file_path = url.path()
                
                self.logger.debug(f"Checking file candidate: {file_path}")
                if file_path and file_path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.webm', '.wmv')):
                    event.acceptProposedAction()
                    return
        
        # Fallback check
        elif mime_data.hasFormat('text/uri-list'):
            self.logger.debug("Format text/uri-list detected (potential file drop)")
            event.acceptProposedAction()
            return
            
        event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move events - required for Wayland to keep accepting"""
        # Robust check to ensure we keep accepting the drag during movement
        should_accept = event.mimeData().hasUrls() or event.mimeData().hasFormat('text/uri-list')
        
        # Uncomment to debug high-frequency move events (can be spammy)
        # self.logger.debug(f"Drag move. Accept: {should_accept}")
        
        if should_accept:
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events to load video files"""
        self.logger.debug("Drop event received")
        mime_data = event.mimeData()
        
        paths_to_check = []
        
        # Method 1: Standard URL extraction
        if mime_data.hasUrls():
            for url in mime_data.urls():
                fpath = url.toLocalFile()
                if not fpath and url.scheme() == 'file':
                    fpath = url.path()
                if fpath:
                    paths_to_check.append(fpath)
                    
        # Method 2: Manual URI list parsing if Method 1 yielded nothing useful but format exists
        if not paths_to_check and mime_data.hasFormat('text/uri-list'):
            try:
                data = bytes(mime_data.data('text/uri-list')).decode('utf-8')
                for line in data.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    if line.startswith('file://'):
                        # rudimentary parsing if needed
                        paths_to_check.append(QUrl(line).toLocalFile())
                    else:
                        paths_to_check.append(line)
            except Exception as e:
                self.logger.error(f"Error parsing uri-list: {e}")

        self.logger.info(f"Processing drop candidates: {paths_to_check}")

        for file_path in paths_to_check:
            if file_path and file_path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.webm', '.wmv')):
                self.logger.info(f"Valid video file dropped: {file_path}")
                self.video_path = file_path
                self.controller.load_video(file_path)
                self.range_slider.lower_value = 0
                self.range_slider.upper_value = 100
                self.range_slider.update()
                event.acceptProposedAction()
                return
                
        self.logger.warning("Drop event ignored - no valid video files found in payload")
        event.ignore()

    def eventFilter(self, watched, event):
        """Filter events to intercept drag/drop for the video widget and other containers"""
        if event.type() == QEvent.DragEnter:
            self.dragEnterEvent(event)
            return True # We handled it
        elif event.type() == QEvent.DragMove:
            self.dragMoveEvent(event)
            return True
        elif event.type() == QEvent.Drop:
            self.dropEvent(event)
            return True
        
        return super().eventFilter(watched, event)

    # ============================================
    # WINDOW RESIZE SUPPORT (Wayland-compatible)
    # ============================================
    
    def _get_resize_edge(self, pos):
        """Determine which edge/corner the mouse is near for resizing"""
        rect = self.rect()
        margin = self._resize_margin
        
        edges = Qt.Edges()
        
        if pos.x() <= margin:
            edges |= Qt.LeftEdge
        elif pos.x() >= rect.width() - margin:
            edges |= Qt.RightEdge
            
        if pos.y() <= margin:
            edges |= Qt.TopEdge
        elif pos.y() >= rect.height() - margin:
            edges |= Qt.BottomEdge
            
        return edges
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for edge/corner resizing"""
        if event.button() == Qt.LeftButton:
            edges = self._get_resize_edge(event.pos())
            if edges:
                window = self.windowHandle()
                if window:
                    window.startSystemResize(edges)
                event.accept()
                return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Update cursor based on resize edge position"""
        edges = self._get_resize_edge(event.pos())
        
        if edges == (Qt.LeftEdge | Qt.TopEdge) or edges == (Qt.RightEdge | Qt.BottomEdge):
            self.setCursor(QCursor(Qt.SizeFDiagCursor))
        elif edges == (Qt.RightEdge | Qt.TopEdge) or edges == (Qt.LeftEdge | Qt.BottomEdge):
            self.setCursor(QCursor(Qt.SizeBDiagCursor))
        elif edges & (Qt.LeftEdge | Qt.RightEdge):
            self.setCursor(QCursor(Qt.SizeHorCursor))
        elif edges & (Qt.TopEdge | Qt.BottomEdge):
            self.setCursor(QCursor(Qt.SizeVerCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
            
        super().mouseMoveEvent(event)