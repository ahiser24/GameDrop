#!/usr/bin/env python
"""
Game Drop - Main Application Entry Point

This module serves as the entry point for the Game Drop application. It handles the initialization of the application, including:
- Setting up the logging system for debugging and error tracking
- Creating the main application window and controller
- Configuring the application-wide icon
- Starting the Qt event loop
"""

import sys
import os
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gamedrop.utils.paths import resource_path, get_logs_directory
from gamedrop.core.app_controller import GameDropController
from gamedrop.ui.main_window import MainWindow

# Set up application-wide logging configuration
# - Logs will be written to both a file and the console
# - Log file location: [logs directory]/game_drop_debug.log
# - Format: timestamp - logger name - log level - message
log_file = os.path.join(get_logs_directory(), 'game_drop_debug.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),  # Write logs to file
        logging.StreamHandler()         # Also output logs to console
    ]
)
logger = logging.getLogger("GameDrop")

def main():
    """
    Main application entry point that initializes and starts the Game Drop application.
    
    This function:
    1. Creates the Qt application instance
    2. Sets up the application icon (loaded from assets/logo.ico)
    3. Initializes the main controller that manages application logic
    4. Creates and displays the main application window
    5. Starts the Qt event loop
    
    Returns:
        int: Application exit code (0 for normal exit, non-zero for errors)
    """
    app = QApplication(sys.argv)
    
    # Load and set the application-wide icon
    # The icon is stored in the assets folder and loaded using the resource_path utility
    icon_path = resource_path('assets/logo.ico')
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    else:
        logger.warning(f"Application icon not found at {icon_path}")
    
    # Initialize the main application controller
    # This handles the core application logic and coordinates between UI and backend
    controller = GameDropController()
    
    # Create and configure the main application window
    # The window is connected to the controller for handling user interactions
    main_window = MainWindow(controller)
    controller.set_main_window(main_window)
    main_window.show()
    
    # Start the Qt event loop and return the application exit code
    return app.exec()

if __name__ == '__main__':
    # Run the application and use its exit code as the process exit code
    sys.exit(main())