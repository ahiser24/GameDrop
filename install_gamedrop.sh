#!/bin/bash

APP_NAME="GameDrop"
APPIMAGE_FILENAME="${APP_NAME}.AppImage"
ICON_SOURCE_FILENAME="logo.png"
DESKTOP_FILENAME="${APP_NAME,,}.desktop" # creates gamedrop.desktop
ICON_SIZE_DIR="256x256" # The logo is a 256x256 icon, adjust if yours is different

# --- Target Locations ---
# User-specific application directory
INSTALL_DIR_APPIMAGE="${HOME}/Applications"
# Standard directory for user-specific .desktop files
INSTALL_DIR_DESKTOP="${HOME}/.local/share/applications"
# Standard base directory for user-specific icons (following Freedesktop spec)
INSTALL_DIR_ICON_BASE="${HOME}/.local/share/icons/hicolor"
INSTALL_DIR_ICON="${INSTALL_DIR_ICON_BASE}/${ICON_SIZE_DIR}/apps"

# Determine the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_APPIMAGE_PATH="${SCRIPT_DIR}/${APPIMAGE_FILENAME}"
SOURCE_ICON_PATH="${SCRIPT_DIR}/gamedrop/assets/logo.png"

echo "--- ${APP_NAME} AppImage Installer ---"

# Check if AppImage exists in the script's directory
if [ ! -f "${SOURCE_APPIMAGE_PATH}" ]; then
    echo "Error: ${APPIMAGE_FILENAME} not found in ${SCRIPT_DIR}."
    echo "Please place this script in the same directory as ${APPIMAGE_FILENAME} and ${ICON_SOURCE_FILENAME}."
    exit 1
fi

# Check if icon exists in the script's directory
if [ ! -f "${SOURCE_ICON_PATH}" ]; then
    echo "Error: ${ICON_SOURCE_FILENAME} not found in ${SCRIPT_DIR}."
    echo "Please place this script in the same directory as ${APPIMAGE_FILENAME} and ${ICON_SOURCE_FILENAME}."
    exit 1
fi

# Confirm with the user before proceeding
read -r -p "Do you want to install ${APP_NAME} to your user applications directory (${INSTALL_DIR_APPIMAGE})? [Y/n] " response
response=${response,,} # tolower
if [[ "$response" =~ ^(n|no)$ ]]; then
    echo "Installation cancelled by user."
    exit 0
fi

echo "Creating installation directories (if they don't exist)..."
mkdir -p "${INSTALL_DIR_APPIMAGE}"
mkdir -p "${INSTALL_DIR_DESKTOP}"
mkdir -p "${INSTALL_DIR_ICON}"

TARGET_APPIMAGE_PATH="${INSTALL_DIR_APPIMAGE}/${APPIMAGE_FILENAME}"
echo "Copying ${APPIMAGE_FILENAME} to ${TARGET_APPIMAGE_PATH}..."
cp "${SOURCE_APPIMAGE_PATH}" "${TARGET_APPIMAGE_PATH}"
echo "Making ${APPIMAGE_FILENAME} executable..."
chmod +x "${TARGET_APPIMAGE_PATH}"

TARGET_ICON_PATH="${INSTALL_DIR_ICON}/${ICON_SOURCE_FILENAME}"
echo "Copying icon ${ICON_SOURCE_FILENAME} to ${TARGET_ICON_PATH}..."
cp "${SOURCE_ICON_PATH}" "${TARGET_ICON_PATH}"

echo "Creating .desktop file at ${INSTALL_DIR_DESKTOP}/${DESKTOP_FILENAME}..."
# Create the .desktop file content
# Note: The 'Icon' field uses the base name of the icon file (without extension)
# as per Freedesktop spec, assuming it's placed in a standard icon theme path.
cat > "${INSTALL_DIR_DESKTOP}/${DESKTOP_FILENAME}" << EOF
[Desktop Entry]
Version=1.0.0
Type=Application
Name=${APP_NAME}
Comment=Revolutionize Your Gameplay Highlights with Smart Clipping and Seamless Discord Sharing!
Exec=${TARGET_APPIMAGE_PATH}
Icon=${APP_NAME,,}
Categories=Utility;VideoEditor;Game;
Terminal=false
Path=${INSTALL_DIR_APPIMAGE}
StartupWMClass=${APP_NAME}
EOF
# Set appropriate permissions for the .desktop file
chmod 644 "${INSTALL_DIR_DESKTOP}/${DESKTOP_FILENAME}"

echo "Updating desktop application database..."
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database -q "${INSTALL_DIR_DESKTOP}"
else
    echo "Warning: 'update-desktop-database' command not found. You might need to log out and back in for the application to appear in your menu."
fi

echo "Updating icon cache..."
if command -v gtk-update-icon-cache &> /dev/null; then
    # Check if the directory exists before trying to update its cache
    if [ -d "${INSTALL_DIR_ICON_BASE}" ]; then
        gtk-update-icon-cache -q -f -t "${INSTALL_DIR_ICON_BASE}"
    fi
else
    echo "Warning: 'gtk-update-icon-cache' command not found. The icon may not appear immediately or you might need to log out and back in."
fi

echo ""
echo "${APP_NAME} has been installed successfully!"
echo "You should be able to find it in your application menu."
echo "If not, please try logging out and logging back in, or restarting your desktop environment."
echo "Application installed at: ${TARGET_APPIMAGE_PATH}"
exit 0