# Quick Start: Distributing Your App

## Recommended Approach: GitHub Releases

**Why GitHub Releases?**
- ✅ Free and reliable
- ✅ Version control
- ✅ Direct download links
- ✅ Professional appearance
- ✅ Easy to share

## Quick Steps

### 1. Create a DMG (Recommended)
```bash
./create_dmg.sh
```
This creates a professional disk image that users can easily install.

### 2. Prepare Release Files
```bash
./prepare_release.sh
```
This creates a release directory with all necessary files.

### 3. Create GitHub Release

**Option A: Using GitHub Web Interface**
1. Go to your repository on GitHub
2. Click "Releases" → "Draft a new release"
3. Tag: `v1.0.0` (use your version from version.py)
4. Title: `TruyenFull Downloader v1.0.0`
5. Upload: `dist/TruyenFullDownloader-1.0.0.dmg`
6. Add release notes
7. Publish release

**Option B: Using GitHub CLI** (if installed)
```bash
gh release create v1.0.0 \
  --title "TruyenFull Downloader v1.0.0" \
  --notes-file release_1.0.0/RELEASE_NOTES.md \
  dist/TruyenFullDownloader-1.0.0.dmg
```

### 4. Share the Link

Your download link will be:
```
https://github.com/YOUR_USERNAME/truyenfull/releases/download/v1.0.0/TruyenFullDownloader-1.0.0.dmg
```

## Alternative: Direct Download

If you have a website:
1. Upload the DMG to your web server
2. Provide a direct download link
3. Consider using a CDN for faster downloads

## Important Notes

### macOS Security Warning
Users will see a security warning because the app isn't code-signed. This is normal for open-source apps.

**User Instructions:**
- Right-click the app → Open
- Or: System Settings → Privacy & Security → Allow

### Code Signing (Optional)
To remove the warning, you need:
- Apple Developer account ($99/year)
- Code signing certificate
- Notarization process

See [DISTRIBUTION.md](DISTRIBUTION.md) for details.

## File Sizes

- App bundle: ~50-100 MB
- DMG file: ~40-80 MB (compressed)

Make sure your hosting supports these file sizes.





