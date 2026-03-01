# How to Rebuild the GameDrop AppImage

This document outlines the steps to rebuild the GameDrop AppImage after making changes to the source code.

## Prerequisites

1.  **Linux Environment**: AppImage creation is typically done on Linux.
2.  **Python 3**: Ensure you have Python 3 installed.
3.  **Dependencies**: The build script uses `python3-venv` (often included with Python or installable via your package manager, e.g., `sudo apt install python3-venv` on Debian/Ubuntu).
4.  **Internet Connection**: Required to download `appimagetool` if it's not already present.

## Steps

1.  **Navigate to Project Directory**:
    Open your terminal and change to the root directory of the GameDrop project (the directory containing `build_appimage.sh`).
    ```bash
    cd /path/to/gamedrop
    ```

2.  **Ensure Script is Executable**:
    Make sure the build script has execute permissions.
    ```bash
    chmod +x build_appimage.sh
    ```

3.  **Run the Build Script**:
    Execute the script. You can optionally provide a version number as the first argument. If omitted, it defaults to the version specified within the script (currently "1.0.0").
    ```bash
    # Build with default version
    ./build_appimage.sh

    # Or, build with a specific version (e.g., 1.1.0)
    ./build_appimage.sh 1.1.0
    ```

4.  **Process**:
    The script will perform the following actions:
    *   Set up a Python virtual environment (if it doesn't exist).
    *   Install/update dependencies from `requirements.txt`.
    *   Clean previous build artifacts (`build/`, `dist/`, `*.spec`, `*.AppImage`).
    *   Run PyInstaller using the `GameDrop.spec` file to create a one-directory bundle in `dist/GameDrop`.
    *   Create an `AppDir` structure (`build/GameDrop.AppDir`).
    *   Copy the PyInstaller output into the `AppDir`.
    *   Create necessary files (`AppRun`, `.desktop`, icons).
    *   Download `appimagetool` (if needed).
    *   Use `appimagetool` to package the `AppDir` into the final `.AppImage` file (e.g., `GameDrop-1.0.0-x86_64.AppImage`).

5.  **Result**:
    The final AppImage file will be located in the project's root directory. You can make it executable and run it:
    ```bash
    chmod +x GameDrop-*.AppImage
    ./GameDrop-*.AppImage
    ```

## Notes

*   **`GameDrop.spec`**: If you need to change PyInstaller settings (like adding hidden imports or modifying data file inclusion), edit the `GameDrop.spec` file directly. The build script now uses this file.
*   **Dependencies**: If you add new Python dependencies to your project, make sure to update the `requirements.txt` file before running the build script.
*   **Assets**: Ensure any new assets (images, etc.) are placed within the `gamedrop/assets/` directory, as this is what's configured in `GameDrop.spec` to be included in the bundle.
