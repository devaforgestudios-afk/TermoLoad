# Linux Build - Quick Reference Card

## 🎯 Goal
Make TermoLoad run on Linux without needing a Linux machine!

---

## ⚡ Super Quick Start (Copy-Paste Ready)

### Windows PowerShell (as Administrator):
```powershell
# 1. Install WSL
wsl --install

# 2. Restart computer (if prompted)

# 3. After restart, open WSL and run:
cd /mnt/e/TermoLoad
python3 -m venv venv
source venv/bin/activate
pip install textual aiohttp aiofiles Pillow pystray pyinstaller
```

### Edit app.py (3 changes):
1. Line 85: Change `import winsound` to conditional import
2. After imports: Add `play_notification_sound()` function  
3. Replace 4x `winsound.Beep()` calls

### Build:
```bash
chmod +x build_linux.sh
./build_linux.sh
./dist/TermoLoad
```

**Done!** 🎉

---

## 📋 Code Changes (Copy-Paste)

### Change 1: Line 85-86
```python
# BEFORE:
import ctypes
import winsound

# AFTER:
import ctypes

if sys.platform == 'win32':
    import winsound
```

### Change 2: After imports (~line 100)
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

### Change 3: Replace 4 instances
Use VS Code Find & Replace (Ctrl+H):

| Find | Replace |
|------|---------|
| `winsound.Beep(800, 150)` | `play_notification_sound(800, 150, 'info')` |
| `winsound.Beep(1000, 200)` | `play_notification_sound(1000, 200, 'complete')` |
| `winsound.Beep(500, 200)` | `play_notification_sound(500, 200, 'error')` |
| `winsound.Beep(300, 250)` | `play_notification_sound(300, 250, 'error')` |

---

## 🔨 Build Commands

```bash
# Single executable
./build_linux.sh

# Universal package (works on all Linux)
./build_appimage.sh

# Debian/Ubuntu package
./build_deb.sh

# Test
./dist/TermoLoad
```

---

## 📂 What You Get

```
dist/
├── TermoLoad                    # Linux binary
├── TermoLoad-1.0.0-x86_64.AppImage  # Universal
└── termoload_1.0.0_amd64.deb    # Debian package
```

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "wsl not found" | Run in PowerShell as Admin |
| "python3 not found" | `sudo apt install python3 python3-pip` |
| "Permission denied" | `chmod +x build_linux.sh` |
| Can't find files | Use `/mnt/e/` not `E:\` |

---

## 📚 Documentation Map

| File | When to Use |
|------|-------------|
| **WSL_QUICK_START.md** | First time building on Linux |
| **LINUX_BUILD_GUIDE.md** | Detailed reference |
| **LINUX_BUILD_SUMMARY.md** | Overview & decision guide |
| **CROSS_PLATFORM_CHANGES.md** | Exact code modifications |

---

## ⏱️ Time Breakdown

- WSL setup (first time): 15 min
- Code changes: 10 min
- Build: 5 min
- Test: 5 min
- **Total: ~35 minutes**

---

## ✅ Testing Checklist

```bash
# In WSL
./dist/TermoLoad

# Test:
[ ] App launches
[ ] UI shows correctly
[ ] Add download works
[ ] Download completes
[ ] No crashes
```

---

## 🚀 Distribution

Upload to GitHub Releases:
- `TermoLoad` (Linux binary)
- `TermoLoad-x86_64.AppImage` (recommended for users)
- `termoload_1.0.0_amd64.deb` (for apt users)
- `TermoLoad.exe` (existing Windows)

---

## 📊 Platform Support

| OS | Package | Status |
|----|---------|--------|
| Windows 10/11 | .exe | ✅ Working |
| Linux (all) | .AppImage | ✅ Ready |
| Debian/Ubuntu | .deb | ✅ Ready |
| macOS | .app | 📝 Code ready |

---

## 💡 Pro Tips

1. **Edit on Windows** - Files in E:\ are accessible in WSL at /mnt/e/
2. **No VM needed** - WSL is lightweight and fast
3. **Test instantly** - No file transfers required
4. **Works offline** - No cloud services needed

---

## 🎓 Learning Resources

- **WSL Basics**: https://learn.microsoft.com/en-us/windows/wsl/
- **PyInstaller**: https://pyinstaller.org/
- **AppImage**: https://appimage.org/

---

## 🆘 Need Help?

1. Check "Troubleshooting" in **WSL_QUICK_START.md**
2. See "Common Issues" in **LINUX_BUILD_GUIDE.md**
3. Review error messages - they're helpful!

---

## 🎯 Success Criteria

✅ WSL installed  
✅ Python 3.12 working  
✅ Code changes applied  
✅ `python app.py` runs in WSL  
✅ `./dist/TermoLoad` executes  
✅ AppImage created  

**You're ready to distribute!** 🎉

---

## 📞 Quick Command Reference

```bash
# WSL
wsl                             # Start
wsl --shutdown                  # Stop
wsl --list                      # List distros

# Navigation
cd /mnt/e/TermoLoad            # Windows E: drive
pwd                            # Current directory
ls -la                         # List files

# Python
python3 --version              # Check version
source venv/bin/activate       # Activate venv
deactivate                     # Deactivate venv

# Build
./build_linux.sh               # Build
./dist/TermoLoad               # Run
chmod +x file.sh               # Make executable

# Files
nano file.txt                  # Edit in terminal
code file.txt                  # Edit in VS Code
cp file1 file2                 # Copy
rm file                        # Delete
```

---

**Start with: WSL_QUICK_START.md** 🚀

**Estimated completion: 1 hour** ⏱️

**Difficulty: Beginner-friendly** ✨
