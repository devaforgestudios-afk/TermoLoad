# TermoLoad v1.0 - First Stable Release 🚀

## Overview

TermoLoad is a powerful, feature-rich download manager with torrent support, built with a modern Terminal User Interface (TUI). This first stable release brings robust downloading capabilities with an intuitive interface that runs directly in your terminal.

## 🎯 Key Features

### Download Management
- **Multi-Protocol Support**: HTTP, HTTPS, FTP, and BitTorrent protocols
- **Concurrent Downloads**: Handle multiple downloads simultaneously
- **Resume Capability**: Pause and resume downloads at any time
- **Speed Control**: Real-time download speed monitoring
- **Progress Tracking**: Visual progress bars and ETA calculations
- **Queue Management**: Organize and prioritize your downloads

### Torrent Support
- **Magnet Links**: Direct support for magnet URIs
- **Torrent Files**: Import .torrent files from disk or URL
- **File Selection**: Choose specific files from multi-file torrents
- **DHT Support**: Distributed Hash Table for trackerless torrents
- **Peer Statistics**: Real-time peer and seed counts
- **Smart Metadata Fetching**: Automatic torrent info retrieval

### User Interface
- **Modern TUI**: Beautiful terminal-based interface using Textual framework
- **Responsive Design**: Adapts to your terminal size
- **Keyboard Shortcuts**: Efficient navigation and control
- **System Tray Integration**: Minimize to system tray (Windows)
- **Native Dialogs**: File and folder pickers using native OS dialogs

### Performance & Reliability
- **Lazy Loading**: Fast startup with on-demand module loading (2-5 seconds)
- **Error Recovery**: Comprehensive error handling with automatic retries
- **Session Persistence**: Remembers your downloads across restarts
- **Low Memory Footprint**: Efficient resource usage
- **Crash Prevention**: Robust error handling prevents application crashes

## 📦 What's Included

### Executables
- **`TermoLoad.exe`** (25.7 MB) - Main application executable
- **`_internal/`** - Required dependencies (distributed with exe)

### Build Mode
- **Type**: One-directory build (onedir)
- **Console**: Console window enabled for debugging
- **Platform**: Windows 10/11 (64-bit)

## 🔥 Major Improvements in v1.0

### Torrent Engine Enhancements
- ✅ **Firewall Integration**: Automatic Windows Firewall permission handling
- ✅ **Session Stability**: 5-attempt retry logic with exponential backoff
- ✅ **Better Error Messages**: User-friendly status messages
- ✅ **Metadata Countdown**: Visual countdown during magnet link resolution
- ✅ **Cleanup System**: Automatic temporary file removal

### UI/UX Improvements
- ✅ **Thread-Safe Dialogs**: Prevents hangs when using file pickers
- ✅ **Real-Time Updates**: Live progress updates every second
- ✅ **Status Indicators**: Clear visual feedback for all operations
- ✅ **Responsive Controls**: Smooth interaction even during heavy operations

### Technical Improvements
- ✅ **Async Architecture**: Non-blocking operations throughout
- ✅ **Lazy Module Loading**: Faster startup times
- ✅ **Comprehensive Logging**: Detailed logs for troubleshooting
- ✅ **Error Recovery**: Graceful handling of network issues and errors

## 🚀 Getting Started

### Installation

1. **Download the release**
   - Download `TermoLoad-v1.0-Windows.zip`
   - Extract to your desired location

2. **First Run**
   ```batch
   cd TermoLoad
   TermoLoad.exe
   ```

3. **Firewall Setup** (Important for Torrents!)
   - When you add your first torrent, Windows will show a firewall prompt
   - Click **"Allow access"** to enable P2P connections
   - This is required for torrent downloads to work

### Basic Usage

#### Adding Downloads
- **URL Downloads**: Press `A` → Enter URL → Enter
- **Torrent Files**: Press `A` → Select .torrent file
- **Magnet Links**: Press `A` → Paste magnet link

#### Managing Downloads
- **Pause**: Select download → Press `P`
- **Resume**: Select download → Press `R`
- **Cancel**: Select download → Press `Del`
- **Open Folder**: Select download → Press `O`

#### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `A` | Add new download |
| `P` | Pause selected download |
| `R` | Resume selected download |
| `Del` | Remove selected download |
| `O` | Open download folder |
| `S` | Open settings |
| `Q` | Quit application |
| `↑/↓` | Navigate downloads |

## ⚙️ Configuration

### Default Settings
- **Download Location**: `C:\Users\<YourUsername>\Downloads`
- **Log File**: `C:\Users\<YourUsername>\termoload.log`
- **Torrent Port**: 6881 (configurable)
- **Max Concurrent Downloads**: Unlimited

### Changing Settings
Settings can be modified through the Settings menu (`S` key) or by editing `settings.json`.

## 🐛 Known Issues & Limitations

### Current Limitations
- Windows only (Linux/Mac support planned for v1.1)
- No built-in video player preview
- No bandwidth scheduling
- No automatic antivirus scanning

### Known Issues
- First startup may take 3-5 seconds (modules loading)
- Large torrents (>100 files) may take time to load file list
- Firewall popup may not appear if rules already exist from previous installations

### Workarounds
- **Firewall Issues**: Manually add firewall rule via Windows Defender settings
- **Slow Metadata**: Wait up to 60 seconds for magnet link resolution
- **Port Conflicts**: Change port 6881 if already in use

## 🔧 Troubleshooting

### Application Won't Start
- Ensure you extracted the entire folder (not just the .exe)
- Run as Administrator if you encounter permission errors
- Check `termoload.log` for error messages

### Torrent Downloads Not Working
1. **Check Firewall**: Ensure you clicked "Allow access" on the Windows Firewall prompt
2. **Verify Network**: Confirm internet connection is active
3. **Check Logs**: Look for errors in `%USERPROFILE%\termoload.log`
4. **Manual Firewall Rule**: Add rule for TermoLoad.exe in Windows Defender Firewall

### Slow Performance
- First run is slower due to module loading (normal)
- Subsequent runs should start in 2-3 seconds
- Large download lists may increase startup time

### Log File Analysis
```powershell
# View recent log entries
Get-Content $env:USERPROFILE\termoload.log -Tail 30

# Search for errors
Select-String -Path $env:USERPROFILE\termoload.log -Pattern "error|exception" -CaseSensitive:$false
```

## 📊 System Requirements

### Minimum Requirements
- **OS**: Windows 10 (64-bit) or later
- **RAM**: 2 GB
- **Disk**: 100 MB for application + space for downloads
- **Network**: Active internet connection

### Recommended Requirements
- **OS**: Windows 11 (64-bit)
- **RAM**: 4 GB or more
- **Disk**: SSD with ample free space
- **Network**: Broadband connection (for torrents)

## 📝 Technical Details

### Built With
- **Python**: 3.12.7
- **Textual**: Modern TUI framework
- **libtorrent**: BitTorrent protocol implementation
- **aiohttp**: Async HTTP client
- **aiofiles**: Async file I/O
- **PyInstaller**: Executable packaging

### Architecture
- Async/await throughout for non-blocking operations
- Lazy module loading for fast startup
- Thread pool for native dialogs
- Persistent state management

## 📄 License

This project is released under the MIT License. See LICENSE file for details.

## 🙏 Acknowledgments

- Textual framework for the amazing TUI capabilities
- libtorrent community for robust torrent support
- All beta testers who helped identify and fix issues

## 📞 Support & Feedback

- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Join GitHub Discussions for questions
- **Email**: Contact maintainers via GitHub

## 🗺️ Roadmap

### Planned for v1.1
- [ ] Linux and macOS support
- [ ] Browser extension integration
- [ ] Scheduling downloads
- [ ] Bandwidth limits per download
- [ ] Categories and tags
- [ ] Search integration with torrent sites

### Planned for v1.2
- [ ] Video preview/streaming
- [ ] Auto-extraction of archives
- [ ] Remote control via web interface
- [ ] Mobile companion app
- [ ] Plugins system

## 📸 Screenshots

*Note: Add screenshots in the GitHub release assets showing:*
- Main download interface
- Torrent file selection dialog
- Settings screen
- System tray integration

## 🔐 Security Notes

### Firewall Requirements
TermoLoad requests Windows Firewall access for torrent functionality. This is required for:
- Incoming peer connections
- DHT network participation
- Tracker communication

### Privacy
- No telemetry or analytics collected
- No data sent to external servers (except for downloads)
- All downloads stored locally
- No account or registration required

## 📦 Download

### Release Files

**TermoLoad-v1.0-Windows.zip** (Latest)
- Size: ~26 MB compressed
- SHA-256: `[Add checksum after creating zip]`
- Platform: Windows 10/11 (64-bit)

### Verification

Verify the download integrity:
```powershell
Get-FileHash TermoLoad-v1.0-Windows.zip -Algorithm SHA256
```

## 🎉 Thank You!

Thank you for using TermoLoad v1.0! We're excited to bring you a powerful, reliable download manager. Your feedback helps us improve - please report issues and suggest features on GitHub.

**Happy Downloading! 🚀**

---

## Changelog

### [1.0.0] - October 20, 2025

#### Added
- Initial stable release
- HTTP/HTTPS/FTP download support
- BitTorrent protocol support (magnets and .torrent files)
- Multi-file torrent selection
- System tray integration
- Native file/folder dialogs
- Persistent download state
- Comprehensive error handling
- Windows Firewall integration
- Real-time progress tracking
- Peer/seed statistics for torrents
- Lazy module loading for performance
- Detailed logging system

#### Fixed
- Session initialization crashes
- Torrent metadata fetch timeouts
- File dialog hangs in compiled executable
- aiofiles lazy loading issues
- Memory leaks in long-running sessions
- Progress bar rendering issues
- Temporary file cleanup

#### Technical
- Built with Python 3.12.7
- PyInstaller 6.13.0
- Textual TUI framework
- libtorrent 2.x
- Async architecture throughout
- Thread-safe dialog handling

---

**Version**: 1.0.0  
**Release Date**: October 20, 2025  
**Build**: onedir-console  
**Size**: 25.7 MB  
**Platform**: Windows 10/11 (64-bit)
