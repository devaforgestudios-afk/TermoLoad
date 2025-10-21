# Linux Build - Complete Guide Summary

## What We Created

### Documentation Files
1. **LINUX_BUILD_GUIDE.md** - Complete Linux building guide
2. **WSL_QUICK_START.md** - Quick start for building on Windows WSL
3. **CROSS_PLATFORM_CHANGES.md** - Code modifications needed

### Build Scripts
1. **build_linux.sh** - Build Linux executable
2. **build_appimage.sh** - Create AppImage package
3. **build_deb.sh** - Create DEB package for Debian/Ubuntu

---

## Quick Decision Guide

### Do you have access to a Linux machine?

#### ✅ YES → Use Native Linux
```bash
# On Linux machine
git clone <repo>
cd TermoLoad
./build_linux.sh
```
See: **LINUX_BUILD_GUIDE.md** for full details

#### ❌ NO → Use WSL on Windows  
```powershell
# On Windows
wsl --install
# Then follow WSL_QUICK_START.md
```
See: **WSL_QUICK_START.md** for step-by-step

---

## What Needs to Change in Code

### 3 Simple Changes to app.py:

**1. Fix imports (line 85-86)**
```python
import ctypes

if sys.platform == 'win32':
    import winsound
```

**2. Add sound function (after imports)**
```python
def play_notification_sound(frequency=800, duration=150, sound_type='info'):
    """Cross-platform notification sound."""
    try:
        if sys.platform == 'win32':
            import winsound
            winsound.Beep(frequency, duration)
        elif sys.platform.startswith('linux'):
            subprocess.run(['paplay', '/usr/share/sounds/freedesktop/stereo/message.oga'], 
                         check=False, capture_output=True, timeout=2)
    except:
        pass
```

**3. Replace 4 instances of winsound.Beep()**
- Find: `winsound.Beep(800, 150)` → Replace: `play_notification_sound(800, 150, 'info')`
- Find: `winsound.Beep(1000, 200)` → Replace: `play_notification_sound(1000, 200, 'complete')`
- Find: `winsound.Beep(500, 200)` → Replace: `play_notification_sound(500, 200, 'error')`
- Find: `winsound.Beep(300, 250)` → Replace: `play_notification_sound(300, 250, 'error')`

**That's it!** ✅

---

## Build Process Overview

### Method 1: WSL (Easiest - No Linux Machine Needed!)

```bash
# 1. Install WSL on Windows
wsl --install

# 2. In WSL
cd /mnt/e/TermoLoad
python3 -m venv venv
source venv/bin/activate
pip install textual aiohttp aiofiles Pillow pystray pyinstaller

# 3. Build
./build_linux.sh

# 4. Output
./dist/TermoLoad
```

### Method 2: Docker (Test Multiple Distros)

```bash
docker run -it -v $(pwd):/app ubuntu:22.04
# Then follow Linux build steps inside container
```

### Method 3: GitHub Actions (Automated)

```yaml
# Add .github/workflows/build-linux.yml
# See LINUX_BUILD_GUIDE.md for full workflow
```

---

## Output Formats Comparison

| Format | Use Case | Size | Install | Universal |
|--------|----------|------|---------|-----------|
| **Binary** | Quick testing | 30 MB | None | No |
| **AppImage** | Best for users | 30 MB | None | ✅ Yes |
| **DEB** | Debian/Ubuntu | 30 MB | `dpkg -i` | No |
| **RPM** | Fedora/RHEL | 30 MB | `rpm -i` | No |

**Recommendation:** Build both **Binary** (for GitHub releases) and **AppImage** (universal)

---

## Testing Checklist

After building, test these on Linux:

- [ ] App launches
- [ ] UI displays correctly in terminal
- [ ] Add HTTP download
- [ ] Add torrent download
- [ ] Resume works
- [ ] Open folder works
- [ ] Sound notifications work (or fail gracefully)
- [ ] No crashes on quit
- [ ] Log file created at `~/termoload.log`

---

## Distribution Plan

### For GitHub Release:

Upload these files:
1. `TermoLoad` - Linux binary (direct download)
2. `TermoLoad-x86_64.AppImage` - Universal package
3. `termoload_1.0.0_amd64.deb` - Debian/Ubuntu package
4. `TermoLoad.exe` - Windows executable (existing)

### Installation Instructions for Users:

**Linux - Method 1 (Binary):**
```bash
wget https://github.com/.../TermoLoad
chmod +x TermoLoad
./TermoLoad
```

**Linux - Method 2 (AppImage):**
```bash
wget https://github.com/.../TermoLoad-x86_64.AppImage
chmod +x TermoLoad-x86_64.AppImage
./TermoLoad-x86_64.AppImage
```

**Linux - Method 3 (DEB):**
```bash
wget https://github.com/.../termoload_1.0.0_amd64.deb
sudo dpkg -i termoload_1.0.0_amd64.deb
termoload
```

**Windows:**
```
Download TermoLoad.exe
Double-click to run
Allow firewall when prompted
```

---

## File Structure After Building

```
E:\TermoLoad\
├── app.py (modified for cross-platform)
├── build_linux.sh ✨
├── build_appimage.sh ✨
├── build_deb.sh ✨
├── build_fast.bat (existing - Windows)
├── dist/
│   ├── TermoLoad (Linux binary) ✨
│   └── TermoLoad/ (Windows - existing)
├── TermoLoad-1.0.0-x86_64.AppImage ✨
├── termoload_1.0.0_amd64.deb ✨
└── docs/
    ├── LINUX_BUILD_GUIDE.md ✨
    ├── WSL_QUICK_START.md ✨
    └── CROSS_PLATFORM_CHANGES.md ✨
```

✨ = New files created

---

## Time Estimates

| Task | Time |
|------|------|
| Code changes | 15 min |
| WSL setup (first time) | 15 min |
| Build on WSL | 5 min |
| Test Linux version | 10 min |
| Create AppImage | 5 min |
| Create DEB package | 5 min |
| **Total** | **~1 hour** |

---

## Commands Cheat Sheet

### WSL Commands
```bash
wsl                              # Start WSL
cd /mnt/e/TermoLoad             # Go to project
source venv/bin/activate        # Activate venv
python app.py                   # Test app
./build_linux.sh                # Build executable
./dist/TermoLoad                # Run executable
exit                            # Exit WSL
```

### Build Commands
```bash
./build_linux.sh                # Build single executable
./build_linux.sh onedir         # Build with dependencies folder
./build_appimage.sh             # Build AppImage
./build_deb.sh                  # Build DEB package
```

### Make Scripts Executable
```bash
chmod +x build_linux.sh
chmod +x build_appimage.sh
chmod +x build_deb.sh
```

---

## Common Issues & Solutions

### "wsl: command not found"
- Update Windows to 10 version 2004+ or Windows 11
- Or install manually: https://aka.ms/wsl2

### "python3: command not found"
```bash
sudo apt install python3 python3-pip
```

### "Permission denied" on scripts
```bash
chmod +x build_*.sh
```

### "PyInstaller not found"
```bash
pip install pyinstaller
```

### "libtorrent not found" (optional)
```bash
sudo apt install python3-libtorrent
```

---

## Next Steps - In Order

1. ✅ **Read** `WSL_QUICK_START.md`
2. ✅ **Install** WSL: `wsl --install`
3. ✅ **Apply** code changes from `CROSS_PLATFORM_CHANGES.md`
4. ✅ **Test** with `python app.py` in WSL
5. ✅ **Build** with `./build_linux.sh`
6. ✅ **Test** with `./dist/TermoLoad`
7. ✅ **Package** with `./build_appimage.sh`
8. ✅ **Upload** to GitHub Releases

---

## Support Matrix After Changes

| Platform | Status | Package Format | Size |
|----------|--------|----------------|------|
| Windows 10/11 | ✅ Working | `.exe` | 25.7 MB |
| Linux (All) | ✅ Ready | `.AppImage` | ~30 MB |
| Linux (Debian/Ubuntu) | ✅ Ready | `.deb` | ~30 MB |
| macOS | ⚠️ Code ready, needs Mac to build | `.app` | ~30 MB |

---

## What You Can Do RIGHT NOW

### Option 1: Quick Test (5 minutes)
```powershell
# In PowerShell (Windows)
wsl --install
# Wait for install, restart if needed
wsl
# In WSL
cd /mnt/e/TermoLoad
python3 app.py
```

### Option 2: Full Build (1 hour)
Follow **WSL_QUICK_START.md** step by step

### Option 3: Just Apply Code Changes
Edit `app.py` on Windows with the 3 changes above, commit to GitHub, and build later!

---

## Resources

- **Main Guide**: `LINUX_BUILD_GUIDE.md` - Complete reference
- **Quick Start**: `WSL_QUICK_START.md` - Step-by-step for Windows users
- **Code Changes**: `CROSS_PLATFORM_CHANGES.md` - Exact modifications needed
- **Scripts**: `build_linux.sh`, `build_appimage.sh`, `build_deb.sh`

---

## Questions?

- **"Do I need a Linux computer?"** → No! Use WSL on Windows
- **"Will it break Windows version?"** → No! Changes are backward compatible
- **"How long will it take?"** → 1 hour including learning WSL
- **"What if something goes wrong?"** → Check "Troubleshooting" sections in guides
- **"Can I test on different Linux distros?"** → Yes! Use Docker (see LINUX_BUILD_GUIDE.md)

---

**Ready to build for Linux? Start with WSL_QUICK_START.md!** 🐧🚀
