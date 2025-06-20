#!/bin/bash
# Build script for GameDrop AppImage
# Creates a one-dir PyInstaller build and packages it into an AppImage.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
APP_NAME="GameDrop"
MAIN_SCRIPT="game_drop.py"
PACKAGE_DIR="gamedrop"
ASSETS_DIR="${PACKAGE_DIR}/assets"
ICON_FILE="${ASSETS_DIR}/logo.png" # Use PNG for Linux icon
VERSION="1.1.0" # Default version, can be overridden

# Allow version override from command line argument
if [ ! -z "$1" ]; then
    VERSION=$1
fi

echo "--- Starting GameDrop AppImage Build v${VERSION} ---"

# --- Environment Setup ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for required directories and files
if [ ! -f "$MAIN_SCRIPT" ]; then
    echo "ERROR: Main script '$MAIN_SCRIPT' not found in $SCRIPT_DIR"
    exit 1
fi
if [ ! -d "$PACKAGE_DIR" ]; then
    echo "ERROR: Package directory '$PACKAGE_DIR' not found in $SCRIPT_DIR"
    exit 1
fi
if [ ! -d "$ASSETS_DIR" ]; then
    echo "ERROR: Assets directory '$ASSETS_DIR' not found in $SCRIPT_DIR"
    exit 1
fi
if [ ! -f "$ICON_FILE" ]; then
    echo "WARNING: Icon file '$ICON_FILE' not found. AppImage/Desktop file might lack an icon."
    # Create a dummy icon file to prevent AppImageTool errors if needed
    # touch dummy_icon.png
    # ICON_FILE="dummy_icon.png"
fi

# Optional: Setup and activate virtual environment
VENV_DIR=".venv_build"
if [ ! -d "$VENV_DIR" ]; then
    echo "--- Creating build virtual environment in '$VENV_DIR' ---"
    python3 -m venv "$VENV_DIR"
fi
echo "--- Activating virtual environment ---"
source "$VENV_DIR/bin/activate"

# --- Install Dependencies ---
echo "--- Installing/Updating Dependencies ---"
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller # Ensure PyInstaller is installed

# --- Clean Previous Builds ---
echo "--- Cleaning previous build artifacts ---"
rm -rf build dist "${APP_NAME}-*.AppImage"

# --- PyInstaller Build ---
echo "--- Running PyInstaller ---"
# --onedir: Create a one-directory bundle
# --name: Name of the executable and build directory
# --windowed: Create a GUI application (no console window)
# --add-data: Bundle assets. Format 'source:destination_in_bundle'
#             We map the entire 'gamedrop/assets' dir to 'gamedrop/assets' inside the bundle.
# --icon: Specify the application icon (used by executable, not directly by AppImage/desktop)
# Note: PyInstaller uses the .ico for Windows/macOS, but we specify .png for consistency here.
#       The .desktop file and AppDir structure will handle the Linux icon separately.
# Ensure backslashes are the VERY LAST character on the line for continuation
# pyinstaller --onedir \\
#             --name "$APP_NAME" \\
#             --windowed \\
#             --add-data "${SCRIPT_DIR}/${ASSETS_DIR}:assets" \\ # Corrected destination path
#             --add-data "${SCRIPT_DIR}/${PACKAGE_DIR}:${PACKAGE_DIR}" \\
#             --hidden-import="PySide6.QtCore" \\
#             --hidden-import="PySide6.QtGui" \\
#             --hidden-import="PySide6.QtWidgets" \\
#             --hidden-import="PySide6.QtMultimedia" \\
#             --hidden-import="PySide6.QtMultimediaWidgets" \\
#             --icon="${SCRIPT_DIR}/${ICON_FILE}" \\
#             "$MAIN_SCRIPT"
# Use the spec file instead to ensure consistency
"$VENV_DIR/bin/pyinstaller" GameDrop.spec

# --- AppImage Structure Setup ---
echo "--- Creating AppDir structure ---"
APPDIR="${SCRIPT_DIR}/build/${APP_NAME}.AppDir"
rm -rf "$APPDIR" # Clean any previous AppDir
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

echo "--- Copying PyInstaller output to AppDir ---"
# Copy the entire contents of the PyInstaller dist directory
cp -r "${SCRIPT_DIR}/dist/${APP_NAME}/"* "$APPDIR/usr/bin/"

# --- AppRun Script ---
echo "--- Creating AppRun script ---"
# This script is the entry point for the AppImage.
# It sets up the environment and executes the main application binary.
cat > "$APPDIR/AppRun" <<EOL
#!/bin/bash
HERE=\$(dirname \$(readlink -f "\${0}"))
export PATH="\${HERE}/usr/bin:\${PATH}"
export LD_LIBRARY_PATH="\${HERE}/usr/lib:\${HERE}/usr/bin:\${LD_LIBRARY_PATH}" # Include usr/bin for bundled libs
export XDG_DATA_DIRS="\${HERE}/usr/share:\${XDG_DATA_DIRS}"
export QT_PLUGIN_PATH="\${HERE}/usr/bin/PySide6/plugins:\${QT_PLUGIN_PATH}" # Help Qt find plugins

# Navigate to the binary directory before executing
cd "\${HERE}/usr/bin"

# Execute the main application binary
# Pass all arguments ($@) to the application
exec "./${APP_NAME}" "\$@"
EOL
chmod +x "$APPDIR/AppRun"

# --- Desktop Entry ---
echo "--- Creating .desktop file ---"
# This file tells desktop environments about the application.
DESKTOP_FILE="$APPDIR/usr/share/applications/${APP_NAME,,}.desktop" # Use lowercase name
cat > "$DESKTOP_FILE" <<EOL
[Desktop Entry]
Name=${APP_NAME}
Comment=Revolutionize Your Gameplay Highlights with Seamless Discord Sharing!
Exec=AppRun
Icon=${APP_NAME,,}
Type=Application
Categories=AudioVideo;Video;Utility;
Terminal=false
EOL
# Symlink the .desktop file to the AppDir root (optional but common)
ln -sf "usr/share/applications/${APP_NAME,,}.desktop" "$APPDIR/${APP_NAME,,}.desktop"

# --- Icon Handling ---
echo "--- Copying application icon ---"
if [ -f "$ICON_FILE" ]; then
    # Copy icon to the standard hicolor theme directory
    cp "$ICON_FILE" "$APPDIR/usr/share/icons/hicolor/256x256/apps/${APP_NAME,,}.png"
    # Copy icon to the AppDir root with the lowercase name AppImageTool expects
    cp "$ICON_FILE" "$APPDIR/${APP_NAME,,}.png"
    # Set .DirIcon (used by some file managers to show icon for the AppDir)
    ln -sf "${APP_NAME,,}.png" "$APPDIR/.DirIcon"
else
    echo "WARNING: Icon file not found, skipping icon setup."
fi

# --- AppImageTool ---
echo "--- Downloading AppImageTool ---"
APPIMAGE_TOOL="appimagetool-x86_64.AppImage"
if [ ! -f "$APPIMAGE_TOOL" ]; then
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/${APPIMAGE_TOOL}" -O "$APPIMAGE_TOOL"
    chmod +x "$APPIMAGE_TOOL"
fi

# --- Build AppImage ---
echo "--- Building AppImage ---"
# Set ARCH explicitly to avoid warnings and ensure correct build
export ARCH=x86_64
# Define the output filename as just the app name
OUTPUT_FILENAME="${APP_NAME}.AppImage"

echo "--- Running appimagetool to create ${OUTPUT_FILENAME} ---"
# Use the downloaded tool to package the AppDir. Add verbose flag (-v).
./"$APPIMAGE_TOOL" -v "$APPDIR" "$OUTPUT_FILENAME"

# Check the exit code of appimagetool
if [ $? -ne 0 ]; then
    echo "--- ERROR: appimagetool failed to create the AppImage. ---"
    exit 1
fi

# Check if the AppImage file exists
if [ ! -f "$OUTPUT_FILENAME" ]; then
    echo "--- ERROR: Expected AppImage file ${OUTPUT_FILENAME} not found after running appimagetool. ---"
    exit 1
fi

echo "--- AppImage created successfully: ${OUTPUT_FILENAME} ---"

# --- Deactivate Virtual Env ---
# Deactivate if we sourced it earlier
if command -v deactivate &> /dev/null; then
    echo "--- Deactivating virtual environment ---"
    deactivate
fi

# --- Final Touches ---
# Optional: Clean up build directory
# rm -rf build

echo "--- Build Complete ---"
echo "AppImage created at: ${SCRIPT_DIR}/${OUTPUT_FILENAME}"
echo "To run: chmod +x ${OUTPUT_FILENAME} && ./${OUTPUT_FILENAME}"
echo "Log files on Linux will be stored in: ~/.config/gamedrop/logs/"

