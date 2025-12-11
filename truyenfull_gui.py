#!/usr/bin/env python3
"""
Multi-Site Novel Downloader - Desktop GUI Application
A graphical interface for downloading novels/stories from multiple Vietnamese novel websites
Supports: TruyenFull, TangThuVien, LaoPhatGia
"""

import sys
import os
import platform

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, filedialog, messagebox
except ImportError:
    print("Error: tkinter is not installed.")
    print("Please install tkinter:")
    print("  macOS: tkinter is usually included with Python")
    print("  Linux: sudo apt-get install python3-tk (Ubuntu/Debian)")
    print("         or: sudo yum install python3-tkinter (RHEL/CentOS)")
    print("  Windows: tkinter is included with Python")
    sys.exit(1)

import threading
import socket
import tempfile
from truyenfull_downloader import TruyenFullDownloader
try:
    from version import __version__
except ImportError:
    __version__ = "1.0.0"
try:
    import ebooklib
    EPUB_AVAILABLE = True
except ImportError:
    EPUB_AVAILABLE = False


class SingleInstance:
    """Ensure only one instance of the application runs at a time"""

    def __init__(self, app_name='TruyenFullDownloader'):
        self.app_name = app_name
        self.lock_socket = None
        self.lock_file = None

        if platform.system() == 'Windows':
            # Windows: Use a socket bound to localhost
            self.lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.lock_socket.bind(('127.0.0.1', 47777))
            except OSError:
                self.lock_socket = None
                return
        else:
            # macOS/Linux: Use a lock file
            lock_file_path = os.path.join(tempfile.gettempdir(), f'{app_name}.lock')
            try:
                self.lock_file = open(lock_file_path, 'w')
                import fcntl
                # Use flock for exclusive lock (more reliable)
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (IOError, OSError, BlockingIOError) as e:
                if self.lock_file:
                    self.lock_file.close()
                self.lock_file = None
                return

    def is_already_running(self):
        """Check if another instance is already running"""
        if platform.system() == 'Windows':
            return self.lock_socket is None
        else:
            return self.lock_file is None

    def __del__(self):
        """Cleanup lock resources"""
        if self.lock_socket:
            try:
                self.lock_socket.close()
            except:
                pass
        if self.lock_file:
            try:
                import fcntl
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
            except:
                pass


def get_default_download_dir():
    """Get platform-specific default download directory"""
    system = platform.system()
    if system == 'Darwin':  # macOS
        return os.path.expanduser("~/Downloads/truyenfull_downloader")
    elif system == 'Windows':
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads", "truyenfull_downloader")
        return downloads_path
    else:  # Linux and others
        return os.path.expanduser("~/Downloads/truyenfull_downloader")


class TruyenFullGUI:
    def __init__(self, root):
        print("Initializing TruyenFullGUI...")
        self.root = root
        self.root.title(f"Tải Truyện - Multi-Site Downloader v{__version__} by minhnhatdigital")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Set a visible background color
        self.root.configure(bg='#f0f0f0')
        print("Window properties set")
        
        # Configure root window first
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        print("Root window configured")
        
        # Try to set a ttk theme that works
        try:
            style = ttk.Style()
            available_themes = style.theme_names()
            print(f"Available ttk themes: {available_themes}")
            # Try to use a theme that's more likely to work
            if 'clam' in available_themes:
                style.theme_use('clam')
            elif 'default' in available_themes:
                style.theme_use('default')
            elif available_themes:
                style.theme_use(available_themes[0])
            print(f"Using theme: {style.theme_use()}")
        except Exception as e:
            print(f"Could not set ttk theme: {e}")
        
        # Variables
        self.downloader = None
        self.is_downloading = False
        self.current_progress = 0
        self.total_chapters = 0
        
        print("Setting up UI...")
        self.setup_ui()
        print("UI setup complete")
        
        # Force update and make sure everything is visible
        self.root.update()
        self.root.update_idletasks()
        print("Window updated, centering...")
        self.center_window()
        
        # Force window to be visible
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.update()
        print("Initialization complete")
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """Setup the user interface"""
        print("  Creating main frame...")
        # Main container - use regular Frame with background for better visibility
        main_frame = tk.Frame(self.root, bg='#f0f0f0', padx=10, pady=10)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)  # Make log area expandable
        print("  Main frame created and gridded")
        
        # Title - use regular Label for better visibility across Python versions
        print("  Creating title label...")
        title_label = tk.Label(main_frame, text=f"Tải Truyện - Multi-Site v{__version__}",
                              font=("Arial", 16, "bold"), bg='#f0f0f0', fg='#000000')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 5))

        # Credit label
        credit_label = tk.Label(main_frame, text="by minhnhatdigital",
                               font=("Arial", 10, "italic"), bg='#f0f0f0', fg='#888888')
        credit_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))

        # Subtitle with supported sites
        subtitle_label = tk.Label(main_frame, text="Hỗ trợ: TruyenFull, TangThuVien, LaoPhatGia, WordPress (tất cả)",
                                 font=("Arial", 9), bg='#f0f0f0', fg='#666666')
        subtitle_label.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        print("  Title label created")

        # URL input
        ttk.Label(main_frame, text="URL Truyện:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=60)
        url_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))

        # Password input (for WordPress password-protected chapters)
        ttk.Label(main_frame, text="Mật khẩu (tùy chọn):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(main_frame, textvariable=self.password_var, width=60, show="")
        password_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))

        # Output directory
        ttk.Label(main_frame, text="Thư mục lưu:").grid(row=5, column=0, sticky=tk.W, pady=5)
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        output_frame.columnconfigure(0, weight=1)

        # Set default output directory based on platform
        default_output = get_default_download_dir()
        self.output_var = tk.StringVar(value=default_output)
        output_entry = ttk.Entry(output_frame, textvariable=self.output_var, width=50)
        output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        browse_btn = ttk.Button(output_frame, text="Chọn...", command=self.browse_folder)
        browse_btn.grid(row=0, column=1)

        # Chapter range
        range_frame = ttk.LabelFrame(main_frame, text="Phạm vi chương (Tùy chọn)", padding="10")
        range_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        range_frame.columnconfigure(1, weight=1)
        range_frame.columnconfigure(3, weight=1)
        
        ttk.Label(range_frame, text="Bắt đầu:").grid(row=0, column=0, padx=5)
        self.start_var = tk.StringVar(value="1")
        start_spin = ttk.Spinbox(range_frame, from_=1, to=99999, textvariable=self.start_var, width=10)
        start_spin.grid(row=0, column=1, padx=5)
        
        ttk.Label(range_frame, text="Kết thúc:").grid(row=0, column=2, padx=5)
        self.end_var = tk.StringVar()
        end_spin = ttk.Spinbox(range_frame, from_=1, to=99999, textvariable=self.end_var, width=10)
        end_spin.grid(row=0, column=3, padx=5)
        
        ttk.Label(range_frame, text="(Để trống Kết thúc để tải tất cả chương)").grid(row=0, column=4, padx=10)
        
        # Delay setting - minimum 2 seconds
        delay_frame = ttk.Frame(main_frame)
        delay_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(delay_frame, text="Độ trễ yêu cầu (giây):").grid(row=0, column=0, padx=5)
        self.delay_var = tk.StringVar(value="2.0")
        
        # Create spinbox with minimum 2.0
        delay_spin = ttk.Spinbox(delay_frame, from_=2.0, to=10.0, increment=0.5, 
                                textvariable=self.delay_var, width=10)
        delay_spin.grid(row=0, column=1, padx=5)
        
        # Validate input to ensure minimum 2.0
        def validate_delay(value):
            try:
                val = float(value)
                if val < 2.0:
                    self.delay_var.set("2.0")
                    return False
                return True
            except ValueError:
                if value == "":
                    return True
                self.delay_var.set("2.0")
                return False
        
        # Bind validation on focus out
        delay_spin.bind('<FocusOut>', lambda e: validate_delay(self.delay_var.get()))
        delay_spin.bind('<Return>', lambda e: validate_delay(self.delay_var.get()))
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Sẵn sàng")
        progress_label = ttk.Label(main_frame, textvariable=self.progress_var)
        progress_label.grid(row=8, column=0, columnspan=2, pady=(10, 5))

        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate')
        self.progress_bar.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Log output
        log_frame = ttk.LabelFrame(main_frame, text="Nhật ký", padding="5")
        log_frame.grid(row=10, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(10, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=11, column=0, columnspan=2, pady=10)
        
        self.download_btn = ttk.Button(button_frame, text="Tải xuống", 
                                       command=self.start_download, width=20)
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Dừng", 
                                    command=self.stop_download, state=tk.DISABLED, width=20)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(button_frame, text="Xóa nhật ký", 
                                    command=self.clear_log, width=20)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
    
    def browse_folder(self):
        """Open folder browser dialog"""
        folder = filedialog.askdirectory(title="Chọn thư mục lưu")
        if folder:
            self.output_var.set(folder)
    
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        """Clear the log"""
        self.log_text.delete(1.0, tk.END)
    
    def show_about(self):
        """Show about dialog with version information"""
        # Create custom dialog window
        about_window = tk.Toplevel(self.root)
        about_window.title("Giới thiệu")
        about_window.geometry("500x500")
        about_window.resizable(False, False)

        # Center the window
        about_window.update_idletasks()
        x = (about_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (about_window.winfo_screenheight() // 2) - (500 // 2)
        about_window.geometry(f'500x500+{x}+{y}')

        # Create main frame with padding
        main_frame = tk.Frame(about_window, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(main_frame,
                              text="Multi-Site Novel Downloader",
                              font=("Arial", 14, "bold"),
                              bg='white')
        title_label.pack(pady=(0, 5))

        # Credit
        credit_label = tk.Label(main_frame,
                               text="by minhnhatdigital",
                               font=("Arial", 10, "italic"),
                               bg='white',
                               fg='#666666')
        credit_label.pack(pady=(0, 15))

        # Scrollable text area for information
        text_frame = tk.Frame(main_frame, bg='white')
        text_frame.pack(fill=tk.BOTH, expand=True)

        about_text = scrolledtext.ScrolledText(text_frame,
                                              wrap=tk.WORD,
                                              width=50,
                                              height=18,
                                              font=("Arial", 10),
                                              bg='#f9f9f9',
                                              relief=tk.FLAT,
                                              padx=10,
                                              pady=10)
        about_text.pack(fill=tk.BOTH, expand=True)

        # Insert content
        content = f"""Phiên bản: {__version__}

Ứng dụng tải truyện từ nhiều trang web:
• TruyenFull (truyenfull.vision)
• TangThuVien (truyen.tangthuvien.vn)
• LaoPhatGia (laophatgia.net)
• WordPress (tất cả các trang WordPress)

Tính năng:
• Tải truyện với đầy đủ chương
• Tạo file EPUB với mục lục và ảnh bìa
• Hỗ trợ tải theo phạm vi chương
• Tự động bỏ qua chương đã tải
• Tạm dừng và tạo EPUB với chương đã tải
• Tự động phát hiện trang web
• Hỗ trợ nội dung bảo vệ bằng mật khẩu (WordPress)
• Tự động chuẩn hóa tên file
• Tải nhiều chương song song
• Bảo toàn cấu trúc dòng trong nội dung

Cách sử dụng:
1. Nhập URL trang truyện hoặc chương
2. (Tùy chọn) Nhập mật khẩu nếu có chương bảo vệ
3. Chọn thư mục lưu file
4. (Tùy chọn) Đặt phạm vi chương muốn tải
5. Nhấn "Tải xuống"

Lưu ý:
• Độ trễ tối thiểu 2 giây để tôn trọng server
• File EPUB được tạo tự động sau khi tải
• Chương đã tải sẽ được bỏ qua khi tải lại"""

        about_text.insert('1.0', content)
        about_text.config(state=tk.DISABLED)  # Make read-only

        # Close button
        close_btn = ttk.Button(main_frame, text="Đóng", command=about_window.destroy, width=15)
        close_btn.pack(pady=(15, 0))

        # Make modal
        about_window.transient(self.root)
        about_window.grab_set()
        self.root.wait_window(about_window)
    
    def start_download(self):
        """Start the download process"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Lỗi", "Vui lòng nhập URL truyện")
            return
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Import site detector to validate URL
        from site_adapters import SiteDetector
        from urllib.parse import urlparse

        # Check if URL is from a supported site
        parsed = urlparse(url)
        supported_sites = SiteDetector.get_supported_sites()
        is_supported = any(
            any(domain in parsed.netloc for domain in site['domains'])
            for site in supported_sites
        )

        if not is_supported:
            site_list = '\n'.join([f"  • {site['name']}: {', '.join(site['domains'])}" for site in supported_sites])
            messagebox.showerror(
                "Lỗi",
                f"URL phải từ một trong các trang web được hỗ trợ:\n\n{site_list}\n\nVí dụ:\n  • https://truyenfull.vision/ten-truyen/\n  • https://truyen.tangthuvien.vn/doc-truyen/ten-truyen\n  • https://laophatgia.net/truyen/ten-truyen"
            )
            return
        
        output_dir = self.output_var.get().strip()
        if not output_dir:
            # Use default if empty
            output_dir = get_default_download_dir()
        else:
            # Expand user path (handle ~)
            output_dir = os.path.expanduser(output_dir)
        
        try:
            start_chapter = int(self.start_var.get()) if self.start_var.get() else 1
        except ValueError:
            start_chapter = 1
        
        try:
            end_chapter = int(self.end_var.get()) if self.end_var.get() else None
        except ValueError:
            end_chapter = None
        
        try:
            delay = float(self.delay_var.get())
            # Enforce minimum 2.0 seconds
            if delay < 2.0:
                delay = 2.0
                self.delay_var.set("2.0")
        except ValueError:
            delay = 2.0
            self.delay_var.set("2.0")

        # Get password if provided
        password = self.password_var.get().strip() if self.password_var.get().strip() else None

        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_bar['value'] = 0
        self.progress_var.set("Đang bắt đầu tải xuống...")

        # Start download in separate thread
        thread = threading.Thread(target=self.download_thread,
                                 args=(url, output_dir, start_chapter, end_chapter, delay, password),
                                 daemon=True)
        thread.start()
    
    def download_thread(self, url, output_dir, start_chapter, end_chapter, delay, password=None):
        """Download thread function"""
        try:
            self.log(f"Initializing downloader...")
            self.downloader = TruyenFullDownloader(delay=delay, password=password)
            
            # Override methods to log to GUI and track progress
            original_get_story_info = self.downloader.get_story_info
            original_get_chapter_content = self.downloader.get_chapter_content
            original_get_page = self.downloader.get_page
            
            def get_story_info_with_log(story_url):
                # Normalize URL first
                normalized_url, was_chapter = self.downloader.normalize_url(story_url)
                if was_chapter:
                    self.log(f"Phát hiện URL chương. Đang trích xuất truyện từ: {normalized_url}")
                else:
                    self.log(f"Đang lấy thông tin truyện từ {normalized_url}...")
                
                result = original_get_story_info(normalized_url)
                if result:
                    self.log(f"Tìm thấy: {result['title']}")
                    self.log(f"Tác giả: {result['author']}")
                    self.log(f"Tổng số chương: {len(result['chapters'])}")
                    self.total_chapters = len(result['chapters'])
                return result
            
            def get_chapter_content_with_log(chapter_url):
                result = original_get_chapter_content(chapter_url)
                if result and self.is_downloading:
                    self.current_progress += 1
                    progress_pct = (self.current_progress / self.total_chapters * 100) if self.total_chapters > 0 else 0
                    self.progress_bar['value'] = progress_pct
                    self.progress_var.set(f"Đang tải chương {self.current_progress}/{self.total_chapters}")
                    self.log(f"Đã tải: {result['title']}")
                return result
            
            # Override print to capture download_story output
            import builtins
            original_print = builtins.print
            
            def gui_print(*args, **kwargs):
                """Capture print statements and log to GUI"""
                message = ' '.join(str(arg) for arg in args)
                if message.strip():
                    self.log(message)
            
            self.downloader.get_story_info = get_story_info_with_log
            self.downloader.get_chapter_content = get_chapter_content_with_log
            
            # Get story info first to determine total chapters
            story_info = self.downloader.get_story_info(url)
            if not story_info:
                self.log("Không thể lấy thông tin truyện")
                self.download_complete(False)
                return
            
            if not story_info['chapters']:
                self.log("Không tìm thấy chương nào.")
                self.download_complete(False)
                return
            
            # Calculate story-safe title for subdirectory
            import re
            safe_title = re.sub(r'[^\w\s-]', '', story_info['title']).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            
            # Store story info for stop functionality
            self.story_info = story_info
            
            # Calculate final output directory (download_story will add story subdirectory)
            # So we pass base directory, then calculate final after
            base_output_dir = output_dir  # This is the base directory from GUI
            
            # Calculate chapter range for progress tracking
            total_chapters = len(story_info['chapters'])
            start_idx = max(0, start_chapter - 1)
            end_idx = end_chapter if end_chapter else total_chapters
            end_idx = min(end_idx, total_chapters)
            chapters_to_download = end_idx - start_idx
            self.total_chapters = chapters_to_download
            self.current_progress = 0
            
            # Temporarily override print to capture download_story messages
            builtins.print = gui_print
            
            try:
                # Use the downloader's download_story method (includes EPUB generation)
                # download_story will automatically create story-specific subdirectory
                # Pass is_downloading flag to allow cancellation
                success = self.downloader.download_story(
                    url,
                    output_dir=base_output_dir,  # Base directory, download_story adds story subdirectory
                    start_chapter=start_chapter,
                    end_chapter=end_chapter,
                    is_downloading=lambda: self.is_downloading
                )
                
                # Calculate directories (root for EPUB, story_dir for txt/json)
                # download_story uses truyen_id for story directory
                truyen_id = story_info.get('truyen_id', 'unknown')
                if not base_output_dir:
                    root_dir = get_default_download_dir()
                else:
                    root_dir = base_output_dir
                
                story_dir = os.path.join(root_dir, truyen_id)
                
                # Store directories
                self.output_dir = story_dir
                self.root_dir = root_dir
                
                if success and self.is_downloading:
                    # Check if EPUB was created (in root directory)
                    safe_title = re.sub(r'[^\w\s-]', '', story_info['title']).strip()
                    safe_title = re.sub(r'[-\s]+', '-', safe_title)
                    epub_file = os.path.join(root_dir, f"{safe_title}.epub")
                    if os.path.exists(epub_file):
                        self.log(f"  Đã tạo file EPUB: {os.path.basename(epub_file)}")
                    
                    self.download_complete(True, story_dir, root_dir)
                elif not self.is_downloading:
                    # Download was stopped, create EPUB with downloaded chapters
                    self.log("Đã dừng tải xuống. Đang tạo EPUB với các chương đã tải...")
                    self.create_epub_from_downloaded(story_dir, root_dir, story_info)
                    self.download_complete(True, story_dir, root_dir, stopped=True)
                else:
                    self.download_complete(False)
            finally:
                # Restore original print
                builtins.print = original_print
        
        except Exception as e:
            self.log(f"Lỗi: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            self.download_complete(False)
    
    def download_complete(self, success, story_dir=None, root_dir=None, stopped=False):
        """Handle download completion"""
        self.is_downloading = False
        self.progress_bar['value'] = 100 if success else 0
        if stopped:
            self.progress_var.set("Đã dừng")
        else:
            self.progress_var.set("Hoàn thành" if success else "Thất bại")
        self.download_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        if success:
            # Check for EPUB file in root directory
            epub_files = []
            if root_dir and os.path.exists(root_dir):
                for file in os.listdir(root_dir):
                    if file.endswith('.epub'):
                        epub_files.append(file)
            
            if stopped:
                message = f"Đã dừng tải xuống!\n\nĐã tạo EPUB với các chương đã tải.\n\nChương đã lưu tại:\n{os.path.abspath(story_dir) if story_dir else 'N/A'}"
            else:
                message = f"Tải xuống hoàn tất thành công!\n\nChương đã lưu tại:\n{os.path.abspath(story_dir) if story_dir else 'N/A'}"
            
            if epub_files:
                message += f"\n\nEPUB đã lưu tại:\n{os.path.abspath(root_dir) if root_dir else 'N/A'}\n\nFile EPUB: {', '.join(epub_files)}"
            
            messagebox.showinfo("Thành công" if not stopped else "Đã dừng", message)
        else:
            messagebox.showerror("Lỗi", "Tải xuống thất bại. Vui lòng kiểm tra nhật ký để biết chi tiết.")
    
    def stop_download(self):
        """Stop the current download and create EPUB with downloaded chapters"""
        if self.is_downloading:
            self.is_downloading = False
            self.log("Đang dừng tải xuống...")
            self.progress_var.set("Đang dừng...")
            # The download thread will handle creating EPUB
    
    def create_epub_from_downloaded(self, story_dir, root_dir, story_info):
        """Create EPUB from already downloaded chapter files"""
        try:
            import re
            import glob
            
            if not story_dir or not os.path.exists(story_dir):
                self.log("Không tìm thấy thư mục chương")
                return
            
            # Find all chapter files in story directory
            chapter_files = sorted(glob.glob(os.path.join(story_dir, "chapter_*.txt")))
            
            if not chapter_files:
                self.log("Không tìm thấy chương nào đã tải")
                return
            
            self.log(f"Tìm thấy {len(chapter_files)} chương đã tải")
            
            # Read all chapters
            all_chapters = []
            for chapter_file in chapter_files:
                try:
                    with open(chapter_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # Parse the file: first line is title, rest is content
                    lines = content.split('\n', 1)
                    if len(lines) >= 2:
                        chapter_title = lines[0].strip()
                        chapter_content = lines[1].strip()
                    else:
                        chapter_title = os.path.basename(chapter_file)
                        chapter_content = content.strip()
                    
                    all_chapters.append({
                        'title': chapter_title,
                        'content': chapter_content
                    })
                except Exception as e:
                    self.log(f"Lỗi khi đọc {chapter_file}: {e}")
            
            if not all_chapters:
                self.log("Không thể đọc các chương đã tải")
                return
            
            self.log(f"Đang tạo EPUB với {len(all_chapters)} chương...")
            
            # Create EPUB using downloader's method (save to root directory)
            if self.downloader and EPUB_AVAILABLE:
                safe_title = re.sub(r'[^\w\s-]', '', story_info['title']).strip()
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                epub_path = self.downloader.create_epub(story_info, all_chapters, root_dir, epub_filename_base=safe_title)
                if epub_path:
                    self.log(f"  Đã tạo file EPUB: {os.path.basename(epub_path)}")
                else:
                    self.log("  Lỗi khi tạo EPUB")
            else:
                self.log("  Không thể tạo EPUB (ebooklib không có sẵn)")
        
        except Exception as e:
            self.log(f"Lỗi khi tạo EPUB: {e}")
            import traceback
            self.log(traceback.format_exc())


def main():
    # Check for single instance
    single_instance = SingleInstance()
    if single_instance.is_already_running():
        # Show error dialog
        root = tk.Tk()
        root.withdraw()  # Hide main window
        messagebox.showerror(
            "Application Already Running",
            "TruyenFull Downloader is already running.\n\n"
            "Only one instance of the application can run at a time.\n"
            "Please close the existing instance before starting a new one."
        )
        root.destroy()
        sys.exit(0)

    try:
        print("Starting TruyenFull Downloader GUI...")
        root = tk.Tk()
        print("Root window created")

        # Set a background color to ensure visibility
        root.configure(bg='#f0f0f0')
        print("Background configured")

        print("Creating GUI application...")
        app = TruyenFullGUI(root)
        print("GUI created, updating window...")

        root.update()
        root.update_idletasks()
        print("Window updated, starting mainloop...")

        # Force window to be visible
        root.deiconify()
        root.lift()
        root.focus_force()

        root.mainloop()
        print("Mainloop ended")
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        traceback.print_exc()
        import sys
        sys.exit(1)


if __name__ == '__main__':
    main()

