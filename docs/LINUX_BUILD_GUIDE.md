# Building TermoLoad for Linux

## Overview
This guide will help you build TermoLoad for Linux distributions (Ubuntu, Debian, Fedora, Arch, etc.). You can develop and test directly from Windows using WSL (Windows Subsystem for Linux)!

---

## Quick Start: Using WSL (Windows Subsystem for Linux)

### Option 1: Build & Test on WSL (Recommended - No Linux Machine Needed!)

#### 1. **Install WSL on Windows**

```powershell
# Open PowerShell as Administrator and run:
wsl --install

# Or install specific distro:
wsl --install -d Ubuntu-22.04

# Restart your computer if prompted
```

#### 2. **Start WSL**

```powershell
# Open WSL (Ubuntu terminal will open)
wsl

# Or from Windows Terminal: Click dropdown → Ubuntu
```

#### 3. **Setup Linux Environment**

```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install Python 3.12 and development tools
sudo apt install -y python3.12 python3.12-venv python3-pip
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev

# Install additional dependencies
sudo apt install -y portaudio19-dev libasound2-dev

# Verify Python
python3 --version  # Should show 3.12.x
```

#### 4. **Navigate to Your Project**

```bash
# Your Windows files are accessible at /mnt/
cd /mnt/e/TermoLoad

# Or copy to Linux home:
cp -r /mnt/e/TermoLoad ~/
cd ~/TermoLoad
```

#### 5. **Create Virtual Environment**

```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### 6. **Install Dependencies**

```bash
# Install from requirements
pip install textual aiohttp aiofiles Pillow pystray pyinstaller

# For torrents
pip install python-libtorrent

# If libtorrent fails, try:
sudo apt install -y python3-libtorrent
# Then symlink to venv (if needed)
```

---

## Code Changes for Linux

### Issues to Fix (Same as macOS)

1. **Windows-only imports**: `winsound`, `ctypes.windll`
2. **Sound notifications**: Need Linux alternative
3. **Console window manipulation**: Linux uses different methods
4. **Firewall**: Linux uses ufw/iptables

### Apply Cross-Platform Changes

Use the same changes from `CROSS_PLATFORM_CHANGES.md`:

#### **1. Fix imports (line 85-86)**

```python
# Before:
import ctypes
import winsound

# After:
import ctypes

if sys.platform == 'win32':
    import winsound
```

#### **2. Add sound function (after imports)**

```python
def play_notification_sound(frequency=800, duration=150, sound_type='info'):
    """Cross-platform notification sound."""
    try:
        if sys.platform == 'win32':
            import winsound
            winsound.Beep(frequency, duration)
        elif sys.platform == 'darwin':
            # macOS
            sound_map = {
                'info': '/System/Library/Sounds/Glass.aiff',
                'complete': '/System/Library/Sounds/Hero.aiff',
                'error': '/System/Library/Sounds/Basso.aiff'
            }
            sound_file = sound_map.get(sound_type, sound_map['info'])
            subprocess.run(['afplay', sound_file], check=False, capture_output=True, timeout=2)
        elif sys.platform.startswith('linux'):
            # Linux - try multiple sound systems
            try:
                # Try paplay (PulseAudio) first
                subprocess.run(['paplay', '/usr/share/sounds/freedesktop/stereo/message.oga'], 
                             check=False, capture_output=True, timeout=2)
            except FileNotFoundError:
                try:
                    # Try aplay (ALSA) as fallback
                    subprocess.run(['aplay', '/usr/share/sounds/alsa/Front_Center.wav'],
                                 check=False, capture_output=True, timeout=2)
                except FileNotFoundError:
                    try:
                        # Try beep command as last resort
                        subprocess.run(['beep', '-f', str(frequency), '-l', str(duration)],
                                     check=False, capture_output=True, timeout=2)
                    except FileNotFoundError:
                        pass  # No sound available
    except Exception as e:
        logging.debug(f"[TermoLoad] Could not play sound: {e}")
```

#### **3. Replace winsound.Beep() - 4 locations**

```python
# Find and replace all 4 instances:
winsound.Beep(800, 150)   →  play_notification_sound(800, 150, 'info')
winsound.Beep(1000, 200)  →  play_notification_sound(1000, 200, 'complete')
winsound.Beep(500, 200)   →  play_notification_sound(500, 200, 'error')
winsound.Beep(300, 250)   →  play_notification_sound(300, 250, 'error')
```

#### **4. Fix firewall function**

```python
def _request_firewall_permission(self):
    """Request firewall permission (cross-platform)"""
    try:
        if sys.platform.startswith('linux'):
            # Linux: Check if ufw is available
            try:
                result = subprocess.run(['which', 'ufw'], 
                                      capture_output=True, timeout=1)
                if result.returncode == 0:
                    logging.info("[TermoLoad] Linux firewall detected (ufw)")
                    logging.info("[TermoLoad] To allow torrents: sudo ufw allow 6881/tcp")
                    logging.info("[TermoLoad] To allow torrents: sudo ufw allow 6881/udp")
            except:
                pass
            return
        elif sys.platform == 'darwin':
            logging.info("[TermoLoad] macOS will prompt for network access if needed")
            return
        elif sys.platform != 'win32':
            return
            
        # Windows code continues...
```

---

## Test on Linux (WSL)

### 1. **Apply Code Changes**

```bash
# Edit app.py with your changes
nano app.py
# or
code app.py  # If VS Code is installed
```

### 2. **Test Run**

```bash
# Activate venv
source venv/bin/activate

# Run the app
python app.py
```

**Expected:** App should run in your terminal with the Textual UI!

### 3. **Verify Features**

- [ ] App launches
- [ ] UI displays correctly
- [ ] Add HTTP download
- [ ] Add torrent (if libtorrent installed)
- [ ] Open folder (uses `xdg-open`)
- [ ] Sound notifications (if audio configured)
- [ ] Download completes
- [ ] No crashes

---

## Building Linux Executable

### Option 1: PyInstaller (Single Binary)

#### **Create build script: `build_linux.sh`**

```bash
#!/bin/bash
# TermoLoad Linux Build Script

echo "========================================"
echo "   TermoLoad Linux Build Script"
echo "========================================"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist *.spec

# Detect architecture
ARCH=$(uname -m)
echo "Architecture: $ARCH"

# Build single file executable
echo "Building Linux executable..."
pyinstaller \
    --onefile \
    --name TermoLoad \
    --console \
    --add-data "README.md:." \
    app.py

# Check if successful
if [ -f "dist/TermoLoad" ]; then
    echo "========================================"
    echo "Build SUCCESSFUL!"
    echo "========================================"
    echo "Output: dist/TermoLoad"
    echo "Size: $(du -h dist/TermoLoad | cut -f1)"
    echo ""
    echo "To run: ./dist/TermoLoad"
    echo "To install: sudo cp dist/TermoLoad /usr/local/bin/"
else
    echo "========================================"
    echo "Build FAILED!"
    echo "========================================"
    exit 1
fi
```

Make it executable:
```bash
chmod +x build_linux.sh
```

#### **Build**

```bash
# Run build script
./build_linux.sh
```

**Output:** `dist/TermoLoad` (single executable file)

#### **Test**

```bash
# Run directly
./dist/TermoLoad

# Or install system-wide
sudo cp dist/TermoLoad /usr/local/bin/
termoload  # Run from anywhere
```

---

### Option 2: AppImage (Universal Linux Package)

AppImage works on ALL Linux distros without installation!

#### **Install AppImage tools**

```bash
# Download appimagetool
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage
```

#### **Create AppImage structure**

```bash
#!/bin/bash
# Create AppImage for TermoLoad

# Build with PyInstaller first
pyinstaller --onefile --name TermoLoad app.py

# Create AppDir structure
mkdir -p TermoLoad.AppDir/usr/bin
mkdir -p TermoLoad.AppDir/usr/share/applications
mkdir -p TermoLoad.AppDir/usr/share/icons/hicolor/256x256/apps

# Copy executable
cp dist/TermoLoad TermoLoad.AppDir/usr/bin/

# Create desktop entry
cat > TermoLoad.AppDir/termoload.desktop << 'EOF'
[Desktop Entry]
Name=TermoLoad
Exec=TermoLoad
Icon=termoload
Type=Application
Categories=Network;FileTransfer;
Comment=Fast Terminal-Based Download Manager
Terminal=true
EOF

# Create AppRun script
cat > TermoLoad.AppDir/AppRun << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
exec "${HERE}/usr/bin/TermoLoad" "$@"
EOF
chmod +x TermoLoad.AppDir/AppRun

# Create icon (placeholder)
cat > TermoLoad.AppDir/termoload.png << 'EOF'
# Add your icon here or use ImageMagick to convert
EOF

# Copy icon
cp TermoLoad.AppDir/termoload.png TermoLoad.AppDir/usr/share/icons/hicolor/256x256/apps/

# Build AppImage
./appimagetool-x86_64.AppImage TermoLoad.AppDir TermoLoad-x86_64.AppImage

echo "AppImage created: TermoLoad-x86_64.AppImage"
echo "Run with: ./TermoLoad-x86_64.AppImage"
```

---

### Option 3: DEB Package (Debian/Ubuntu)

#### **Create package structure**

```bash
#!/bin/bash
# Create DEB package

VERSION="1.0.0"
ARCH="amd64"  # or arm64 for ARM

# Create directory structure
mkdir -p termoload_${VERSION}_${ARCH}/DEBIAN
mkdir -p termoload_${VERSION}_${ARCH}/usr/local/bin
mkdir -p termoload_${VERSION}_${ARCH}/usr/share/applications
mkdir -p termoload_${VERSION}_${ARCH}/usr/share/doc/termoload

# Build executable
pyinstaller --onefile --name TermoLoad app.py

# Copy executable
cp dist/TermoLoad termoload_${VERSION}_${ARCH}/usr/local/bin/

# Create control file
cat > termoload_${VERSION}_${ARCH}/DEBIAN/control << EOF
Package: termoload
Version: ${VERSION}
Section: net
Priority: optional
Architecture: ${ARCH}
Depends: libc6
Maintainer: DevaForge Studios <your@email.com>
Description: Fast Terminal-Based Download Manager
 TermoLoad is a powerful terminal-based download manager
 with support for HTTP, HTTPS, and torrent downloads.
EOF

# Create desktop entry
cat > termoload_${VERSION}_${ARCH}/usr/share/applications/termoload.desktop << 'EOF'
[Desktop Entry]
Name=TermoLoad
Exec=TermoLoad
Type=Application
Categories=Network;FileTransfer;
Comment=Fast Terminal-Based Download Manager
Terminal=true
EOF

# Create README
cp README.md termoload_${VERSION}_${ARCH}/usr/share/doc/termoload/

# Build DEB package
dpkg-deb --build termoload_${VERSION}_${ARCH}

echo "DEB package created: termoload_${VERSION}_${ARCH}.deb"
echo "Install with: sudo dpkg -i termoload_${VERSION}_${ARCH}.deb"
```

#### **Install DEB package**

```bash
sudo dpkg -i termoload_1.0.0_amd64.deb

# Run
termoload
```

---

### Option 4: RPM Package (Fedora/RHEL/CentOS)

```bash
#!/bin/bash
# Create RPM package

# Install rpm-build
sudo dnf install -y rpm-build rpmdevtools

# Create build structure
rpmdev-setuptree

# Create spec file
cat > ~/rpmbuild/SPECS/termoload.spec << 'EOF'
Name:           termoload
Version:        1.0.0
Release:        1%{?dist}
Summary:        Fast Terminal-Based Download Manager

License:        MIT
URL:            https://github.com/devaforgestudios-afk/TermoLoad
Source0:        termoload-1.0.0.tar.gz

BuildRequires:  python3-devel
Requires:       python3

%description
TermoLoad is a powerful terminal-based download manager
with support for HTTP, HTTPS, and torrent downloads.

%prep
%setup -q

%build
pyinstaller --onefile --name TermoLoad app.py

%install
mkdir -p %{buildroot}%{_bindir}
cp dist/TermoLoad %{buildroot}%{_bindir}/

%files
%{_bindir}/TermoLoad

%changelog
* Mon Oct 21 2025 DevaForge Studios <your@email.com> - 1.0.0-1
- Initial release
EOF

# Build RPM
rpmbuild -ba ~/rpmbuild/SPECS/termoload.spec

echo "RPM created in: ~/rpmbuild/RPMS/"
```

---

## Distribution Formats Comparison

| Format | Best For | Size | Pros | Cons |
|--------|----------|------|------|------|
| **Single Binary** | Quick testing | ~30 MB | Simple, fast | No desktop integration |
| **AppImage** | Universal Linux | ~30 MB | Works everywhere, no install | Larger size |
| **DEB** | Debian/Ubuntu | ~30 MB | Native package manager | Debian-only |
| **RPM** | Fedora/RHEL | ~30 MB | Native package manager | RPM-only |
| **Snap** | Ubuntu | ~40 MB | Auto-updates | Ubuntu-focused |
| **Flatpak** | All distros | ~50 MB | Sandboxed, universal | Larger size |

---

## Testing on Different Linux Distributions

### Using Docker (Test on any distro from Windows/WSL!)

#### **Test on Ubuntu**

```bash
# Create Dockerfile
cat > Dockerfile.ubuntu << 'EOF'
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    build-essential

WORKDIR /app
COPY . .

RUN python3 -m pip install textual aiohttp aiofiles Pillow pystray

CMD ["python3", "app.py"]
EOF

# Build and run
docker build -t termoload-ubuntu -f Dockerfile.ubuntu .
docker run -it termoload-ubuntu
```

#### **Test on Fedora**

```bash
cat > Dockerfile.fedora << 'EOF'
FROM fedora:latest

RUN dnf install -y python3 python3-pip

WORKDIR /app
COPY . .

RUN pip3 install textual aiohttp aiofiles Pillow pystray

CMD ["python3", "app.py"]
EOF

docker build -t termoload-fedora -f Dockerfile.fedora .
docker run -it termoload-fedora
```

#### **Test on Arch Linux**

```bash
cat > Dockerfile.arch << 'EOF'
FROM archlinux:latest

RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm python python-pip

WORKDIR /app
COPY . .

RUN pip install textual aiohttp aiofiles Pillow pystray

CMD ["python", "app.py"]
EOF

docker build -t termoload-arch -f Dockerfile.arch .
docker run -it termoload-arch
```

---

## GitHub Actions (Automated Linux Builds)

Create `.github/workflows/build-linux.yml`:

```yaml
name: Build Linux

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build-linux:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        arch: [x86_64, aarch64]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install textual aiohttp aiofiles Pillow pystray pyinstaller
        pip install python-libtorrent || echo "libtorrent optional"
    
    - name: Build executable
      run: |
        pyinstaller --onefile --name TermoLoad app.py
    
    - name: Create AppImage
      run: |
        # Download appimagetool
        wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
        chmod +x appimagetool-x86_64.AppImage
        
        # Create AppDir
        mkdir -p TermoLoad.AppDir/usr/bin
        cp dist/TermoLoad TermoLoad.AppDir/usr/bin/
        
        # Create AppRun
        cat > TermoLoad.AppDir/AppRun << 'EOF'
        #!/bin/bash
        SELF=$(readlink -f "$0")
        HERE=${SELF%/*}
        export PATH="${HERE}/usr/bin:${PATH}"
        exec "${HERE}/usr/bin/TermoLoad" "$@"
        EOF
        chmod +x TermoLoad.AppDir/AppRun
        
        # Create desktop file
        cat > TermoLoad.AppDir/termoload.desktop << 'EOF'
        [Desktop Entry]
        Name=TermoLoad
        Exec=TermoLoad
        Type=Application
        Categories=Network;
        Terminal=true
        EOF
        
        # Build AppImage
        ./appimagetool-x86_64.AppImage TermoLoad.AppDir TermoLoad-${{ matrix.arch }}.AppImage
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: TermoLoad-Linux-${{ matrix.arch }}
        path: |
          dist/TermoLoad
          TermoLoad-${{ matrix.arch }}.AppImage
```

---

## Installation Instructions for Users

### Method 1: Download and Run (Simplest)

```bash
# Download latest release
wget https://github.com/devaforgestudios-afk/TermoLoad/releases/latest/download/TermoLoad

# Make executable
chmod +x TermoLoad

# Run
./TermoLoad
```

### Method 2: Install System-Wide

```bash
# Download
wget https://github.com/devaforgestudios-afk/TermoLoad/releases/latest/download/TermoLoad

# Install
sudo install -m 755 TermoLoad /usr/local/bin/

# Run from anywhere
termoload
```

### Method 3: AppImage (No Installation)

```bash
# Download AppImage
wget https://github.com/devaforgestudios-afk/TermoLoad/releases/latest/download/TermoLoad-x86_64.AppImage

# Make executable
chmod +x TermoLoad-x86_64.AppImage

# Run
./TermoLoad-x86_64.AppImage
```

### Method 4: DEB Package (Debian/Ubuntu)

```bash
# Download
wget https://github.com/devaforgestudios-afk/TermoLoad/releases/latest/download/termoload_1.0.0_amd64.deb

# Install
sudo dpkg -i termoload_1.0.0_amd64.deb

# Run
termoload
```

---

## Quick Build Summary

### On WSL (Windows):

```bash
# 1. Start WSL
wsl

# 2. Navigate to project
cd /mnt/e/TermoLoad

# 3. Setup
python3 -m venv venv
source venv/bin/activate
pip install textual aiohttp aiofiles Pillow pystray pyinstaller

# 4. Apply code changes (see CROSS_PLATFORM_CHANGES.md)

# 5. Test
python app.py

# 6. Build
pyinstaller --onefile --name TermoLoad app.py

# 7. Test executable
./dist/TermoLoad

# 8. Package (optional)
# Create AppImage, DEB, or RPM as needed
```

---

## Common Issues on Linux

### Issue: "libtorrent not found"
```bash
# Install via apt
sudo apt install python3-libtorrent

# Or compile from source
sudo apt install build-essential libboost-all-dev libssl-dev
pip install python-libtorrent
```

### Issue: "No sound playing"
```bash
# Install PulseAudio
sudo apt install pulseaudio pulseaudio-utils

# Test sound
paplay /usr/share/sounds/freedesktop/stereo/message.oga
```

### Issue: "tkinter not found"
```bash
sudo apt install python3-tk
```

### Issue: "pystray icon not showing"
```bash
# Install system tray support
sudo apt install gir1.2-appindicator3-0.1
```

---

## Next Steps

1. ✅ Apply cross-platform code changes
2. ✅ Test on WSL
3. ✅ Build with PyInstaller
4. ✅ Create AppImage or DEB
5. ✅ Upload to GitHub Releases
6. ✅ Update README with Linux instructions

**Estimated time:** 1-2 hours for code + build + testing

Ready to start? Let me know if you need help with any specific part! 🐧🚀
