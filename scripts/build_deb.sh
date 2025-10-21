#!/bin/bash
# Create DEB package for Debian/Ubuntu/Linux Mint

set -e

echo "========================================"
echo "   TermoLoad DEB Package Builder"
echo "========================================"

VERSION="1.0.0"
ARCH="amd64"  # Change to arm64 for ARM, armhf for ARM 32-bit
PACKAGE_NAME="termoload_${VERSION}_${ARCH}"

# Build executable first if needed
if [ ! -f "dist/TermoLoad" ]; then
    echo "Building executable first..."
    ./build_linux.sh onefile
fi

# Clean previous package
rm -rf "${PACKAGE_NAME}" "${PACKAGE_NAME}.deb"

# Create directory structure
echo "Creating package structure..."
mkdir -p "${PACKAGE_NAME}/DEBIAN"
mkdir -p "${PACKAGE_NAME}/usr/local/bin"
mkdir -p "${PACKAGE_NAME}/usr/share/applications"
mkdir -p "${PACKAGE_NAME}/usr/share/doc/termoload"
mkdir -p "${PACKAGE_NAME}/usr/share/man/man1"

# Copy executable
cp dist/TermoLoad "${PACKAGE_NAME}/usr/local/bin/"
chmod 755 "${PACKAGE_NAME}/usr/local/bin/TermoLoad"

# Create control file
cat > "${PACKAGE_NAME}/DEBIAN/control" << CONTROL
Package: termoload
Version: ${VERSION}
Section: net
Priority: optional
Architecture: ${ARCH}
Depends: libc6 (>= 2.31)
Maintainer: DevaForge Studios <contact@devaforge.com>
Homepage: https://github.com/devaforgestudios-afk/TermoLoad
Description: Fast Terminal-Based Download Manager
 TermoLoad is a powerful terminal-based download manager with support
 for HTTP, HTTPS, and torrent downloads. Features include:
 .
  - Multi-threaded downloads for maximum speed
  - BitTorrent support with DHT and peer exchange
  - Resume capability for interrupted downloads
  - System tray integration
  - Beautiful terminal UI using Textual
  - Cross-platform compatibility
CONTROL

# Create postinst script (runs after installation)
cat > "${PACKAGE_NAME}/DEBIAN/postinst" << 'POSTINST'
#!/bin/bash
set -e

# Create symlink for easy access
if [ ! -L /usr/bin/termoload ]; then
    ln -s /usr/local/bin/TermoLoad /usr/bin/termoload
fi

echo "TermoLoad installed successfully!"
echo "Run with: termoload"
exit 0
POSTINST
chmod 755 "${PACKAGE_NAME}/DEBIAN/postinst"

# Create prerm script (runs before uninstallation)
cat > "${PACKAGE_NAME}/DEBIAN/prerm" << 'PRERM'
#!/bin/bash
set -e

# Remove symlink
if [ -L /usr/bin/termoload ]; then
    rm -f /usr/bin/termoload
fi

exit 0
PRERM
chmod 755 "${PACKAGE_NAME}/DEBIAN/prerm"

# Create desktop entry
cat > "${PACKAGE_NAME}/usr/share/applications/termoload.desktop" << 'DESKTOP'
[Desktop Entry]
Name=TermoLoad
Comment=Fast Terminal-Based Download Manager
Exec=termoload
Icon=utilities-terminal
Type=Application
Categories=Network;FileTransfer;
Terminal=true
Keywords=download;torrent;http;manager;
StartupNotify=false
DESKTOP

# Copy documentation
if [ -f "README.md" ]; then
    cp README.md "${PACKAGE_NAME}/usr/share/doc/termoload/"
fi

# Create simple man page
cat > "${PACKAGE_NAME}/usr/share/man/man1/termoload.1" << 'MANPAGE'
.TH TERMOLOAD 1 "October 2025" "TermoLoad 1.0.0" "User Commands"
.SH NAME
termoload \- Fast Terminal-Based Download Manager
.SH SYNOPSIS
.B termoload
.SH DESCRIPTION
TermoLoad is a powerful terminal-based download manager with support for HTTP, HTTPS, and torrent downloads.
.SH OPTIONS
No command-line options are currently supported. All operations are performed through the interactive UI.
.SH FILES
.I ~/.config/termoload/settings.json
.RS
User configuration file
.RE
.I ~/termoload.log
.RS
Application log file
.RE
.SH AUTHOR
DevaForge Studios
.SH "SEE ALSO"
Full documentation at: https://github.com/devaforgestudios-afk/TermoLoad
MANPAGE

# Compress man page
gzip -9 "${PACKAGE_NAME}/usr/share/man/man1/termoload.1"

# Set proper permissions
find "${PACKAGE_NAME}" -type d -exec chmod 755 {} \;
find "${PACKAGE_NAME}" -type f -exec chmod 644 {} \;
chmod 755 "${PACKAGE_NAME}/usr/local/bin/TermoLoad"
chmod 755 "${PACKAGE_NAME}/DEBIAN/postinst"
chmod 755 "${PACKAGE_NAME}/DEBIAN/prerm"

# Build DEB package
echo "Building DEB package..."
dpkg-deb --build "${PACKAGE_NAME}"

if [ -f "${PACKAGE_NAME}.deb" ]; then
    echo ""
    echo "========================================"
    echo "DEB Package Build SUCCESSFUL!"
    echo "========================================"
    echo "Output: ${PACKAGE_NAME}.deb"
    echo "Size: $(du -h ${PACKAGE_NAME}.deb | cut -f1)"
    echo ""
    echo "To install:"
    echo "  sudo dpkg -i ${PACKAGE_NAME}.deb"
    echo ""
    echo "To uninstall:"
    echo "  sudo dpkg -r termoload"
    echo ""
    echo "Compatible with: Debian, Ubuntu, Linux Mint, Pop!_OS, elementary OS"
else
    echo "DEB package build failed!"
    exit 1
fi
