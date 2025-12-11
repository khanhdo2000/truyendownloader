# Multi-Site Vietnamese Novel Downloader

A powerful desktop application and command-line tool for downloading Vietnamese novels from multiple popular websites and converting them to EPUB format.

## Supported Websites

✅ **TruyenFull** (truyenfull.vision, truyenfull.vn)
✅ **TangThuVien** (truyen.tangthuvien.vn)
✅ **LaoPhatGia** (laophatgia.net)

The application automatically detects which website you're downloading from and uses the appropriate adapter.

## Features

- 📚 **Multi-site support** - Download from multiple Vietnamese novel websites
- 🔍 **Auto-detection** - Automatically detects and selects the right website adapter
- 📖 **EPUB generation** - Creates professional EPUB files with table of contents and cover images
- 🎯 **Chapter range selection** - Download specific chapter ranges
- ⏸️ **Pause/Resume** - Stop downloads and create EPUB with chapters already downloaded
- 💾 **Smart caching** - Automatically skips already downloaded chapters
- 🖥️ **Dual interface** - Both GUI and command-line options
- 🌐 **Chapter & Story URLs** - Works with both story main pages and individual chapter URLs

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Or install manually:
pip install requests beautifulsoup4 ebooklib
```

**For GUI application**: Ensure tkinter is installed
- **macOS**: Usually included with Python
- **Linux**: `sudo apt-get install python3-tk` (Ubuntu/Debian) or `sudo yum install python3-tkinter` (RHEL/CentOS)
- **Windows**: Included with Python

## Usage

### Desktop GUI Application (Recommended)

The easiest way to use the downloader:

```bash
python truyenfull_gui.py
```

**GUI Features:**
1. Enter the URL of any supported story or chapter
2. Select output directory (default: ~/Downloads/truyenfull_downloader)
3. Optional: Set chapter range (start/end)
4. Adjust request delay (minimum 2 seconds - be respectful to servers!)
5. Click "Tải xuống" (Download) to start
6. Monitor progress in the log window
7. Stop anytime and get EPUB with downloaded chapters

### Command Line Interface

For automation and scripting:

```bash
# Download entire story
python truyenfull_downloader.py https://truyenfull.vision/story-name/

# Download from TangThuVien
python truyenfull_downloader.py https://truyen.tangthuvien.vn/doc-truyen/story-name

# Download from LaoPhatGia
python truyenfull_downloader.py https://laophatgia.net/truyen/story-name

# Download specific chapter range
python truyenfull_downloader.py https://truyenfull.vision/story-name/ --start 10 --end 20

# Custom output directory
python truyenfull_downloader.py https://truyenfull.vision/story-name/ -o /path/to/output

# Adjust request delay (seconds)
python truyenfull_downloader.py https://truyenfull.vision/story-name/ --delay 3.0
```

#### Command Line Options

```
positional arguments:
  url                   URL of the story page on any supported website

optional arguments:
  -h, --help           show this help message and exit
  -o OUTPUT, --output OUTPUT
                       Output directory (default: story title)
  --start START        Start chapter number (default: 1)
  --end END            End chapter number (default: all)
  --delay DELAY        Delay between requests in seconds (minimum: 2.0, default: 2.0)
```

## Example URLs

### TruyenFull
```
https://truyenfull.vision/cam-nang-sinh-ton-cua-ke-me-an-o-co-dai/
https://truyenfull.vision/cam-nang-sinh-ton-cua-ke-me-an-o-co-dai/chuong-1/
```

### TangThuVien
```
https://truyen.tangthuvien.vn/doc-truyen/linh-vu-thien-ha
https://truyen.tangthuvien.vn/doc-truyen/linh-vu-thien-ha/chuong-1
```

### LaoPhatGia
```
https://laophatgia.net/truyen/toan-chuc-phap-su
https://laophatgia.net/truyen/toan-chuc-phap-su/chuong-1.html
```

## Output Structure

```
output_directory/
├── story_id/              # Story-specific folder (uses unique ID)
│   ├── chapter_0001.txt   # Individual chapter files
│   ├── chapter_0002.txt
│   ├── ...
│   ├── complete_story.txt # All chapters in one file
│   ├── metadata.json      # Story metadata
│   └── cover.jpg          # Downloaded cover image (if available)
└── Story-Title.epub       # Final EPUB file (in root directory)
```

## Architecture

The application uses a modular adapter pattern for multi-site support:

### Site Adapters

Each website has its own adapter implementing the `SiteAdapter` interface:

- `TruyenFullAdapter` - For truyenfull.vision
- `TangThuVienAdapter` - For truyen.tangthuvien.vn
- `LaoPhatGiaAdapter` - For laophatgia.net

### Site Detection

The `SiteDetector` automatically identifies which website you're downloading from and selects the appropriate adapter. No manual configuration needed!

### Adding New Sites

To add support for a new website:

1. Create a new adapter class in `site_adapters.py` extending `SiteAdapter`
2. Implement required methods:
   - `site_name` - Display name
   - `supported_domains` - List of domain patterns
   - `normalize_url()` - Convert chapter URLs to story URLs
   - `get_story_info()` - Extract story metadata and chapter list
   - `get_chapter_content()` - Extract chapter text
3. Register the adapter in `SiteDetector.ADAPTERS`

Example adapter structure:
```python
class NewSiteAdapter(SiteAdapter):
    @property
    def site_name(self):
        return "NewSite"

    @property
    def supported_domains(self):
        return ['newsite.com', 'www.newsite.com']

    # Implement other required methods...
```

## Rate Limiting & Ethics

⚠️ **Important**: This tool enforces a minimum 2-second delay between requests to be respectful to website servers.

- Default delay: 2.0 seconds
- Minimum delay: 2.0 seconds (enforced)
- Be considerate: Don't reduce the delay or hammer the servers
- The tool will automatically skip already-downloaded chapters

## Features in Detail

### Auto-detection
Paste any story or chapter URL from supported sites. The app automatically:
- Detects which website you're using
- Selects the appropriate adapter
- Normalizes chapter URLs to story URLs
- Fetches the complete chapter list

### Smart Resume
If you stop a download:
- Already downloaded chapters are saved as individual `.txt` files
- Restarting the download will skip existing chapters
- EPUB is created from all available chapters

### EPUB Generation
Creates professional EPUB files with:
- Properly formatted table of contents
- Cover image (if available from the website)
- Story metadata (title, author, description)
- Clean chapter formatting
- Vietnamese language support

## Building Desktop Application

To create a standalone executable that doesn't require Python installation:

### macOS/Linux:
```bash
./build.sh
```

Or use the Python script:
```bash
python build_app.py
```

### Windows:
```cmd
build.bat
```

The executable will be created in the `dist/` folder:
- **macOS/Linux**: `dist/TruyenFullDownloader`
- **Windows**: `dist/TruyenFullDownloader.exe`

You can distribute this executable to others without requiring them to install Python or dependencies.

### Build Requirements

- PyInstaller (automatically installed via requirements.txt)
- All dependencies from requirements.txt

## Troubleshooting

### No chapters found
- Verify the URL is correct and accessible in a browser
- Some stories might have different page structures
- Check if the website is currently accessible

### EPUB generation fails
- Ensure `ebooklib` is installed: `pip install ebooklib`
- Check that chapters were downloaded successfully
- Look for error messages in the log

### Website not detected
- Verify the URL is from one of the supported sites
- Check for typos in the domain name
- Make sure you're using the correct URL format

### Connection errors
- Check your internet connection
- The website might be temporarily down
- Try increasing the delay with `--delay 3.0`

### GUI issues
- Make sure tkinter is installed (usually included with Python)
- Try running from command line to see error messages
- Check Python version (3.7+ required)

## Requirements

See `requirements.txt`:
```
requests>=2.31.0
beautifulsoup4>=4.12.0
ebooklib>=0.18
```

## Platform Support

- ✅ Windows
- ✅ macOS
- ✅ Linux

Default download location:
- Windows: `C:\Users\YourName\Downloads\truyenfull_downloader`
- macOS: `~/Downloads/truyenfull_downloader`
- Linux: `~/Downloads/truyenfull_downloader`

## Version History

### v1.1.0 - Multi-Site Support (Current)
- ✨ Added support for TangThuVien and LaoPhatGia
- 🏗️ Implemented adapter pattern architecture
- 🔍 Auto-detection of website from URL
- 📝 Updated GUI with multi-site support
- 📚 Improved documentation

### v1.0.0 - Initial Release
- Initial release with TruyenFull support
- EPUB generation
- GUI and CLI interfaces

## License

This tool is for personal use only. Please respect the website's terms of service and copyright of the original content creators.

## Contributing

Contributions are welcome! To add support for a new website:

1. Fork the repository
2. Create a new adapter in `site_adapters.py`
3. Test thoroughly with multiple stories
4. Submit a pull request with:
   - Adapter implementation
   - Example URLs
   - Test results

## Disclaimer

This tool is provided as-is for personal use only. Users are responsible for complying with the terms of service of the websites they download from. The authors are not responsible for any misuse of this tool.

## Credits

Developed for the Vietnamese reading community. Special thanks to all the translators and authors who make these stories available.
