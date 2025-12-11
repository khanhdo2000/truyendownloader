#!/bin/bash
# Helper script to prepare files for GitHub release

set -e

VERSION=$(grep "__version__" version.py | cut -d'"' -f2 | cut -d"'" -f2)
if [ -z "$VERSION" ]; then
    VERSION="1.0.0"
fi

APP_NAME="TruyenFullDownloader"
RELEASE_DIR="release_${VERSION}"

echo "Preparing release v${VERSION}..."

# Create release directory
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# Check if app exists
if [ ! -d "dist/${APP_NAME}.app" ]; then
    echo "Error: App not found. Building first..."
    ./build.sh
fi

# Check if DMG exists, create if not
if [ ! -f "dist/${APP_NAME}-${VERSION}.dmg" ]; then
    echo "Creating DMG..."
    ./create_dmg.sh
fi

# Copy files to release directory
echo "Copying release files..."
cp "dist/${APP_NAME}-${VERSION}.dmg" "$RELEASE_DIR/" 2>/dev/null || cp "dist/${APP_NAME}.app" "$RELEASE_DIR/" -R
cp README.md "$RELEASE_DIR/"
cp DISTRIBUTION.md "$RELEASE_DIR/"

# Create release notes template
cat > "$RELEASE_DIR/RELEASE_NOTES.md" << EOF
# TruyenFull Downloader v${VERSION}

## What's New

- Initial release
- Desktop GUI application
- Download stories from truyenfull.vn
- Export to text and EPUB formats

## Installation

1. Download \`${APP_NAME}-${VERSION}.dmg\`
2. Open the DMG file
3. Drag \`${APP_NAME}.app\` to Applications folder
4. Launch from Applications or Spotlight

## First Launch

If macOS shows a security warning:
- Right-click the app → **Open**
- Or: **System Settings → Privacy & Security → Open Anyway**

## System Requirements

- macOS 10.13 (High Sierra) or later
- No additional dependencies required

## Files

- \`${APP_NAME}-${VERSION}.dmg\` - Disk image for easy installation
EOF

# Calculate checksums
echo "Calculating checksums..."
cd "$RELEASE_DIR"
if [ -f "${APP_NAME}-${VERSION}.dmg" ]; then
    shasum -a 256 "${APP_NAME}-${VERSION}.dmg" > "${APP_NAME}-${VERSION}.dmg.sha256"
    echo "SHA256: $(cat ${APP_NAME}-${VERSION}.dmg.sha256)"
fi
cd ..

echo ""
echo "✓ Release files prepared in: $RELEASE_DIR/"
echo ""
echo "Next steps:"
echo "1. Review files in $RELEASE_DIR/"
echo "2. Create a GitHub release:"
echo "   - Tag: v${VERSION}"
echo "   - Title: TruyenFull Downloader v${VERSION}"
echo "   - Upload: ${APP_NAME}-${VERSION}.dmg"
echo "   - Description: Copy from $RELEASE_DIR/RELEASE_NOTES.md"
echo ""
echo "GitHub CLI (if installed):"
echo "  gh release create v${VERSION} \\"
echo "    --title 'TruyenFull Downloader v${VERSION}' \\"
echo "    --notes-file $RELEASE_DIR/RELEASE_NOTES.md \\"
echo "    $RELEASE_DIR/${APP_NAME}-${VERSION}.dmg"





