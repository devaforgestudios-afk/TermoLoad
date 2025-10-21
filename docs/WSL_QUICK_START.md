# Quick Start: Building TermoLoad for Linux on Windows (WSL)

## Step 1: Install WSL (One-Time Setup)

Open PowerShell as Administrator:

```powershell
# Install WSL with Ubuntu
wsl --install

# Restart your computer when prompted
```

After restart, Ubuntu will open automatically. Create a username and password.

---

## Step 2: Setup Linux Environment

In WSL/Ubuntu terminal:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and build tools
sudo apt install -y python3.12 python3.12-venv python3-pip build-essential

# Verify installation
python3 --version  # Should show 3.12.x
```

---

## Step 3: Access Your Project from WSL

```bash
# Your Windows E: drive is at /mnt/e/
cd /mnt/e/TermoLoad

# Check files
ls -la
```

---

## Step 4: Apply Code Changes

First, apply the cross-platform fixes to `app.py`:

### Edit in WSL:
```bash
# Use nano (simple editor)
nano app.py

# Or use VS Code from WSL
code app.py
```

### Or Edit on Windows:
Just edit `E:\TermoLoad\app.py` in VS Code on Windows - WSL can access it!

### Required Changes:

**1. Line 85-86 - Fix imports:**
```python
# Change from:
import ctypes
import winsound

# To:
import ctypes

if sys.platform == 'win32':
    import winsound
```

**2. After imports (~line 100) - Add sound function:**
```python
def play_notification_sound(frequency=800, duration=150, sound_type='info'):
    """Cross-platform notification sound."""
    try:
        if sys.platform == 'win32':
            import winsound
            winsound.Beep(frequency, duration)
        elif sys.platform.startswith('linux'):
            try:
                subprocess.run(['paplay', '/usr/share/sounds/freedesktop/stereo/message.oga'], 
                             check=False, capture_output=True, timeout=2)
            except:
                pass  # Silent if sound not available
    except Exception as e:
        logging.debug(f"[TermoLoad] Could not play sound: {e}")
```

**3. Replace 4 instances of `winsound.Beep()`:**
```bash
# In nano/vim, use search and replace
# Or in VS Code: Ctrl+H

# Find: winsound.Beep(800, 150)
# Replace: play_notification_sound(800, 150, 'info')

# Find: winsound.Beep(1000, 200)
# Replace: play_notification_sound(1000, 200, 'complete')

# Find: winsound.Beep(500, 200)
# Replace: play_notification_sound(500, 200, 'error')

# Find: winsound.Beep(300, 250)
# Replace: play_notification_sound(300, 250, 'error')
```

---

## Step 5: Setup Python Environment

```bash
# In /mnt/e/TermoLoad
cd /mnt/e/TermoLoad

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install textual aiohttp aiofiles Pillow pystray pyinstaller

# Optional: Install libtorrent for torrent support
pip install python-libtorrent
# If that fails:
sudo apt install -y python3-libtorrent
```

---

## Step 6: Test the App

```bash
# Make sure venv is activated (you should see (venv) in prompt)
python app.py
```

**Expected:** The Textual UI should appear in your terminal! ✅

Test features:
- Add a download
- Check if UI works
- Ctrl+C to quit

---

## Step 7: Build Linux Executable

```bash
# Make build scripts executable
chmod +x build_linux.sh
chmod +x build_appimage.sh
chmod +x build_deb.sh

# Build single-file executable
./build_linux.sh

# Output will be in: dist/TermoLoad
```

---

## Step 8: Test the Executable

```bash
# Run the built executable
./dist/TermoLoad
```

**It should work just like running `python app.py`!** ✅

---

## Step 9: Create Packages (Optional)

### AppImage (Universal Linux package):
```bash
./build_appimage.sh

# Output: TermoLoad-1.0.0-x86_64.AppImage
# Works on ALL Linux distros!
```

### DEB Package (Debian/Ubuntu):
```bash
./build_deb.sh

# Output: termoload_1.0.0_amd64.deb
# Install with: sudo dpkg -i termoload_1.0.0_amd64.deb
```

---

## Step 10: Copy Back to Windows (Optional)

```bash
# Copy builds back to Windows for distribution
cp dist/TermoLoad /mnt/e/TermoLoad/dist_linux/
cp TermoLoad-*.AppImage /mnt/e/TermoLoad/dist_linux/
cp termoload_*.deb /mnt/e/TermoLoad/dist_linux/

# Now accessible from Windows at: E:\TermoLoad\dist_linux\
```

---

## Troubleshooting

### Issue: "wsl: command not found"
**Solution:** You need Windows 10 version 2004+ or Windows 11
- Update Windows
- Or manually install WSL: https://aka.ms/wsl2

### Issue: "python3: command not found"
**Solution:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip
```

### Issue: "Permission denied" on build scripts
**Solution:**
```bash
chmod +x build_linux.sh build_appimage.sh build_deb.sh
```

### Issue: Can't find files in `/mnt/e/`
**Solution:**
```bash
# Check if drive is mounted
ls /mnt/

# If empty, mount manually:
sudo mount -t drvfs E: /mnt/e
```

### Issue: "pip: command not found"
**Solution:**
```bash
sudo apt install -y python3-pip
python3 -m pip install --upgrade pip
```

---

## Quick Commands Reference

```bash
# Start WSL from Windows
wsl

# Navigate to project
cd /mnt/e/TermoLoad

# Activate venv
source venv/bin/activate

# Run app
python app.py

# Build Linux executable
./build_linux.sh

# Test executable
./dist/TermoLoad

# Exit WSL
exit
```

---

## File Locations

| Windows Path | WSL Path |
|--------------|----------|
| `E:\TermoLoad\` | `/mnt/e/TermoLoad/` |
| `E:\TermoLoad\app.py` | `/mnt/e/TermoLoad/app.py` |
| `E:\TermoLoad\dist\` | `/mnt/e/TermoLoad/dist/` |

**You can edit files in Windows and build in WSL!** 🎉

---

## What You'll Have After This

✅ **Windows EXE** - Already built with `build_fast.bat`  
✅ **Linux Binary** - Built with `./build_linux.sh`  
✅ **AppImage** - Universal Linux package  
✅ **DEB Package** - For Debian/Ubuntu  

**Your app will work on Windows, Linux, and can be adapted for macOS!** 🚀

---

## Expected Output Sizes

- **Linux Binary**: ~30 MB
- **AppImage**: ~30 MB
- **DEB Package**: ~30 MB

All smaller than the Windows version due to Linux's efficient libraries!

---

## Next Steps

1. ✅ Apply code changes to `app.py`
2. ✅ Test on WSL with `python app.py`
3. ✅ Build with `./build_linux.sh`
4. ✅ Test executable with `./dist/TermoLoad`
5. ✅ Create AppImage with `./build_appimage.sh`
6. ✅ Upload to GitHub Releases

**Total time: 30-60 minutes** ⏱️

---

## Tips

- **Edit on Windows, build on WSL** - Best of both worlds!
- **No Linux VM needed** - WSL is lightweight and fast
- **Test immediately** - No need to transfer files
- **Works offline** - No cloud services required

**Happy building!** 🐧✨
