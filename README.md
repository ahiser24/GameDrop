<p align="center">
  <img src="gamedrop/assets/logo.png" alt="Game Drop Logo" width="150">
</p>


## <p style="text-align: center;">Game Drop</p>

Revolutionize Your Gameplay Highlights with Smart Clipping and Seamless Discord Sharing!


<p align="center">
  <img src="gamedrop/assets/Game Drop.png" alt="Game Drop Logo">
</p>

## Features

- **Video Clipping**: Easily select portions of your gameplay videos with precise control
- **Discord-Optimized Compression**: Automatically targets Discord's 10MB file limit for direct sharing
- **Hardware Acceleration**: Utilizes NVIDIA (NVENC), AMD (AMF), Intel, or VA-API GPU encoding
- **Custom Export Options**: Adjustable file sizes and quality settings for non-Discord purposes
- **One-click Discord Integration**: Send clips directly to your Discord servers via webhooks
- **Cross-Platform Support**: Works on Windows, Linux, and Steam Deck
- **Dark-mode Interface**: Clean, modern dark UI designed for gamers

## Getting Started Video
[![Watch the video](https://img.youtube.com/vi/jyNgILNK-KI/maxresdefault.jpg)](https://www.youtube.com/watch?v=jyNgILNK-KI)

### Installation
## Download

#### Windows
1. **Windows Installer (v1.0.0):** [Download GameDrop_Setup.zip](https://github.com/ahiser24/GameDrop/releases/download/v1.0.0/GameDrop_Setup.zip)
2. Extract the files
3. Run the installer and follow the on-screen instructions
4. Launch Game Drop

#### Linux & Steam Deck
1. **Linux Version (v1.0.0):** [Download GameDrop_Setup.tar.gz](https://github.com/ahiser24/GameDrop/releases/download/v1.0.0/GameDrop_Setup.tar.gz)
2. Extract the files
3. Run install_GameDrop.sh and follow the on-screen instructions
4. Launch Game Drop

### Using Game Drop
1. Click **Load Video** to open a gameplay video file
2. Use the slider to select the start and end points of your clip
3. For Discord sharing without Nitro:
   - Keep "Opitimize for discord" checked
   - (Optional) Set up Discord webhooks by clicking **Manage Webhooks**
   - Add an optional custom clip name
4. For longer clips:
   - Uncheck "Opitimize for discord" to access size and quality options
   - Select your desired file size or enter a custom value
   - Add an optional custom clip name
5. Click **Drop It** to create your clip (and send to Discord if webhooks are configured)

### Setting Up Discord Webhooks

1. In your Discord server, go to **Server Settings** > **Integrations** > **Webhooks**
2. Click **New Webhook**, give it a name, and select the channel where clips will be posted
3. Copy the webhook URL
4. In Game Drop, click **Manage Webhooks**, then **Add Webhook**
5. Enter a name for the webhook and paste the URL

## System Requirements

### Windows
- Windows 10 or later
- 4GB RAM (8GB recommended)
- DirectX 11 compatible graphics card
- FFmpeg (automatically downloaded if not found)

### Linux
- Modern Linux x64 distribution (Ubuntu 20.04+, Arch, Fedora 34+, SteamOS)
- 4GB RAM (8GB recommended)
- Mesa drivers for AMD/Intel GPUs or NVIDIA proprietary drivers
- FFmpeg (automatically downloaded if not found)

### Recommended
- NVIDIA, AMD, or Intel GPU that supports hardware-accelerated H.264 encoding
- Internet connection for Discord uploads

## Troubleshooting

- **FFmpeg Missing**: Game Drop will automatically download and install FFmpeg if it's not detected
- **Video Won't Load**: Make sure your video is in a supported format (MP4, AVI, MKV, MOV)
- **Discord Upload Failing**: Verify your webhook URL and internet connection
- **Quality Issues**: For better quality but larger files, uncheck the Discord limit and select a higher file size
- **Hardware Acceleration Not Working**: Update your graphics drivers

## Project Structure

The application follows a modular architecture for better maintainability:

```
gamedrop/
  ├── __main__.py                 # Application entry point
  ├── version.py                  # Sets the version number
  ├── core/                       # Core functionality
  │   ├── app_controller.py       # Main application controller
  │   ├── media_controller.py     # Video playback functionality
  │   └── video_processor.py      # Video compression and export
  ├── platform_utils/             # Platform detection utilities
  ├── ui/                         # User interface components
  │   ├── dialogs.py              # Dialog windows
  │   ├── main_window.py          # Main application window
  │   └── range_slider.py         # Custom slider for selecting clip range
  └── utils/                      # Utility modules
      ├── ffmpeg_wrapper.py       # FFmpeg integration
      ├── gpu/                    # GPU detection and selection
      └── paths.py                # Resource path handling
```

## Development

### Prerequisites

- Python 3.8 or later
- PySide6 (Qt for Python)
- FFmpeg (automatically downloaded if not present)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/ahiser24/gamedrop.git
cd gamedrop
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python game_drop.py
```

### Building

#### Windows Executable
- Run build_windows.bat
- To create an installer, run the GameDrop.iss file with Inno Installer

#### Linux AppImage
- Run build_appimage.sh
- To create .desktop file, run install_gamedrop.sh

See [REBUILD_APPIMAGE.md](REBUILD_APPIMAGE.md) for detailed Linux build instructions.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
