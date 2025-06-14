#!/usr/bin/env python
"""
Game Drop Launcher
------------------
This script is the main entry point for launching the Game Drop application directly from the root folder.

Key responsibilities:
- Ensures the current directory is in the Python path so imports work correctly
- Checks if FFmpeg is available (required for video processing)
- If FFmpeg is missing, notifies the user that the app will prompt for download
- Imports and runs the main Game Drop application
- Handles and reports import or runtime errors in a user-friendly way
"""

import sys
import os
import logging

# Ensure the current directory (project root) is in the Python path
# This allows running the script from the root folder without install
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Try to import and launch the Game Drop application
try:
    # Check if FFmpeg is available before starting the app
    # FFmpeg is required for all video clipping and compression features
    from gamedrop.utils.ffmpeg_wrapper import check_ffmpeg_available
    if not check_ffmpeg_available():
        # If FFmpeg is not found, print a message
        # The app will show a dialog to help the user download FFmpeg
        print("FFmpeg not found. The application will prompt you to download it.")
    
    # Import the main entry point for the Game Drop app
    from gamedrop.__main__ import main
    # Start the application (this will block until the app exits)
    sys.exit(main())

except ImportError as e:
    # If any Game Drop modules fail to import, print a clear error message
    print(f"Error importing Game Drop modules: {e}")
    print("Make sure you have installed all dependencies from requirements.txt")
    sys.exit(1)

except Exception as e:
    # Catch any other errors that occur during startup
    print(f"Error starting Game Drop: {e}")
    sys.exit(1)