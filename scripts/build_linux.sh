#!/bin/bash
# TermoLoad Linux Build Script
# Usage: ./build_linux.sh [onefile|onedir]

MODE="${1:-onefile}"  # Default to onefile

echo "========================================"
echo "   TermoLoad Linux Build Script"
echo "========================================"
echo "Build mode: $MODE"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed!"
    echo "Install with: sudo apt install python3 python3-pip"
    exit 1
fi

# Check if PyInstaller is available
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo "Error: PyInstaller is not installed!"
    echo "Install with: pip install pyinstaller"
    exit 1
fi

# Detect architecture
ARCH=$(uname -m)
echo "Architecture: $ARCH"
echo ""

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist *.spec
echo ""

# Build based on mode
if [ "$MODE" = "onedir" ]; then
    echo "Building onedir (folder with dependencies)..."
    pyinstaller \
        --clean \
        --name TermoLoad \
        --console \
        --onedir \
        --add-data "README.md:." \
        app.py
else
    echo "Building onefile (single executable)..."
    pyinstaller \
        --clean \
        --name TermoLoad \
        --console \
        --onefile \
        --add-data "README.md:." \
        app.py
fi

# Check if build was successful
if [ "$MODE" = "onedir" ]; then
    if [ -f "dist/TermoLoad/TermoLoad" ]; then
        echo ""
        echo "========================================"
        echo "Build SUCCESSFUL!"
        echo "========================================"
        echo "Output: dist/TermoLoad/"
        echo "Main executable: dist/TermoLoad/TermoLoad"
        echo "Size: $(du -sh dist/TermoLoad | cut -f1)"
        echo ""
        echo "To run: ./dist/TermoLoad/TermoLoad"
        echo "To test: cd dist/TermoLoad && ./TermoLoad"
    else
        echo ""
        echo "========================================"
        echo "Build FAILED!"
        echo "========================================"
        exit 1
    fi
else
    if [ -f "dist/TermoLoad" ]; then
        echo ""
        echo "========================================"
        echo "Build SUCCESSFUL!"
        echo "========================================"
        echo "Output: dist/TermoLoad"
        echo "Size: $(du -h dist/TermoLoad | cut -f1)"
        echo ""
        echo "To run: ./dist/TermoLoad"
        echo "To install system-wide: sudo cp dist/TermoLoad /usr/local/bin/"
    else
        echo ""
        echo "========================================"
        echo "Build FAILED!"
        echo "========================================"
        exit 1
    fi
fi
