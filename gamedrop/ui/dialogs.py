"""
Dialog components for GameDrop application

This module contains custom dialog classes for the GameDrop application UI. These dialogs handle user interactions for managing Discord webhooks, viewing application logs, and downloading FFmpeg. Each dialog is implemented as a subclass of QDialog from PySide6, with detailed UI layouts and logic for user actions.
"""
import os
import json
import sys
import subprocess
import logging
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QFormLayout, QDialogButtonBox,
                             QPushButton, QCheckBox, QMessageBox, QWidget,
                             QApplication, QTextEdit, QProgressBar)
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtCore import QUrl
from gamedrop.utils.paths import resource_path, get_logs_directory, get_webhooks_path

# Configure logging for this module
logger = logging.getLogger("GameDrop.UI.Dialogs")

# Path for storing webhooks - OS specific
WEBHOOKS_FILE = get_webhooks_path()

class WebhookDialog(QDialog):
    """
    Dialog for managing Discord webhooks.
    Allows users to add, edit, enable/disable, and remove Discord webhooks.
    Webhooks are stored in a JSON file at a platform-specific location.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the WebhookDialog UI and load existing webhooks.
        """
        super().__init__(parent)
        self.setWindowTitle('Discord Webhooks')
        self.setMinimumWidth(500)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

        # Title and description for the dialog
        title_label = QLabel("Manage Discord Webhooks")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        description_label = QLabel("Add, enable, or remove webhooks to automatically send clips to Discord")
        description_label.setStyleSheet("color: #8a8a8a;")
        
        self.layout.addWidget(title_label)
        self.layout.addWidget(description_label)
        self.layout.addSpacing(10)
        
        # Section label for the list of webhooks
        webhooks_label = QLabel("Your Webhooks")
        webhooks_label.setStyleSheet("font-weight: bold;")
        self.layout.addWidget(webhooks_label)
        
        # Layout to hold the list of webhook entries
        self.webhook_list_layout = QVBoxLayout()
        self.load_webhooks()  # Populate the list with existing webhooks
        self.layout.addLayout(self.webhook_list_layout)
        
        # Button to add a new webhook
        self.add_webhook_button = QPushButton('Add Webhook')
        self.add_webhook_button.setIcon(QIcon(resource_path('assets/logo.png')))
        self.add_webhook_button.clicked.connect(self.add_webhook)
        self.add_webhook_button.setMinimumHeight(40)
        self.layout.addWidget(self.add_webhook_button)
        
        self.layout.addStretch(1)

        # OK/Cancel dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)
        
        # Apply parent window styling if available
        if parent:
            self.setStyleSheet(parent.styleSheet())        

    def load_webhooks(self):
        """
        Load webhooks from the JSON file and display them in the dialog.
        Each webhook is shown with a checkbox (enable/disable), edit, and delete buttons.
        """
        # Clear any existing widgets from the list layout
        for i in reversed(range(self.webhook_list_layout.count())): 
            widget = self.webhook_list_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        self.webhook_items = []  # Store tuples of (checkbox, widget) for later reference
        
        if os.path.exists(WEBHOOKS_FILE):
            try:
                with open(WEBHOOKS_FILE, 'r') as f:
                    self.webhooks = json.load(f)
                    
                    if not self.webhooks:
                        # Show message if no webhooks exist
                        no_webhooks_label = QLabel("No webhooks added yet")
                        no_webhooks_label.setStyleSheet("color: #8a8a8a; font-style: italic;")
                        self.webhook_list_layout.addWidget(no_webhooks_label)
                    
                    for name, data in self.webhooks.items():
                        webhook_layout = QHBoxLayout()
                        
                        # Checkbox to enable/disable webhook
                        checkbox = QCheckBox(name)
                        checkbox.setChecked(data.get('checked', False))
                        checkbox.setToolTip(data.get('url', ''))
                        webhook_layout.addWidget(checkbox, 1)
                        
                        # Edit button to modify webhook details
                        edit_button = QPushButton('Edit')
                        edit_button.setFixedWidth(80)
                        edit_button.clicked.connect(lambda _, n=name: self.edit_webhook(n))
                        webhook_layout.addWidget(edit_button)
                        
                        # Delete button to remove webhook
                        delete_button = QPushButton('Delete')
                        delete_button.setFixedWidth(80)
                        delete_button.clicked.connect(lambda _, n=name: self.delete_webhook(n))
                        webhook_layout.addWidget(delete_button)
                        
                        # Container widget for styling
                        webhook_widget = QWidget()
                        webhook_widget.setLayout(webhook_layout)
                        webhook_widget.setStyleSheet("""
                            QWidget {
                                background-color: #2d2d2d; 
                                border-radius: 4px;
                                padding: 4px;
                                margin: 4px;
                            }
                        """)
                        
                        self.webhook_list_layout.addWidget(webhook_widget)
                        self.webhook_items.append((checkbox, webhook_widget))
            except (json.JSONDecodeError, FileNotFoundError):
                # If file is missing or invalid, show empty state
                self.webhooks = {}
                no_webhooks_label = QLabel("No webhooks added yet")
                no_webhooks_label.setStyleSheet("color: #8a8a8a; font-style: italic;")
                self.webhook_list_layout.addWidget(no_webhooks_label)
        else:
            # If file does not exist, show empty state
            self.webhooks = {}
            no_webhooks_label = QLabel("No webhooks added yet")
            no_webhooks_label.setStyleSheet("color: #8a8a8a; font-style: italic;")
            self.webhook_list_layout.addWidget(no_webhooks_label)

    def add_webhook(self):
        """
        Open a dialog to add a new Discord webhook.
        Prompts user for a name and webhook URL, then saves it if valid.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle('Add Discord Webhook')
        dialog.setMinimumWidth(400)
        
        form_layout = QFormLayout()
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(10)
        
        title_label = QLabel("Add New Webhook")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        form_layout.addRow(title_label)
        
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g. My Gaming Server")
        
        url_edit = QLineEdit()
        url_edit.setPlaceholderText("https://discord.com/api/webhooks/...")

        form_layout.addRow('Name:', name_edit)
        form_layout.addRow('Webhook URL:', url_edit)
        
        help_text = QLabel("You can get a webhook URL from Discord Server Settings > Integrations > Webhooks")
        help_text.setStyleSheet("color: #8a8a8a; font-size: 12px;")
        help_text.setWordWrap(True)
        form_layout.addRow(help_text)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(lambda: self.save_webhook(dialog, name_edit.text(), url_edit.text()))
        button_box.rejected.connect(dialog.reject)
        form_layout.addRow(button_box)

        dialog.setLayout(form_layout)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec_()

    def save_webhook(self, dialog, name, url):
        """
        Save a new webhook to the JSON file if both name and URL are provided.
        Shows a warning if either field is empty.
        """
        if name and url:
            self.webhooks[name] = {'url': url, 'checked': True}
            with open(WEBHOOKS_FILE, 'w') as f:
                json.dump(self.webhooks, f)
            dialog.accept()
            self.load_webhooks()
        else:
            QMessageBox.warning(self, 'Error', 'Both name and URL are required')

    def delete_webhook(self, name):
        """
        Prompt the user to confirm deletion of a webhook, then remove it if confirmed.
        Updates the JSON file and UI after deletion.
        """
        confirm = QMessageBox.question(
            self, 
            'Confirm Deletion',
            f'Are you sure you want to delete the webhook "{name}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes and name in self.webhooks:
            del self.webhooks[name]
            with open(WEBHOOKS_FILE, 'w') as f:
                json.dump(self.webhooks, f)
            self.load_webhooks()

    def accept(self):
        """
        Save the enabled/disabled (checked) state for each webhook when dialog is accepted.
        Updates the JSON file with the new states.
        """
        # Update the checked status for all webhooks
        for checkbox, _ in self.webhook_items:
            self.webhooks[checkbox.text()]['checked'] = checkbox.isChecked()
        
        with open(WEBHOOKS_FILE, 'w') as f:
            json.dump(self.webhooks, f)
        super().accept()

    def edit_webhook(self, name):
        """
        Open a dialog to edit an existing webhook's name and URL.
        Pre-fills the dialog with the current values.
        """
        if name not in self.webhooks:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle('Edit Discord Webhook')
        dialog.setMinimumWidth(400)
        
        form_layout = QFormLayout()
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(10)
        
        title_label = QLabel("Edit Webhook")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        form_layout.addRow(title_label)
        
        name_edit = QLineEdit(name)
        url_edit = QLineEdit(self.webhooks[name]['url'])
        
        form_layout.addRow('Name:', name_edit)
        form_layout.addRow('Webhook URL:', url_edit)
        
        help_text = QLabel("You can get a webhook URL from Discord Server Settings > Integrations > Webhooks")
        help_text.setStyleSheet("color: #8a8a8a; font-size: 12px;")
        help_text.setWordWrap(True)
        form_layout.addRow(help_text)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(lambda: self.update_webhook(dialog, name, name_edit.text(), url_edit.text()))
        button_box.rejected.connect(dialog.reject)
        form_layout.addRow(button_box)
        
        dialog.setLayout(form_layout)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec_()
        
    def update_webhook(self, dialog, old_name, new_name, new_url):
        """
        Update an existing webhook with new name and/or URL.
        Handles renaming and prevents duplicate names.
        """
        if not new_name or not new_url:
            QMessageBox.warning(self, 'Error', 'Both name and URL are required')
            return
            
        if new_name != old_name and new_name in self.webhooks:
            QMessageBox.warning(self, 'Error', 'A webhook with this name already exists')
            return
            
        # Remove old webhook if name changed, otherwise just update URL
        if new_name != old_name:
            was_checked = self.webhooks[old_name]['checked']
            del self.webhooks[old_name]
            self.webhooks[new_name] = {'url': new_url, 'checked': was_checked}
        else:
            self.webhooks[new_name]['url'] = new_url
            
        with open(WEBHOOKS_FILE, 'w') as f:
            json.dump(self.webhooks, f)
            
        dialog.accept()
        self.load_webhooks()


class LogViewerDialog(QDialog):
    """Dialog for viewing application logs"""
    
    def __init__(self, parent=None, log_path=None, system_info=None):
        super().__init__(parent)
        self.log_path = log_path
        self.system_info = system_info or ""
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Game Drop Logs")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title and explanation
        title_label = QLabel("Application Logs")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        description_label = QLabel("Review logs to troubleshoot issues. You can copy this content to share with support.")
        description_label.setStyleSheet("color: #8a8a8a;")
        
        # Log display area
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QTextEdit.NoWrap)
        self.log_display.setStyleSheet("""
            background-color: #1a1a1a;
            color: #e0e0e0;
            font-family: monospace;
            padding: 8px;
        """)
        
        # Load log content
        self.load_log_content()
        
        # Buttons
        button_layout = QHBoxLayout()
        copy_button = QPushButton("Copy to Clipboard")
        copy_button.clicked.connect(self.copy_to_clipboard)
        
        open_file_button = QPushButton("Open Log File")
        open_file_button.clicked.connect(self.open_log_file)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(copy_button)
        button_layout.addWidget(open_file_button)
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)
        
        # Add widgets to layout
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addWidget(self.log_display, 1)
        layout.addLayout(button_layout)
        
        # Apply styling if parent exists
        if self.parent():
            self.setStyleSheet(self.parent().styleSheet())
    
    def load_log_content(self):
        """Load log content from file"""
        try:
            if not self.log_path or not os.path.exists(self.log_path):
                self.log_display.setText("Log file not found.")
                return
                
            with open(self.log_path, 'r') as f:
                log_content = f.read()
                self.log_display.setText(self.system_info + log_content)
        except Exception as e:
            self.log_display.setText(f"Error reading log file: {str(e)}")
            
    def copy_to_clipboard(self):
        """Copy log content to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_display.toPlainText())
        
    def open_log_file(self):
        """Open the log file with system default application"""
        if not self.log_path or not os.path.exists(self.log_path):
            QMessageBox.warning(self, "Error", "Log file not found")
            return
            
        try:
            # Use QDesktopServices for cross-platform and sandbox compatibility
            # This is more reliable than os.startfile or subprocess.run in sandboxed environments like MSIX
            qurl_path = QUrl.fromLocalFile(self.log_path)
            
            if not QDesktopServices.openUrl(qurl_path):
                logger.error(f"QDesktopServices.openUrl failed for {qurl_path.toString()}")
                QMessageBox.warning(self, "Error", "Could not open the log file with the default application.")

        except Exception as e:
            logger.error(f"General error when trying to open log file: {str(e)}")
            QMessageBox.warning(self, "Error", f"Could not open log file: {str(e)}")


class FFmpegDownloadDialog(QDialog):
    """Dialog for downloading FFmpeg"""
    
    def __init__(self, parent=None, download_callback=None):
        super().__init__(parent)
        self.download_callback = download_callback
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("FFmpeg Not Found")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Message
        label = QLabel(
            "FFmpeg is required for video clipping and compression.\n\n" +
            "FFmpeg was not found on your system.\n" +
            "Would you like to download and install FFmpeg now?\n\n" +
            "You can also install FFmpeg manually and restart the app."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        
        # Buttons
        btns = QDialogButtonBox()
        self.download_btn = btns.addButton("Download FFmpeg", QDialogButtonBox.AcceptRole)
        self.cancel_btn = btns.addButton(QDialogButtonBox.Cancel)
        layout.addWidget(btns)
        
        # Progress bar (initially hidden)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Connect signals
        self.download_btn.clicked.connect(self.download_ffmpeg)
        self.cancel_btn.clicked.connect(self.reject)
        
        # Apply styling if parent exists
        if self.parent():
            self.setStyleSheet(self.parent().styleSheet())
    
    def download_ffmpeg(self):
        """Start FFmpeg download process"""
        if not self.download_callback:
            self.reject()
            return
            
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        
        # Start download with progress updates
        try:
            success = self.download_callback()
            if success:
                self.accept()
            else:
                QMessageBox.warning(self, "Download Failed", "Could not download FFmpeg. See logs for details.")
                self.reject()
        except Exception as e:
            QApplication.processEvents()  # Process UI events
            QMessageBox.warning(self, "Download Failed", f"Could not download FFmpeg: {str(e)}")
            self.reject()