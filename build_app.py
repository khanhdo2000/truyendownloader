#!/usr/bin/env python3
"""
Build script for creating standalone desktop application
"""

import subprocess
import sys
import os
import platform

def get_version():
    """Get version from version.py file"""
    try:
        # Try to read version from version.py
        version_file = os.path.join(os.path.dirname(__file__), 'version.py')
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                for line in f:
                    if line.startswith('__version__'):
                        version = line.split('=')[1].strip().strip('"').strip("'")
                        return version
    except:
        pass
    return "1.0.0"

def create_windows_version_info(version):
    """Create Windows version info file for PyInstaller"""
    try:
        version_parts = version.split('.')
        major = version_parts[0] if len(version_parts) > 0 else '1'
        minor = version_parts[1] if len(version_parts) > 1 else '0'
        patch = version_parts[2] if len(version_parts) > 2 else '0'
        
        version_info = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'TruyenFull'),
        StringStruct(u'FileDescription', u'TruyenFull Downloader'),
        StringStruct(u'FileVersion', u'{version}'),
        StringStruct(u'InternalName', u'TruyenFullDownloader'),
        StringStruct(u'LegalCopyright', u'Copyright (C) 2024'),
        StringStruct(u'OriginalFilename', u'TruyenFullDownloader.exe'),
        StringStruct(u'ProductName', u'TruyenFull Downloader'),
        StringStruct(u'ProductVersion', u'{version}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)"""
        version_info_file = os.path.join(os.path.dirname(__file__), 'version_info.txt')
        with open(version_info_file, 'w') as f:
            f.write(version_info)
        return version_info_file
    except Exception as e:
        print(f"Warning: Could not create version info file: {e}")
        return None

def build_app():
    """Build the desktop application using PyInstaller"""
    
    import shutil
    system = platform.system()
    app_name = "TruyenFullDownloader"
    version = get_version()
    
    print(f"Building version: {version}")
    
    # Find Python with tkinter support
    python_cmd = shutil.which('python3')
    
    # On macOS, prefer system Python which has tkinter
    if system == 'Darwin':
        system_python = '/usr/bin/python3'
        if os.path.exists(system_python):
            try:
                result = subprocess.run([system_python, '-c', 'import tkinter'], 
                                       capture_output=True, text=True)
                if result.returncode == 0:
                    python_cmd = system_python
                    print("Using system Python (has tkinter support)")
            except:
                pass
    
    if not python_cmd:
        print("Error: Python 3 not found")
        sys.exit(1)
    
    # Check if PyInstaller is available
    try:
        subprocess.run([python_cmd, '-c', 'import PyInstaller'], 
                      check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("PyInstaller not found. Installing...")
        subprocess.run([python_cmd, '-m', 'pip', 'install', '--user', 
                       'pyinstaller', 'requests', 'beautifulsoup4', 'lxml'], 
                      check=True)
    
    # Clean previous builds
    import time
    if os.path.exists('dist'):
        try:
            shutil.rmtree('dist')
        except OSError as e:
            print(f"Warning: Could not remove dist directory: {e}")
            print("Trying alternative cleanup method...")
            # Try alternative cleanup on macOS
            if platform.system() == 'Darwin':
                subprocess.run(['rm', '-rf', 'dist'], check=False)
            time.sleep(1)

    if os.path.exists('build'):
        try:
            shutil.rmtree('build')
        except OSError as e:
            print(f"Warning: Could not remove build directory: {e}")
            if platform.system() == 'Darwin':
                subprocess.run(['rm', '-rf', 'build'], check=False)
            time.sleep(1)
    
    # PyInstaller command - creates standalone executable (no Python needed)
    cmd = [
        python_cmd, '-m', 'PyInstaller',
        '--name', app_name,
        '--windowed',  # No console window (GUI only)
        '--add-data', 'truyenfull_downloader.py:.',  # Include the downloader module
        '--add-data', 'site_adapters.py:.',  # Include site adapters module
        '--add-data', 'version.py:.',  # Include version file
        '--hidden-import', 'tkinter',
        '--hidden-import', 'requests',
        '--hidden-import', 'bs4',
        '--hidden-import', 'lxml',
        '--hidden-import', 'ebooklib',
        '--hidden-import', 'ebooklib.epub',
        '--hidden-import', 'version',
        '--hidden-import', 'site_adapters',
        '--collect-all', 'ebooklib',  # Collect all ebooklib data files
        '--collect-all', 'tkinter',   # Collect all tkinter data files
        'truyenfull_gui.py'
    ]

    # Platform-specific adjustments
    if system == 'Darwin':  # macOS
        # Use --onedir for macOS to create proper .app bundle
        cmd.insert(3, '--onedir')  # Insert after 'PyInstaller'
        cmd.extend([
            '--osx-bundle-identifier', 'com.truyenfull.downloader'
        ])
        # Add macOS icon
        if os.path.exists('icon.icns'):
            cmd.extend(['--icon', 'icon.icns'])
        # Note: macOS version info is typically set via Info.plist, but PyInstaller
        # will use CFBundleShortVersionString from the bundle identifier
    elif system == 'Windows':
        # Use --onefile for Windows (single .exe file)
        cmd.insert(3, '--onefile')  # Insert after 'PyInstaller'
        cmd[cmd.index('truyenfull_downloader.py:.')] = 'truyenfull_downloader.py;.'
        cmd[cmd.index('site_adapters.py:.')] = 'site_adapters.py;.'
        cmd[cmd.index('version.py:.')] = 'version.py;.'
        # Add Windows icon
        if os.path.exists('icon.ico'):
            cmd.extend(['--icon', 'icon.ico'])
        # Windows version info file
        version_info_file = create_windows_version_info(version)
        if version_info_file:
            cmd.extend(['--version-file', version_info_file])
    else:
        # Linux: use --onefile for single executable
        cmd.insert(3, '--onefile')  # Insert after 'PyInstaller'
    
    print("Building desktop application...")
    print(f"Using Python: {python_cmd}")
    print()
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✓ Build successful!")
        print(f"\nOutput location:")
        if system == 'Windows':
            print(f"  dist/{app_name}/")
        else:
            print(f"  dist/{app_name}.app")
            print(f"  dist/{app_name}/")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    build_app()

