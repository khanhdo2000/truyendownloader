# Distribution Guide for TruyenFull Downloader

This guide covers the best practices for distributing your macOS application to users.

## Distribution Options (Ranked by Recommendation)

### 1. **GitHub Releases** ⭐ (Recommended)

**Pros:**
- Free and reliable
- Version control and release history
- Direct download links
- Automatic checksums
- No file size limits for public repos
- Easy to share and track downloads

**Steps:**
1. Create a GitHub repository (if not already)
2. Tag your release: `git tag v1.0.0`
3. Push tag: `git push origin v1.0.0`
4. Go to GitHub → Releases → Draft a new release
5. Upload `TruyenFullDownloader.app` (or create a DMG - see below)
6. Add release notes
7. Share the release URL with users

**Download Link Format:**
```
https://github.com/yourusername/truyenfull/releases/download/v1.0.0/TruyenFullDownloader.dmg
```

### 2. **Create a DMG for Better User Experience**

A DMG (Disk Image) is the standard macOS distribution format. It provides:
- Professional appearance
- Easy drag-and-drop installation
- Automatic mounting/unmounting

**Create DMG Script:**
```bash
# Run: ./create_dmg.sh
```

### 3. **Direct Website Hosting**

If you have a website:
- Upload the app/DMG to your web server
- Provide a direct download link
- Consider using a CDN for faster downloads

### 4. **Cloud Storage (Temporary Solution)**

- **Dropbox/Google Drive**: Share public links
- **OneDrive/iCloud**: Share download links
- ⚠️ Not ideal for production (link expiration, bandwidth limits)

## Important macOS Considerations

### Code Signing (Recommended)

Without code signing, users will see:
> "TruyenFullDownloader.app cannot be opened because the developer cannot be verified"

**To sign your app:**
```bash
# Requires Apple Developer account ($99/year)
codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" dist/TruyenFullDownloader.app
```

### Notarization (Required for macOS Catalina+)

For apps distributed outside the App Store, notarization is required:
```bash
# After signing, create a zip
ditto -c -k --keepParent dist/TruyenFullDownloader.app dist/TruyenFullDownloader.zip

# Submit for notarization
xcrun notarytool submit dist/TruyenFullDownloader.zip --apple-id your@email.com --team-id YOUR_TEAM_ID --password YOUR_APP_PASSWORD
```

### Without Code Signing (User Workaround)

Users can bypass Gatekeeper by:
1. Right-click the app → Open
2. Or: System Settings → Privacy & Security → Allow anyway

**Include instructions in your README:**
```markdown
## Installation

1. Download TruyenFullDownloader.dmg
2. Open the DMG file
3. Drag TruyenFullDownloader.app to Applications folder
4. If you see a security warning:
   - Right-click the app → Open
   - Or: System Settings → Privacy & Security → Allow
```

## Recommended Distribution Workflow

1. **Build the app**: `./build.sh`
2. **Create DMG**: `./create_dmg.sh` (optional but recommended)
3. **Test on a clean Mac** (without your dev environment)
4. **Upload to GitHub Releases**
5. **Share the release URL**

## Example README Section

Add this to your README.md:

```markdown
## Download

Download the latest version from [Releases](https://github.com/yourusername/truyenfull/releases)

### Installation

1. Download `TruyenFullDownloader.dmg`
2. Open the DMG file
3. Drag `TruyenFullDownloader.app` to your Applications folder
4. Launch from Applications or Spotlight

### First Launch

If macOS shows a security warning:
- Right-click the app → **Open**
- Or go to **System Settings → Privacy & Security** and click **Open Anyway**
```

## Update Mechanism (Future Enhancement)

Consider implementing:
- Version check on startup
- Automatic update notifications
- Direct download link to latest release





