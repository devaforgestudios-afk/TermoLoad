# TermoLoad - Download Manager

A powerful, terminal-based download manager built with Python and Textual. TermoLoad provides a beautiful TUI (Text User Interface) for managing multiple downloads with features like concurrent downloads, speed limiting, and automatic shutdown.

## ✨ Features

- **📥 Multi-Protocol Support**: Download files via HTTP/HTTPS
- **⚡ Concurrent Downloads**: Download multiple files simultaneously with configurable concurrency
- **🎯 Speed Control**: Set download speed limits (KB/s)
- **📊 Real-time Progress**: Live progress tracking with speed and ETA
- **💾 Smart Resume**: Automatic pause on exit and resume on next launch (HTTP Range support)
- **🔄 Auto-Shutdown**: Optionally shutdown your PC when all downloads complete
- **📋 Logs**: Built-in logging with file and in-app log viewer (last 20 lines)
- **⚙️ Persistent Settings**: Save your preferences to `settings.json`
- **🎨 Beautiful TUI**: Clean, modern terminal interface powered by Textual

## 📋 Requirements

- Python 3.8 or higher
- Windows, macOS, or Linux

## 🚀 Installation

1. **Clone the repository**:
```bash
git clone https://github.com/devaforgestudios-afk/TermoLoad.git
cd TermoLoad
```

2. **Install dependencies**:
```bash
pip install textual aiohttp aiofiles
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
├── downloads_state.json    # Saved downloads state (auto-generated)
├── termoload.log          # Application logs
├── downloads/             # Default download folder
└── README.md              # This file
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

Active and past downloads are saved to `downloads_state.json` so progress is preserved across restarts. Example entry:

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

## 📧 Contact

- GitHub: [@devaforgestudios-afk](https://github.com/devaforgestudios-afk)
- Repository: [TermoLoad](https://github.com/devaforgestudios-afk/TermoLoad)

---

**Happy Downloading! 🚀**
