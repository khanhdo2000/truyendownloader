@echo off
REM Build script for Windows

echo Building TruyenFull Downloader Desktop App...

REM Check if PyInstaller is installed
where pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

REM Get version from version.py
for /f "tokens=2 delims=^=" %%a in ('findstr "__version__" version.py') do set VERSION=%%a
set VERSION=%VERSION:"=%
set VERSION=%VERSION:'=%
set VERSION=%VERSION: =%
if "%VERSION%"=="" set VERSION=1.0.0
echo Building version: %VERSION%

REM Build the app (standalone executable - no Python needed)
pyinstaller --name TruyenFullDownloader ^
    --windowed ^
    --onefile ^
    --add-data "truyenfull_downloader.py;." ^
    --add-data "version.py;." ^
    --hidden-import tkinter ^
    --hidden-import requests ^
    --hidden-import bs4 ^
    --hidden-import lxml ^
    --hidden-import ebooklib ^
    --hidden-import ebooklib.epub ^
    --hidden-import version ^
    --collect-all ebooklib ^
    --collect-all tkinter ^
    truyenfull_gui.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build successful!
    echo Executable: dist\TruyenFullDownloader.exe
) else (
    echo.
    echo Build failed
    exit /b 1
)

