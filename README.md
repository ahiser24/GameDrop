[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/andrewhiser)

<p align="center">
  <img src="gamedrop/assets/logo.png" alt="Game Drop Logo" width="150">
</p>



### <p align="center">Stop Waiting. Stop Paying. Start Sharing.</p>

**Game Drop** is a high-performance, open-source tool built to solve the #1 frustration for gamers: **The Discord File Limit.** While web-based tools make you wait in queues, upload private data, and charge for "priority access," Game Drop uses the raw power of your own GPU to compress and send clips to Discord in seconds—locally, privately, and for free.

<p align="center">
  <img src="gamedrop/assets/Game Drop.png" alt="Game Drop Interface">
</p>

---

## The Ultimate Benchmark: Local GPU vs. The Web

We tested Game Drop against the leading web alternative using a high-end gaming rig (**RTX 3080 Ti / Ryzen 7 7800X3D**) to see who handles a high-quality 1440p gaming highlight better. 

### **The Source Clip**
- **Original Resolution:** 2560 x 1440 (2K)
- **Length:** 51 seconds
- **Frame Rate:** 60 FPS
- **Bitrate:** ~27 Mbps
- **File Size:** 179.9 MB

### **Performance Comparison**
We separated **Transcode Time** from **Wait Time** to show the true speed of local hardware. Even if you "Skip the Line" on a web service, their servers still can't keep up with your local GPU.

| Metric | **8mb.video** (Web) | **Game Drop** (Local) | The Advantage |
| :--- | :--- | :--- | :--- |
| **Wait Time (22 in Queue)** | 2m 19s | **0s (Instant)** | No waiting for servers |
| **Transcode Time** | 1m 03s | **0m 29s** | **2.1x faster encoding** |
| **Total Time** | **~3m 22s** | **0m 29s** | **~7x faster overall** |
| **Output FPS** | 30 FPS (Choppy) | **60 FPS (Smooth)** | Better viewing experience |
| **Workflow** | Manual Up/Down/Up | **1-Click Auto-Send** | Zero friction |
| **Cost** | $$$ for "Priority" | **Free** | Use the hardware you own |

---

## See It In Action
[![Watch the video](https://img.youtube.com/vi/fFhfKb545To/maxresdefault.jpg)](https://www.youtube.com/watch?v=fFhfKb545To)


---

## Why Choose Game Drop?

- **Instant Processing**: No queues, no "Waiting in Line," and no uploading large source files. Your 30-second transcode starts the moment you click "Drop It."
- **Preserve the Quality**: Most web tools cut your frame rate in half (30 FPS) to save on size. Game Drop prioritizes your GPU's power to keep your clips at a buttery-smooth **60 FPS**.
- **Smart Scaling**: Our system automatically targets the Discord limit, starting at your original resolution and only scaling down (1080p -> 720p -> 480p) if strictly necessary to fit the file size.
- **Discord Native Integration**: Don't just compress—**send**. Game Drop automatically pings your clips directly to your server(s) via Webhooks.
- **Privacy First**: Your gaming highlights never touch a cloud server until they hit Discord. All processing happens 100% locally on your machine.
- **Steam Deck & Linux Ready**: Optimized performance for the best handheld and desktop gaming environments.

---

## Download & Setup

### Windows
1. **Windows Installer:** [Download GameDrop_Setup.zip](https://github.com/ahiser24/GameDrop/releases/latest)
2. Extract and run the installer.
3. If prompted for FFmpeg, click **YES** to automatically download it to %APPDATA%\GameDrop folder.

### Linux & Steam Deck
1. **Linux Version:** [Download GameDrop_Setup.tar.gz](https://github.com/ahiser24/GameDrop/releases/latest)
2. Extract the files and run `install_GameDrop.sh`.
3. Launch the AppImage

---

## How to Use

1. **Load Video**: Select your raw gameplay recording.
2. **Select Range**: Use the visual slider to select the start and end of your highlight.
3. **Drop It**: Start Transcoding
4. **Automated Share**: Game Drop will automatically send the video to all checked webhooks.

### Setting Up Discord Webhooks
1. In Discord: **Server Settings** > **Integrations** > **Webhooks** > **New Webhook**.
2. Copy the Webhook URL.
3. In Game Drop: Click **Manage Webhooks** > **Add Webhook** and paste your URL.

---

## System Requirements

- **OS**: Windows 10+ or Modern Linux (Ubuntu 20.04+, Arch/CachyOS, Fedora 34+, SteamOS).
- **GPU**: NVIDIA, AMD, or Intel GPU with hardware-accelerated H.264 encoding support (NVENC/AMF/VA-API).
- **Internet**: Required for Discord uploads.

---

## License & Disclaimers
This project is licensed under the **MIT License**.

**Disclaimers:**
* **8mb.video** is a trademark of its respective owners. Game Drop is not affiliated with, endorsed by, or sponsored by 8mb.video. Benchmarks reflect performance as of January 2026.
* **Discord** is a trademark of Discord Inc. Game Drop is not affiliated with, endorsed by, or sponsored by Discord Inc.


