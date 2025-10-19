# TermoLoad - Download Manager

A powerful, terminal-based download manager built with Python and Textual. TermoLoad provides a beautiful TUI (Text User Interface) for managing multiple downloads with features like concurrent downloads, torrent support, speed limiting, download history, and automatic shutdown.

## 🚀 Quick Start

```bash
# Install dependencies
pip install textual aiohttp aiofiles Pillow pystray
pip install libtorrent  # Optional: For torrent support
pip install yt-dlp      # Optional: For video downloads

# Run
python app.py
```

**Key Features**: HTTP/HTTPS downloads • BitTorrent (magnets + .torrent) • YouTube/Video (yt-dlp) • Download History • Statistics • Resume Support • Smart Delete • Sound Notifications • System Tray • Open Folder

## ✨ Features

### Core Download Features
- **📥 Multi-Protocol Support**: Download files via HTTP/HTTPS, torrents (magnet/torrent files), and videos via yt-dlp
- **🧲 Torrent Support**: Full BitTorrent support with magnet links and .torrent files
  - Real-time peer/seed count display
  - DHT, PeX, and LSD support
  - Automatic metadata fetching for magnets
  - Resume support for incomplete torrents
- **🎬 YouTube & More (yt-dlp)**: Paste a YouTube (and many other sites) URL; downloads use the video title as the filename and merge best video+audio
- **⚡ Concurrent Downloads**: Download multiple files simultaneously with configurable concurrency
- **🎯 Speed Control**: Set download speed limits (KB/s)
- **📊 Real-time Progress**: Live progress tracking with speed, ETA, and peers/seeds for torrents
- **💾 Smart Resume**: Automatic pause on exit and resume on next launch (HTTP Range support + torrent resume)

### UI & User Experience
- **🎨 Beautiful TUI**: Clean, modern terminal interface powered by Textual
- **� Optimized Layout**: Downloads section at the top with maximum screen space
- **🎯 Stable Selection**: Smart interaction lock prevents selection jumping while clicking (3-second hold)
- **🖱️ Click & Hold**: Click any download and it stays selected while you interact
- **📊 Wide Columns**: Full-width table with optimized column sizes for better visibility
- **System Tray Support**: Minimize to Windows system tray (press 'm' or click Minimize button)
  - Right-click tray icon to show/hide or check active downloads
  - Downloads continue in the background

### Management & Tracking
- **📜 Download History**: Track all completed, failed, and cancelled downloads
  - View history in dedicated History tab
  - Export history to CSV file
  - Persistent storage in `~/.termoload_history.json`
- **📊 Statistics Dashboard**: Comprehensive download statistics
  - Total downloads, success rate, total data downloaded
  - Downloads by type (URL/Torrent/Video)
  - Recent activity (last 7 days)
  - Average download size
- **📁 Open Folder**: Quickly open the download location
  - Right-click or use keyboard shortcut `o`
  - Opens file explorer with file selected (Windows/macOS/Linux)
- **🗑️ Smart Delete Options**:
  - **Remove From List**: Remove entry without deleting files
  - **Delete + Remove**: Delete files from disk AND remove from list
  - Handles directories, partial files, and torrent data
  - Automatic cleanup of empty parent folders

### Settings & Automation
- **🔄 Auto-Shutdown**: Optionally shutdown your PC when all downloads complete
- **🔔 Sound Notifications**: 
  - Play sound on download completion
  - Play sound on download error
  - Configurable in Settings
- **📋 Logs**: Built-in logging with file and in-app log viewer (last 20 lines)
- **⚙️ Persistent Settings**: Save your preferences to `settings.json`
- **💾 Auto-Save State**: Downloads automatically resume on restart

## 📋 Requirements (For developers or contribution)

- Python 3.8 or higher
- Windows, macOS, or Linux
- **Required**: `textual`, `aiohttp`, `aiofiles`, `Pillow`, `pystray`
- **Optional for torrents**: `libtorrent` Python bindings
- **Optional for YouTube/video**: `yt-dlp` (and `ffmpeg` for best results when merging audio/video)

## 🚀 Installation

1. **Clone the repository (For developers/contributions)**:
```bash
git clone https://github.com/devaforgestudios-afk/TermoLoad.git
cd TermoLoad
```

2. **Install dependencies (For developers/contributions)**:
```bash
# Core dependencies
pip install textual aiohttp aiofiles Pillow pystray

# Optional: For torrent support
pip install libtorrent

# Optional: For video downloads
pip install yt-dlp

# Optional: Install ffmpeg for video merging
# Windows (winget): winget install -e --id Gyan.FFmpeg
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg (or equivalent for your distro)
```

3. **Run the application**:
```bash
python app.py
```

## 🎮 Usage

### Keyboard Shortcuts

- `a` - Add new download
- `o` - Open folder for selected download
- `q` - Quit application
- `m` - Minimize to system tray
- `^p` - Open command palette
- **Arrow Keys** - Navigate downloads table
- **During Selection**: UI updates pause for 3 seconds to prevent jumping

### Adding a Download

1. Click **+ Add Download** button or press `a`
2. Enter the URL of the file to download:
   - **HTTP/HTTPS URL**: Direct file download
   - **Magnet Link**: `magnet:?xt=urn:btih:...`
   - **Torrent File**: Path to local `.torrent` file or URL to `.torrent`
   - **YouTube/Video URL**: Automatically detected and routed to yt-dlp
3. Specify the save folder (or leave empty for default)
4. Click **Browse** to select a folder via dialog
5. Click **Add** to start the download immediately

### Managing Downloads

#### Pause/Resume
- **Pause Selected**: Pause the currently selected download
- **Resume Selected**: Resume the selected paused download
- **Pause All**: Pause all active downloads
- **Resume All**: Resume all paused downloads

#### Delete Options
- **Remove From List**: Remove download from list but keep files on disk
- **Delete + Remove**: Delete files from disk AND remove from list
  - Handles directories recursively (for torrents with multiple files)
  - Cleans up partial files (`.part`, `.crdownload`, etc.)
  - Removes empty parent folders automatically

#### Open Folder
- Select a completed download and press `o` or click **Open Folder**
- Opens file explorer with the file selected
- Works on Windows (Explorer), macOS (Finder), and Linux (file manager)

### Download Types

#### 1. HTTP/HTTPS Downloads
- Direct file downloads from web servers
- Supports resume if server provides `Accept-Ranges` header
- Shows download speed and ETA
- Automatic retry on connection errors

#### 2. Torrent Downloads
- **Magnet Links**: Paste `magnet:?xt=urn:btih:...` links
- **Torrent Files**: Provide path to `.torrent` file or URL
- **Real-time Stats**:
  - Peer/seed count (e.g., `5↓/12↑` means 5 peers, 12 seeds)
  - Download speed from swarm
  - Progress and ETA
- **Status Messages**:
  - "Fetching Metadata" - Downloading torrent info
  - "Finding Peers" - Connecting to swarm
  - "Downloading" - Active download
  - "Completed" - Download finished
- **Requirements**: Needs `libtorrent` Python package installed

#### 3. Video Downloads (yt-dlp)

- Paste a YouTube (or any yt-dlp-supported) URL in Add Download.
- TermoLoad automatically routes it through yt-dlp and sets the filename to the actual video title.
- The app uses best video + best audio with mp4 merge when possible.
- Progress is shown with speed and ETA; after download, status briefly shows "Processing" while merging.

Optional setup for best results:
- Install yt-dlp: `pip install yt-dlp`
- Install ffmpeg so yt-dlp can merge video+audio to mp4.
  - Windows (winget): `winget install -e --id Gyan.FFmpeg`
  - Or download from https://ffmpeg.org and add to PATH.

Notes:
- If yt-dlp isn't installed, TermoLoad will show "Error: yt-dlp not installed" for video URLs and continue to work for normal HTTP/HTTPS downloads.
- Some sites may require cookies/login; advanced yt-dlp options can be added in future versions.

### Using Download History

1. Click **History** tab in the navbar
2. View all past downloads with:
   - Date and time
   - File name
   - Download type (URL/Torrent/Video)
   - File size
   - Status (completed/failed/cancelled)
3. **Export to CSV**: Click **Export CSV** to save history
4. **Clear History**: Click **Clear History** to remove all entries

### Viewing Statistics

1. Click **Stats** tab in the navbar
2. View comprehensive statistics:
   - **Total Downloads**: All-time download count
   - **Success Rate**: Percentage of completed downloads
   - **Total Data**: Combined size of all completed downloads
   - **Recent Activity**: Downloads in the last 7 days
   - **By Type**: Breakdown of URL, Torrent, and Video downloads
   - **Average Size**: Mean download size

### Navigating Tabs

- **Downloads**: View and monitor active downloads (default view, shown at top)
- **History**: Browse download history and export to CSV
- **Stats**: View download statistics and metrics
- **Settings**: Configure download preferences
- **Logs**: View the last 20 log entries
- **Help**: Help and about information with detailed error explanations

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

### Sound Notifications
- **Play sound on download completion**: Enable/disable completion sound
- **Play sound on download error**: Enable/disable error sound
- Windows beep sounds (non-intrusive)

### Shutdown Options
- **Shutdown PC when all downloads complete**: Enable automatic shutdown after completion
  - ⚠️ **WARNING**: When enabled, your PC will actually shutdown when all downloads finish
  - Keep disabled for testing (simulated shutdown will be logged instead)

### Saving Settings

1. Modify your preferences in the Settings panel
2. Click **Save Settings** to persist changes to `settings.json`
3. Click **Cancel** to discard changes and reload previous settings

## 📁 File Structure

```
TermoLoad/
├── app.py                          # Main application
├── settings.json                   # Saved settings (auto-generated)
├── README.md                       # This file
├── downloads/                      # Default download folder
└── termoload.log                   # Application logs

# User data files (per-user):
~/.termoload_history.json           # Download history
~/downloads_state.json              # Active downloads state
# Windows: C:\Users\<YourUser>\
# macOS/Linux: ~/
```

## 🔧 Configuration File

Settings are automatically saved to `settings.json`:

```json
{
  "download_folder": "E:\\TermoLoad\\downloads",
  "concurrent": 3,
  "max_speed_kb": 0,
  "shutdown_on_complete": false,
  "sound_on_complete": true,
  "sound_on_error": true
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
      "type": "Torrent",
      "name": "ubuntu-22.04.iso",
      "url": "magnet:?xt=urn:btih:...",
      "path": "E\\\\TermoLoad\\\\downloads",
      "progress": 0.42,
      "status": "Downloading",
      "downloaded_bytes": 451231744,
      "total_size": 1073741824,
      "filepath": "E\\\\TermoLoad\\\\downloads\\\\ubuntu-22.04.iso",
      "peers": 5,
      "seeds": 12,
      "speed": "2.5 MB/s",
      "eta": "5m 23s"
    }
  ]
}
```

On startup, any entries not marked Completed or Error will automatically resume if the server supports HTTP Range requests or if it's a torrent.

### Download History File

Download history is stored in `~/.termoload_history.json`:

```json
[
  {
    "id": 1,
    "name": "file.zip",
    "type": "URL",
    "url": "https://example.com/file.zip",
    "size": 1073741824,
    "downloaded": 1073741824,
    "status": "completed",
    "timestamp": 1729350000.0,
    "date": "2024-10-19 14:30:00",
    "filepath": "E:\\Downloads\\file.zip",
    "error": null
  }
]
```

## 📝 Logs

- **File Logs**: All logs are written to `termoload.log`
- **In-App Logs**: View the last 20 lines in the Logs tab
- **Log Levels**: DEBUG, INFO, ERROR

## 🛠️ Troubleshooting

### Downloads Not Starting
- Check that the URL is valid and accessible
- Ensure you have write permissions to the download folder
- Check `termoload.log` for error details
- For torrents: Ensure `libtorrent` is installed
- For videos: Ensure `yt-dlp` is installed

### Torrents Not Working
- Install libtorrent: `pip install libtorrent`
- Check if magnet link is valid
- Wait for metadata fetching (can take up to 60 seconds)
- Ensure DHT/PeX/LSD are not blocked by firewall
- Check `termoload.log` for detailed torrent errors

### Selection Jumping in Table
- This is fixed with interaction lock (3-second hold)
- UI updates pause while you click/select
- Downloads continue in background
- If still experiencing issues, check for rapid keyboard/mouse input

### UI Not Displaying Correctly
- Ensure your terminal supports Unicode and colors
- Try resizing the terminal window
- On Windows, use Windows Terminal for best results
- For help panel scrolling issues, try upgrading: `pip install --upgrade textual`

### Shutdown Not Working
- Enable "Shutdown PC when all downloads complete" in Settings
- ⚠️ Test with real shutdown at your own risk

### Merged file not mp4
- Some sources provide formats that cannot be merged to mp4; yt-dlp may pick a different container. Installing ffmpeg helps produce mp4 when available.

### Delete + Remove Not Working
- On Windows, files may be locked by antivirus or file explorer
- Close any programs accessing the files
- Check `termoload.log` for detailed error messages
- For torrents, ensure the torrent is stopped first

## 🔒 Safety Features

- **Stable Selection**: 3-second interaction lock prevents UI updates while selecting
- **Background Downloads**: Downloads continue even when UI is paused
- **Smart File Deletion**: 
  - Recursive directory deletion for multi-file torrents
  - Partial file cleanup (`.part`, `.crdownload`, etc.)
  - Empty folder removal
  - Torrent handle cleanup before file deletion
- **One-Time Trigger**: Shutdown only triggers once per session
- **Activity Detection**: Won't trigger on startup, only after downloads actually run and complete
- **Sound Notifications**: Optional audio feedback for completion and errors

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
- Torrent support via [libtorrent](https://www.libtorrent.org/) Python bindings
- Video downloads powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org)
- System tray integration with [pystray](https://github.com/moses-palmer/pystray) and [Pillow](https://python-pillow.org/)

## ✨ Recent Updates

### Version 2.0 (October 2024)
- ✅ Added full BitTorrent support (magnet links + .torrent files)
- ✅ Download History tracking with CSV export
- ✅ Statistics Dashboard with comprehensive metrics
- ✅ Open Folder feature for quick file access
- ✅ Delete + Remove with smart file cleanup
- ✅ Sound notifications for completion and errors
- ✅ Optimized UI layout (downloads at top with max space)
- ✅ Stable selection with 3-second interaction lock
- ✅ Wide table columns for better visibility
- ✅ Enhanced help panel with scrolling support
- ✅ Improved error handling and user feedback

## 📧 Contact

- GitHub: [@devaforgestudios-afk](https://github.com/devaforgestudios-afk)
- Repository: [TermoLoad](https://github.com/devaforgestudios-afk/TermoLoad)

---

**Happy Downloading! 🚀**
