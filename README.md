[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/andrewhiser)

<p align="center">
  <img src="gamedrop/assets/logo.png" alt="Game Drop Logo" width="150">
</p>

### <p align="center">Stop Waiting. Stop Paying. Start Sharing.</p>

**Game Drop** is a high-performance, open-source tool built to solve the #1 frustration for gamers: **The Discord File Limit.** While web-based tools make you wait in queues, upload private data, and charge for "priority access," Game Drop uses the raw power of your own GPU to compress and send clips to Discord in seconds, locally, privately, and for free.

<p align="center">
  <img src="gamedrop/assets/Game Drop.png" alt="Game Drop Interface">
</p>

---

## The Ultimate Benchmark: Local GPU vs. The Web

We tested Game Drop against the leading web alternative using a mid-range gaming rig (**RTX 3080 Ti / Ryzen 7 7800X3D**) to see who handles a high-quality 1440p gaming highlight better. 

### **The Source Clip**
- **Original Resolution:** 2560 x 1440 (2K)
- **Length:** 51 seconds
- **Frame Rate:** 60 FPS
- **Bitrate:** ~27 Mbps
- **File Size:** 179.9 MB

### **Performance Comparison**
By separating **Transcode Time** from **Wait Time**, we can see the true speed of local encoding. Even if you bypass the queue on a web service, local hardware delivers a faster and higher-quality result.

| Metric | **Leading Web Tools** (Cloud) | **Game Drop** (Local) | The Advantage |
| :--- | :--- | :--- | :--- |
| **Wait Time (Queue)** | ~2m 19s | **0s (Instant)** | No waiting for servers |
| **Transcode Time** | ~1m 03s | **0m 29s** | **2.1x faster encoding** |
| **Total Time** | **~3m 22s** | **0m 29s** | **~7x faster overall** |
| **Output FPS** | 30 FPS (Choppy) | **60 FPS (Smooth)** | Better viewing experience |
| **Workflow** | Manual Up/Down/Up | **1-Click Auto-Send** | Zero friction |
| **Cost** | $$$ for "Priority" | **Free** | Use the hardware you own |

---

## Features

- **Instant GPU Processing**: No queues. No uploads. Your transcode starts the moment you click "Drop It" using NVIDIA NVENC, AMD AMF, or Intel VA-API.
- **Discord OAuth2 Integration**: Securely connect your Discord account for seamless, one-click sharing.
- **Drag and Drop Videos**: Added a Drag and Drop feature to load videos into the player.
- **Preserve Quality**: Priority GPU encoding keeps your clips at a smooth **60 FPS**, unlike web tools that often cap at 30 FPS.
- **Smart Scaling & Formats**:
  - **Original**: Maintain your aspect ratio including 21:9.
  - **Landscape (16:9)**: Standard wide-screen.
  - **Vertical (9:16)**: Perfect for TikTok, Reels, and YouTube Shorts.
- **Extra Quality Mode**: Premium encoding path for maximum visual fidelity when file size isn't the only concern.
- **Privacy First**: Your highlights never leave your machine until you send them. 100% local processing.
- **Updates**: Never miss a feature. An option to check for updates is now available.
- **FFmpeg Auto-Setup**: Don't worry about dependencies. Game Drop detects and offers to download FFmpeg automatically.
- **Steam Deck Ready**: Fully optimized for Linux and SteamOS environments.

---

## See It In Action
[![Watch the video](https://img.youtube.com/vi/fFhfKb545To/maxresdefault.jpg)](https://www.youtube.com/watch?v=fFhfKb545To)

---

## Download & Setup

### Windows
1. **Download:** [GameDrop](https://github.com/ahiser24/GameDrop/releases/latest)
2. Run the installer and launch the app.
3. If prompted for FFmpeg, click **YES** to automatically set up the core engine.

### Linux & Steam Deck
1. **Download:** [GameDrop](https://github.com/ahiser24/GameDrop/releases/latest)
2. Right-click the file, go to **Properties > Permissions**, and check **Allow executing file as program**.
3. Double-click to launch!

---

## How to Use

1. **Connect Discord**: Click the Discord button to securely authorize Game Drop (one-time setup).
2. **Load Video**: Drag your video directly into the player or click **Load Video**.
3. **Select Range**: Use the dual-handle slider to crop the perfect moment.
4. **Choose Format**: Select Original, Landscape, or **Vertical (Shorts)**.
5. **Drop It**: Click the button to transcode. If "Send to Discord" is checked, it goes straight to your server!

### Managing Webhooks
For power users who want to send to multiple channels simultaneously:
1. Go to **Server Settings > Integrations > Webhooks** in Discord.
2. Create a Webhook and copy the URL.
3. In Game Drop, click **Webhooks** to add and manage your destination channels.

---

## SYSTEM REQUIREMENTS

### MINIMUM
- **OS:** Windows 10/11 or Modern Linux (Ubuntu, Arch, SteamOS)
- **PROCESSOR:** 64-bit Multi-core CPU
- **MEMORY:** 4 GB RAM
- **GRAPHICS:** Integrated Graphics (NVIDIA NVENC, AMD AMF, or VA-API support recommended)
- **STORAGE:** 500 MB available space

**NOTE:** *Software encoding (CPU-only) is supported but significantly slower than GPU acceleration.*

---

## License & Disclaimers
- This project is licensed under the **MIT License**.
- Benchmarks reflect comparisons with popular web-based services as of early 2026.
- **Discord** is a trademark of Discord Inc. Game Drop is not affiliated with, endorsed by, or sponsored by Discord Inc.


