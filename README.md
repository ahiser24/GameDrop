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

## Why Choose Game Drop?

- **Instant Processing**: No queues or uploading. Your 30-second transcode starts the moment you click "Drop It."
- **Preserve the Quality**: Most tools cut frame rates to 30 FPS. Game Drop prioritizes GPU power to keep clips at 60 FPS.
- **Smart Scaling**: Targets Discord's 10MB limit by dynamically adjusting resolution only when strictly necessary.
- **Discord Integration**: Skip the upload download process. Automatically send clips directly to your servers via Webhooks.
- **Privacy First**: Your gaming highlights stay local. Processing happens 100% on your machine.
- **Handheld Ready**: Fully optimized for Steam Deck and Linux environments for the best mobile gaming support.

---


## See It In Action
[![Watch the video](https://img.youtube.com/vi/fFhfKb545To/maxresdefault.jpg)](https://www.youtube.com/watch?v=fFhfKb545To)




## Download & Setup

### Windows
1. **Windows:** [Download GameDrop_Setup.zip](https://github.com/ahiser24/GameDrop/releases/latest)
2. Extract and run the installer.
3. If prompted for FFmpeg, click **YES** to automatically download it to %APPDATA%\GameDrop folder.

### Linux & Steam Deck
1. **Linux & Steam Deck:** [Download GameDrop_Setup.tar.gz](https://github.com/ahiser24/GameDrop/releases/latest)
2. Extract the files and run `install_GameDrop.sh`.
3. Launch the AppImage

---

## How to Use

1. **Load Video**: Select your raw gameplay recording.
2. **Select Range**: Use the visual slider to select the start and end of your highlight.
3. **Drop It**: Start Transcoding
4. **Automated Share**: Game Drop will automatically send the video to all checked webhooks.

### Setting Up Discord Webhooks
1. In Discord:
2. Go to **Server Settings** > **Integrations** > **Webhooks**
3. Click **New Webhook**, give it a name, and select the target channel
4. Copy the Webhook URL.
5. In Game Drop:
6. Click **Manage Webhooks**, then  **Add Webhook**
7. Enter a nickname and paste your copied URL.
8. Toggle the checkbox to enable sharing to that channel.

---

## SYSTEM REQUIREMENTS

### MINIMUM REQUIREMENTS
**Requires a 64-bit processor and operating system**

* **OS:** Windows 10 or Modern Linux (Ubuntu, Arch, SteamOS)
* **PROCESSOR:** 64-bit Multi-core Processor
* **MEMORY:** 4 GB RAM
* **GRAPHICS:** Integrated Graphics (NVIDIA NVENC, AMD AMF, or VA-API support recommended)
* **NETWORK:** Broadband Internet connection to send data to Discord
* **STORAGE:** 500 MB available space

**ADDITIONAL NOTES:**
*Software encoding (CPU-only) is supported but significantly slower without a supported GPU.*

---

## License & Disclaimers
* This project is licensed under the **MIT License**.
* Benchmarks reflect comparisons with popular web-based compression services as of January 2026.
* **Discord** is a trademark of Discord Inc. Game Drop is not affiliated with, endorsed by, or sponsored by Discord Inc.

