# Build Instructions

This document explains how to build standalone executables for TruyenFull Downloader.

## 📋 Prerequisites

### All Platforms
- Python 3.8 or higher
- pip (Python package installer)

### macOS
```bash
# Install tkinter support
brew install python-tk@3.14
```

### Windows
```bash
# tkinter is usually included with Python
# If needed, reinstall Python with "tcl/tk" option enabled
```

### Linux
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora/RHEL
sudo yum install python3-tkinter
```

## 🚀 Building the Application

You have **two options** for building:

### Option 1: Shell Script (Recommended for macOS/Linux)

```bash
# Make the script executable
chmod +x build.sh

# Run the build
./build.sh
```

**Features:**
- ✅ Automatically creates virtual environment
- ✅ Installs all dependencies
- ✅ Includes app icon (icon.icns)
- ✅ Verifies tkinter availability
- ✅ Creates .app bundle (macOS) or directory (Linux)

**Output:**
- macOS: `dist/TruyenFullDownloader.app`
- Linux: `dist/TruyenFullDownloader/`

### Option 2: Python Script (Cross-platform)

```bash
# Run the build script
python build_app.py
```

**Features:**
- ✅ Cross-platform (macOS, Windows, Linux)
- ✅ Includes app icon (.icns for macOS, .ico for Windows)
- ✅ Creates version info files
- ✅ Platform-specific optimizations

**Output:**
- macOS: `dist/TruyenFullDownloader.app/`
- Windows: `dist/TruyenFullDownloader.exe`
- Linux: `dist/TruyenFullDownloader`

## 📦 What Gets Included

The standalone app includes:

### Core Files
- ✅ `truyenfull_gui.py` - Main GUI application
- ✅ `truyenfull_downloader.py` - Download logic
- ✅ `site_adapters.py` - Multi-site support
- ✅ `version.py` - Version information

### Dependencies
- ✅ tkinter - GUI framework
- ✅ requests - HTTP library
- ✅ beautifulsoup4 - HTML parsing
- ✅ lxml - XML/HTML parser
- ✅ ebooklib - EPUB creation

### Assets
- ✅ App icon (platform-specific)
- ✅ All required data files

## 🎨 App Icon

The build process automatically includes the app icon if present:

- **macOS**: `icon.icns` (155KB, multi-resolution)
- **Windows**: `icon.ico` (721B, multi-resolution)

To regenerate icons:
```bash
python generate_icon.py
```

## 🔍 Troubleshooting

### "tkinter not found"
**macOS:**
```bash
brew install python-tk@3.14
```

**Linux:**
```bash
sudo apt-get install python3-tk
```

### "PyInstaller not found"
```bash
pip install pyinstaller
```

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### Build fails on macOS
```bash
# Clean previous builds
rm -rf dist build *.spec

# Try again
./build.sh
```

### Build fails on Windows
```bash
# Clean previous builds
rmdir /s /q dist build
del *.spec

# Try again
python build_app.py
```

## 📝 Build Configuration

### Customizing the Build

Edit `build.sh` or `build_app.py` to customize:

- App name: Change `--name TruyenFullDownloader`
- Icon: Modify icon file paths
- Dependencies: Add `--hidden-import` for new modules
- Output type: Change `--onedir` to `--onefile` (Windows)

### Version Management

Update version in `version.py`:
```python
__version__ = "1.0.1"
```

## 🚢 Distribution

### macOS
1. Build creates: `dist/TruyenFullDownloader.app`
2. Compress: `zip -r TruyenFullDownloader.zip TruyenFullDownloader.app`
3. Distribute the .zip file
4. Users: Extract and drag to Applications folder

### Windows
1. Build creates: `dist/TruyenFullDownloader.exe`
2. Optional: Create installer with NSIS or Inno Setup
3. Distribute the .exe file
4. Users: Run the executable (no installation needed)

### Linux
1. Build creates: `dist/TruyenFullDownloader/`
2. Package as .tar.gz: `tar -czf TruyenFullDownloader.tar.gz TruyenFullDownloader/`
3. Distribute the .tar.gz file
4. Users: Extract and run the executable

## 📊 Build Size

Typical build sizes:

- **macOS**: ~50-80 MB (app bundle)
- **Windows**: ~40-60 MB (.exe)
- **Linux**: ~50-70 MB (directory)

## ✅ Testing the Build

After building, test the standalone app:

1. **Run the app** - Double-click or execute
2. **Test downloads** - Try downloading a test story
3. **Check features**:
   - URL input and validation
   - Password protection (WordPress)
   - Chapter range selection
   - EPUB generation
   - About dialog

## 📞 Support

If you encounter build issues:

1. Check this documentation
2. Review error messages carefully
3. Ensure all prerequisites are installed
4. Try cleaning and rebuilding

---

Built with ❤️ by minhnhatdigital
