#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting Game Drop Flatpak Build Process...${NC}"

# 1. Check for required tools
echo -e "${GREEN}Checking dependencies...${NC}"
for cmd in flatpak flatpak-builder python3 pip3 wget; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Error: '$cmd' is not installed.${NC}"
        echo "Please install it using your distribution's package manager before continuing."
        exit 1
    fi
done

# 2. Add Flathub remote and install KDE runtime/SDK
echo -e "${GREEN}Installing KDE runtime, SDK and PySide BaseApp...${NC}"
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
# 3. Build the Flatpak app
echo -e "${GREEN}Building the Flatpak application...${NC}"
flatpak-builder --repo=repo --force-clean build-dir com.github.ahiser.GameDrop.yml

# 5. Export the Flatpak single-file bundle
echo -e "${GREEN}Exporting to GameDrop.flatpak bundle...${NC}"
flatpak build-bundle repo GameDrop.flatpak com.github.ahiser.GameDrop

echo -e "${GREEN}Build complete!${NC}"
echo "You can now install the application manually using:"
echo "  flatpak install --user GameDrop.flatpak"
echo "Or run it directly from the generated repository:"
echo "  flatpak run com.github.ahiser.GameDrop"
