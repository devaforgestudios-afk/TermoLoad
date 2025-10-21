#!/bin/bash
# Create AppImage for TermoLoad
# Universal Linux package that works on all distributions

set -e  # Exit on error

echo "========================================"
echo "   TermoLoad AppImage Builder"
echo "========================================"

# Check if PyInstaller build exists
if [ ! -f "dist/TermoLoad" ]; then
    echo "Building executable first..."
    ./build_linux.sh onefile
fi

# Download appimagetool if not present
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    echo "Downloading appimagetool..."
    wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x appimagetool-x86_64.AppImage
fi

# Clean previous AppDir
rm -rf TermoLoad.AppDir

# Create AppDir structure
echo "Creating AppDir structure..."
mkdir -p TermoLoad.AppDir/usr/bin
mkdir -p TermoLoad.AppDir/usr/share/applications
mkdir -p TermoLoad.AppDir/usr/share/icons/hicolor/256x256/apps
mkdir -p TermoLoad.AppDir/usr/share/doc/termoload

# Copy executable
cp dist/TermoLoad TermoLoad.AppDir/usr/bin/
chmod +x TermoLoad.AppDir/usr/bin/TermoLoad

# Create AppRun script
cat > TermoLoad.AppDir/AppRun << 'APPRUN'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
exec "${HERE}/usr/bin/TermoLoad" "$@"
APPRUN
chmod +x TermoLoad.AppDir/AppRun

# Create desktop entry
cat > TermoLoad.AppDir/termoload.desktop << 'DESKTOP'
[Desktop Entry]
Name=TermoLoad
Comment=Fast Terminal-Based Download Manager
Exec=TermoLoad
Icon=termoload
Type=Application
Categories=Network;FileTransfer;
Terminal=true
Keywords=download;torrent;http;manager;
DESKTOP

# Copy desktop file to proper location
cp TermoLoad.AppDir/termoload.desktop TermoLoad.AppDir/usr/share/applications/

# Create simple icon (text-based placeholder)
# In production, replace with actual PNG icon
cat > TermoLoad.AppDir/termoload.png << 'ICON'
# This is a placeholder
# Replace with actual PNG icon using:
# cp your_icon.png TermoLoad.AppDir/termoload.png
# cp your_icon.png TermoLoad.AppDir/usr/share/icons/hicolor/256x256/apps/termoload.png
ICON

# If you have an icon, uncomment and modify:
# cp icon.png TermoLoad.AppDir/termoload.png
# cp icon.png TermoLoad.AppDir/usr/share/icons/hicolor/256x256/apps/termoload.png

# Copy documentation
if [ -f "README.md" ]; then
    cp README.md TermoLoad.AppDir/usr/share/doc/termoload/
fi

# Get version from app or use default
VERSION="1.0.0"
ARCH=$(uname -m)

# Build AppImage
echo "Building AppImage..."
./appimagetool-x86_64.AppImage TermoLoad.AppDir "TermoLoad-${VERSION}-${ARCH}.AppImage"

if [ -f "TermoLoad-${VERSION}-${ARCH}.AppImage" ]; then
    echo ""
    echo "========================================"
    echo "AppImage Build SUCCESSFUL!"
    echo "========================================"
    echo "Output: TermoLoad-${VERSION}-${ARCH}.AppImage"
    echo "Size: $(du -h TermoLoad-${VERSION}-${ARCH}.AppImage | cut -f1)"
    echo ""
    echo "To run: ./TermoLoad-${VERSION}-${ARCH}.AppImage"
    echo "To make executable: chmod +x TermoLoad-${VERSION}-${ARCH}.AppImage"
    echo ""
    echo "This AppImage works on ALL Linux distributions!"
else
    echo "AppImage build failed!"
    exit 1
fi
