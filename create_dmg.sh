#!/bin/bash
# Script to create a DMG file for macOS distribution

set -e

APP_NAME="TruyenFullDownloader"
VERSION=$(grep "__version__" version.py | cut -d'"' -f2 | cut -d"'" -f2)
if [ -z "$VERSION" ]; then
    VERSION="1.0.0"
fi

DMG_NAME="${APP_NAME}-${VERSION}"
DMG_PATH="dist/${DMG_NAME}.dmg"
APP_PATH="dist/${APP_NAME}.app"
TEMP_DMG="dist/temp_${DMG_NAME}.dmg"
MOUNT_DIR="/Volumes/${APP_NAME}"

echo "Creating DMG for ${APP_NAME} v${VERSION}..."

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "Error: ${APP_PATH} not found. Please build the app first using ./build.sh"
    exit 1
fi

# Clean up any existing DMG
rm -f "$DMG_PATH" "$TEMP_DMG"

# Create a temporary directory for DMG contents
DMG_CONTENTS="dist/dmg_contents"
rm -rf "$DMG_CONTENTS"
mkdir -p "$DMG_CONTENTS"

# Copy app to DMG contents
cp -R "$APP_PATH" "$DMG_CONTENTS/"

# Create Applications symlink (standard macOS DMG feature)
ln -s /Applications "$DMG_CONTENTS/Applications"

# Create a README or instructions file
cat > "$DMG_CONTENTS/README.txt" << EOF
TruyenFull Downloader v${VERSION}

Installation:
1. Drag ${APP_NAME}.app to the Applications folder
2. Launch from Applications or Spotlight

First Launch:
If macOS shows a security warning:
- Right-click the app → Open
- Or: System Settings → Privacy & Security → Allow

For more information, visit:
https://github.com/yourusername/truyenfull
EOF

# Calculate size needed (app size + 100MB buffer)
APP_SIZE=$(du -sm "$DMG_CONTENTS" | cut -f1)
DMG_SIZE=$((APP_SIZE + 100))

echo "Creating DMG (size: ${DMG_SIZE}MB)..."

# Create the DMG
hdiutil create -srcfolder "$DMG_CONTENTS" -volname "$APP_NAME" \
    -fs HFS+ -fsargs "-c c=64,a=16,e=16" -format UDRW -size ${DMG_SIZE}m "$TEMP_DMG"

# Mount the DMG
hdiutil attach "$TEMP_DMG" -readwrite -noverify -noautoopen

# Set DMG window properties (optional - requires osascript)
osascript << EOF
tell application "Finder"
    tell disk "${APP_NAME}"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {400, 100, 920, 420}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 72
        set position of item "${APP_NAME}.app" of container window to {160, 205}
        set position of item "Applications" of container window to {360, 205}
        set position of item "README.txt" of container window to {260, 100}
        close
        open
        update without registering applications
        delay 2
    end tell
end tell
EOF

# Unmount
hdiutil detach "$MOUNT_DIR"

# Convert to compressed read-only DMG
echo "Compressing DMG..."
hdiutil convert "$TEMP_DMG" -format UDZO -imagekey zlib-level=9 -o "$DMG_PATH"

# Clean up
rm -f "$TEMP_DMG"
rm -rf "$DMG_CONTENTS"

# Get DMG size
DMG_SIZE_MB=$(du -h "$DMG_PATH" | cut -f1)

echo ""
echo "✓ DMG created successfully!"
echo "  Location: $DMG_PATH"
echo "  Size: $DMG_SIZE_MB"
echo ""
echo "Next steps:"
echo "1. Test the DMG on a clean Mac"
echo "2. Upload to GitHub Releases"
echo "3. Share the download link with users"





