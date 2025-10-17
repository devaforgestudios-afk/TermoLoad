# TermoLoad - Download Manager

A powerful, terminal-based download manager built with Python and Textual. TermoLoad provides a beautiful TUI (Text User Interface) for managing multiple downloads with features like concurrent downloads, speed limiting, and automatic shutdown.

## ✨ Features

- **📥 Multi-Protocol Support**: Download files via HTTP/HTTPS and videos via yt-dlp
- **🎬 YouTube & More (yt-dlp)**: Paste a YouTube (and many other sites) URL; downloads use the video title as the filename and merge best video+audio
- **⚡ Concurrent Downloads**: Download multiple files simultaneously with configurable concurrency
- **🎯 Speed Control**: Set download speed limits (KB/s)
- **📊 Real-time Progress**: Live progress tracking with speed and ETA
- **💾 Smart Resume**: Automatic pause on exit and resume on next launch (HTTP Range support)
- **🔄 Auto-Shutdown**: Optionally shutdown your PC when all downloads complete
- **📋 Logs**: Built-in logging with file and in-app log viewer (last 20 lines)
- **⚙️ Persistent Settings**: Save your preferences to `settings.json`
- **🎨 Beautiful TUI**: Clean, modern terminal interface powered by Textual
- **System Tray Support**: Minimize to Windows system tray (press 'm' or click Minimize button)
  - Right-click tray icon to show/hide or check active downloads
  - Downloads continue in the background

## 📋 Requirements (For developers or contribution)

- Python 3.8 or higher
- Windows, macOS, or Linux
- Optional for YouTube/video: yt-dlp (and ffmpeg for best results when merging audio/video)

## 🚀 Installation

1. **Clone the repository (For developers/contributions)**:
```bash
git clone https://github.com/devaforgestudios-afk/TermoLoad.git
cd TermoLoad
```

2. **Install dependencies (For developers/contributions)**:
```bash
pip install yt-dlp
pip install textual
pip install random
pip install asyncio
pip install aiohttp
pip install aiofiles
pip install os
pip install pathlib
pip install urllib
pip install json
pip install time
pip install tkinter as tk
pip install sys
pip install subprocess
pip install logging
pip install collection
pip install typing
```

3. **Run the application**:
```bash
python app.py
```

## 🎮 Usage

### Keyboard Shortcuts

- `a` - Add new download
- `q` - Quit application
- `^p` - Open command palette

### Adding a Download

1. Click **+ Add Download** button or press `a`
2. Enter the URL of the file to download
3. Specify the save folder (or leave empty for default)
4. Click **Browse** to select a folder via dialog
5. Click **Add** to start the download

### Downloading YouTube or other videos (yt-dlp)

- Paste a YouTube (or any yt-dlp-supported) URL in Add Download.
- TermoLoad automatically routes it through yt-dlp and sets the filename to the actual video title.
- The app uses best video + best audio with mp4 merge when possible.
- Progress is shown with speed and ETA; after download, status briefly shows “Processing” while merging.

Optional setup for best results:
- Install yt-dlp: `pip install yt-dlp`
- Install ffmpeg so yt-dlp can merge video+audio to mp4.
  - Windows (winget): `winget install -e --id Gyan.FFmpeg`
  - Or download from https://ffmpeg.org and add to PATH.

Notes:
- If yt-dlp isn’t installed, TermoLoad will show “Error: yt-dlp not installed” for video URLs and continue to work for normal HTTP/HTTPS downloads.
- Some sites may require cookies/login; advanced yt-dlp options can be added in future versions.

### Navigating Tabs

- **Downloads**: View and monitor active downloads
- **Settings**: Configure download preferences
- **Logs**: View the last 20 log entries
- **Help**: Help and about information

## ⚙️ Settings

Access settings via the **Settings** tab:

### Download Folder
- Set the default folder for all downloads
- Use the **Browse** button to select a folder
- Defaults to `./downloads` if not specified

### Concurrent Downloads
- Number of simultaneous downloads (default: 3)
- Higher values = more parallel downloads but more resource usage

### Max Download Speed
- Set maximum download speed in KB/s
- Set to `0` for unlimited speed

### Shutdown Options
- **Shutdown PC when all downloads complete**: Enable automatic shutdown after completion
- **Allow real system shutdown (dangerous)**: Enable actual system shutdown command
  - ⚠️ **WARNING**: When enabled, your PC will actually shutdown when all downloads finish
  - Keep disabled for testing (simulated shutdown will be logged instead)

### Saving Settings

1. Modify your preferences in the Settings panel
2. Click **Save Settings** to persist changes to `settings.json`
3. Click **Cancel** to discard changes and reload previous settings

## 📁 File Structure

```
TermoLoad/
├── app.py                  # Main application
├── settings.json           # Saved settings (auto-generated)
├── README.md               # This file
└── downloads/              # Default download folder

# State file is saved per-user:
# Windows: C:\Users\<YourUser>\downloads_state.json
# macOS/Linux: ~/downloads_state.json
├── termoload.log          # Application logs
```

## 🔧 Configuration File

Settings are automatically saved to `settings.json`:

```json
{
  "download_folder": "E:\\TermoLoad\\downloads",
  "concurrent": 3,
  "max_speed_kb": 0,
  "shutdown_on_complete": false,
  "allow_real_shutdown": false
}
```

### Downloads State File

Active and past downloads are saved per-user to `~/downloads_state.json` (Windows: `C:\Users\<You>\downloads_state.json`) so progress is preserved across restarts. For backward compatibility, the app will read a legacy `downloads_state.json` from the app folder if present.

Example entry:

```json
{
  "downloads": [
    {
      "id": 1,
      "type": "URL",
      "name": "file.iso",
      "url": "https://example.com/file.iso",
      "path": "E\\\\TermoLoad\\\\downloads",
      "progress": 0.42,
      "status": "Paused",
      "downloaded_bytes": 45112320,
      "total_size": 1073741824,
      "filepath": "E\\\\TermoLoad\\\\downloads\\\\file.iso"
    }
  ]
}
```

On startup, any entries not marked Completed or Error will automatically resume if the server supports HTTP Range requests.

## 📝 Logs

- **File Logs**: All logs are written to `termoload.log`
- **In-App Logs**: View the last 20 lines in the Logs tab
- **Log Levels**: DEBUG, INFO, ERROR

## 🛠️ Troubleshooting

### Downloads Not Starting
- Check that the URL is valid and accessible
- Ensure you have write permissions to the download folder
- Check `termoload.log` for error details

### UI Not Displaying Correctly
- Ensure your terminal supports Unicode and colors
- Try resizing the terminal window
- On Windows, use Windows Terminal for best results

### Shutdown Not Working
- Enable "Shutdown PC when all downloads complete" in Settings
- For actual shutdown, also enable "Allow real system shutdown"
- ⚠️ Test with simulated mode first (default)

### Merged file not mp4
- Some sources provide formats that cannot be merged to mp4; yt-dlp may pick a different container. Installing ffmpeg helps produce mp4 when available.

## 🔒 Safety Features

- **Simulated Shutdown by Default**: Logs "Shut down (simulated)" instead of actually shutting down
- **One-Time Trigger**: Shutdown only triggers once per session
- **Activity Detection**: Won't trigger on startup, only after downloads actually run and complete
- **Manual Override**: Requires explicit settings to enable real shutdown

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Built with [Textual](https://github.com/Textualize/textual) - amazing TUI framework
- Uses [aiohttp](https://github.com/aio-libs/aiohttp) for async HTTP requests
- Uses [aiofiles](https://github.com/Tinche/aiofiles) for async file I/O
- Video downloads powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org)

## 📧 Contact

- GitHub: [@devaforgestudios-afk](https://github.com/devaforgestudios-afk)
- Repository: [TermoLoad](https://github.com/devaforgestudios-afk/TermoLoad)

---

**Happy Downloading! 🚀**
