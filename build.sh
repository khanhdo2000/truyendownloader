#!/bin/bash
# Build script for macOS/Linux

echo "Building TruyenFull Downloader Desktop App..."

# Use virtual environment Python
PYTHON_CMD="./venv/bin/python"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "Installing dependencies..."
    ./venv/bin/pip install -r requirements.txt
fi

# Verify tkinter is available
if ! $PYTHON_CMD -c "import tkinter" 2>/dev/null; then
    echo "Error: tkinter is not available."
    echo "Please run: brew install python-tk@3.14"
    exit 1
fi

# Check if PyInstaller is installed
if ! $PYTHON_CMD -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found. Installing..."
    ./venv/bin/pip install pyinstaller
fi

# Clean previous builds
rm -rf dist build

# Get version from version.py
VERSION=$(grep "__version__" version.py | cut -d'"' -f2 | cut -d"'" -f2)
if [ -z "$VERSION" ]; then
    VERSION="1.0.0"
fi
echo "Building version: $VERSION"

# Build the app (standalone executable - no Python needed)
ICON_ARGS=""
if [ -f "icon.icns" ]; then
    ICON_ARGS="--icon icon.icns"
    echo "Using icon: icon.icns"
fi

$PYTHON_CMD -m PyInstaller --name TruyenFullDownloader \
    --windowed \
    --onedir \
    $ICON_ARGS \
    --add-data "truyenfull_downloader.py:." \
    --add-data "site_adapters.py:." \
    --add-data "version.py:." \
    --hidden-import tkinter \
    --hidden-import requests \
    --hidden-import bs4 \
    --hidden-import lxml \
    --hidden-import ebooklib \
    --hidden-import ebooklib.epub \
    --hidden-import version \
    --hidden-import site_adapters \
    --collect-all ebooklib \
    --collect-all tkinter \
    truyenfull_gui.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Build successful!"
    echo "App bundle: dist/TruyenFullDownloader.app"
    echo "Directory: dist/TruyenFullDownloader/"
else
    echo ""
    echo "✗ Build failed"
    exit 1
fi

