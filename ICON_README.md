# App Icon

This directory contains the application icon for TruyenFull Downloader.

## Icon Design

The icon features:
- **📘 Book**: Represents novel/story content
- **⬇️ Download Arrow**: Indicates downloading functionality
- **Modern Design**: Clean, professional look with shadow effects
- **Color Scheme**:
  - Primary Blue (#3B82F6) - Main background
  - Accent Green (#22C55E) - Download indicator
  - White - Book and arrow elements

## Generated Files

### Universal Formats
- `icon.png` (1024x1024) - High-resolution PNG for any use
- `icon_512.png` (512x512) - Preview/thumbnail size

### Platform-Specific Formats
- `icon.icns` - macOS application icon (multi-resolution)
- `icon.ico` - Windows application icon (multi-resolution)

## Regenerating the Icon

If you need to modify or regenerate the icon:

```bash
# Install required dependencies
pip install Pillow

# Run the generator script
python generate_icon.py
```

## Using the Icon

The icon is automatically included when building the application:

### macOS Build
```bash
python build_app.py
# Creates: dist/TruyenFullDownloader.app (with icon.icns)
```

### Windows Build
```bash
python build_app.py
# Creates: dist/TruyenFullDownloader.exe (with icon.ico)
```

## Icon Specifications

### macOS (.icns)
Contains multiple resolutions:
- 16x16, 32x32, 64x64, 128x128, 256x256, 512x512, 1024x1024
- Includes @2x retina versions

### Windows (.ico)
Contains multiple resolutions:
- 16x16, 32x32, 48x48, 64x64, 128x128, 256x256

## License

This icon is created specifically for TruyenFull Downloader by minhnhatdigital.
