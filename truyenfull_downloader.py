#!/usr/bin/env python3
"""
Multi-Site Novel Downloader
A tool to download novels/stories from multiple Vietnamese novel websites
Supports: TruyenFull, TangThuVien, LaoPhatGia
"""

import requests
from bs4 import BeautifulSoup
import argparse
import os
import time
import re
import platform
from urllib.parse import urljoin, urlparse
import json
from site_adapters import SiteDetector

try:
    import ebooklib
    from ebooklib import epub
    EPUB_AVAILABLE = True
except ImportError:
    EPUB_AVAILABLE = False


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


class TruyenFullDownloader:
    def __init__(self, base_url=None, delay=2.0, site_adapter=None, password=None):
        """
        Initialize the downloader

        Args:
            base_url: Base URL of website (auto-detected if None) - DEPRECATED, use site_adapter instead
            delay: Delay between requests in seconds (minimum 2.0, to be respectful)
            site_adapter: Site adapter instance (auto-detected from URL if None)
            password: Password for password-protected content (optional)
        """
        self.base_url = base_url
        # Enforce minimum 2.0 seconds delay
        self.delay = max(2.0, float(delay))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.site_adapter = site_adapter
        self.password = password
    
    def normalize_url(self, url):
        """
        Normalize URL and extract story main page if chapter URL is provided
        Uses site adapter if available, otherwise falls back to legacy method

        Returns:
            tuple: (story_url, is_chapter_url)
        """
        # Auto-detect site adapter if not set
        if not self.site_adapter:
            self.site_adapter = SiteDetector.detect_site(url, self.session, self.delay, self.password)
            if not self.site_adapter:
                print(f"Warning: Could not detect site for URL: {url}")
                print("Supported sites:")
                for site in SiteDetector.get_supported_sites():
                    print(f"  - {site['name']}: {', '.join(site['domains'])}")
                return url, False

        return self.site_adapter.normalize_url(url)
    
    def get_page(self, url, password=None):
        """Fetch a page with error handling and password support"""
        try:
            time.sleep(self.delay)  # Be respectful to the server

            # Use provided password or instance password
            pwd = password or self.password

            # For WordPress password-protected posts
            if pwd:
                # First, try to get the page to see if it's password-protected
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                response.encoding = 'utf-8'

                # Check if password form is present
                if 'post-password-form' in response.text:
                    # Extract the form action and redirect_to from the form
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    form = soup.find('form', class_='post-password-form')

                    if form:
                        # Get the form action URL
                        form_action = form.get('action', '')
                        if not form_action:
                            # Default WordPress password form action
                            from urllib.parse import urljoin, urlparse
                            parsed = urlparse(url)
                            base_url = f"{parsed.scheme}://{parsed.netloc}"
                            form_action = urljoin(base_url, '/wp-login.php?action=postpass')

                        # Get redirect_to field
                        redirect_input = form.find('input', {'name': 'redirect_to'})
                        redirect_to = redirect_input.get('value', url) if redirect_input else url

                        # Submit the password to the form action
                        post_data = {
                            'post_password': pwd,
                            'Submit': 'Nhập',
                            'redirect_to': redirect_to
                        }

                        # Post to the form action URL
                        response = self.session.post(form_action, data=post_data, timeout=10, allow_redirects=True)
                        response.raise_for_status()
                        response.encoding = 'utf-8'

                        # If we're redirected, fetch the original URL again with the cookie
                        if response.url != url:
                            response = self.session.get(url, timeout=10)
                            response.raise_for_status()
                            response.encoding = 'utf-8'

                return response.text
            else:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def get_chapters_from_page(self, soup, base_url):
        """Extract chapter links from a single page"""
        chapter_links = []
        chapter_list = soup.find('div', id='list-chapter') or soup.find('ul', class_='list-chapter')
        
        if chapter_list:
            links = chapter_list.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if '/chuong-' in href or '/chapter-' in href:
                    full_url = urljoin(base_url, href)
                    chapter_title = link.get_text(strip=True)
                    chapter_links.append({
                        'url': full_url,
                        'title': chapter_title
                    })
        
        # If no chapters found in list, try alternative methods
        if not chapter_links:
            # Try to find chapter navigation or links
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if '/chuong-' in href or '/chapter-' in href:
                    full_url = urljoin(base_url, href)
                    chapter_title = link.get_text(strip=True)
                    if full_url not in [ch['url'] for ch in chapter_links]:
                        chapter_links.append({
                            'url': full_url,
                            'title': chapter_title
                        })
        
        return chapter_links
    
    def find_pagination_links(self, soup, story_url):
        """Find pagination links for chapter pages"""
        pagination_links = []
        
        # Look for pagination elements
        pagination = soup.find('div', class_=re.compile(r'pagination|phan-trang', re.I))
        if not pagination:
            # Try to find pagination in nav or ul elements
            pagination = soup.find('nav', class_=re.compile(r'pagination', re.I))
        if not pagination:
            pagination = soup.find('ul', class_=re.compile(r'pagination', re.I))
        
        if pagination:
            links = pagination.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                # Look for pagination patterns: /trang-2, /page-2, /p/2, etc.
                if re.search(r'/trang-\d+|/page-\d+|/p/\d+', href, re.I):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in pagination_links:
                        pagination_links.append(full_url)
        
        # Also check for "Next" or "Trang sau" links
        next_links = soup.find_all('a', href=True, string=re.compile(r'next|sau|tiếp', re.I))
        for link in next_links:
            href = link.get('href', '')
            if '/trang-' in href or '/page-' in href:
                full_url = urljoin(self.base_url, href)
                if full_url not in pagination_links:
                    pagination_links.append(full_url)
        
        # Sort pagination links to process in order
        def extract_page_num(url):
            match = re.search(r'/trang-(\d+)|/page-(\d+)', url, re.I)
            return int(match.group(1) or match.group(2)) if match else 0
        
        pagination_links.sort(key=extract_page_num)
        
        return pagination_links
    
    def get_truyen_id(self, soup):
        """Extract truyen-id from hidden input field"""
        truyen_id_input = soup.find('input', {'id': 'truyen-id'})
        if truyen_id_input:
            truyen_id = truyen_id_input.get('value', '')
            if truyen_id:
                return truyen_id
        return None
    
    def get_chapters_from_ajax(self, truyen_id, story_url):
        """Fetch all chapters from AJAX endpoint"""
        if not truyen_id:
            return []
        
        ajax_url = f"{self.base_url}/ajax.php?type=chapter_option&data={truyen_id}"
        html = self.get_page(ajax_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        chapter_links = []
        
        # Parse the AJAX response - contains <option> elements with relative chapter paths
        # Option values are like "chuong-1", "chuong-2", etc.
        options = soup.find_all('option', value=True)
        
        # Extract story base path from story_url
        from urllib.parse import urlparse
        parsed = urlparse(story_url)
        story_path = parsed.path.rstrip('/')
        
        for option in options:
            chapter_value = option.get('value', '').strip()
            if not chapter_value or chapter_value in ['', '0']:
                continue
            
            # Construct full URL: story_url + / + chapter_value + /
            # e.g., /cam-nang-sinh-ton-cua-ke-me-an-o-co-dai/ + chuong-1 + /
            if chapter_value.startswith('/'):
                full_url = urljoin(self.base_url, chapter_value)
            else:
                # Relative path: append to story path
                full_url = f"{self.base_url}{story_path}/{chapter_value}/"
            
            chapter_title = option.get_text(strip=True)
            if chapter_title:
                chapter_links.append({
                    'url': full_url,
                    'title': chapter_title
                })
        
        return chapter_links
    
    def get_story_info(self, story_url):
        """Extract story information from the story page"""
        # Auto-detect site adapter if not set
        if not self.site_adapter:
            self.site_adapter = SiteDetector.detect_site(story_url, self.session, self.delay, self.password)
            if not self.site_adapter:
                print(f"Error: Could not detect site for URL: {story_url}")
                print("Supported sites:")
                for site in SiteDetector.get_supported_sites():
                    print(f"  - {site['name']}: {', '.join(site['domains'])}")
                return None

        # Use site adapter to extract story info
        return self.site_adapter.get_story_info(story_url, self.get_page)

    def get_story_info_legacy(self, story_url):
        """Legacy method - Extract story information from the story page (TruyenFull only)"""
        html = self.get_page(story_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract story title
        title_elem = soup.find('h3', class_='title') or soup.find('h1', class_='title')
        if not title_elem:
            title_elem = soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Story"
        
        # Extract author
        author_elem = soup.find('a', href=re.compile(r'/tac-gia/'))
        author = author_elem.get_text(strip=True) if author_elem else "Unknown Author"
        
        # Extract description
        desc_elem = soup.find('div', class_='desc-text') or soup.find('div', id='book-description')
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Extract cover image URL
        cover_image_url = None
        # Try CSS selector: .info-holder > div.books > div > img
        info_holder = soup.find('div', class_='info-holder')
        if info_holder:
            books_div = info_holder.find('div', class_='books')
            if books_div:
                inner_div = books_div.find('div')
                if inner_div:
                    img = inner_div.find('img')
                    if img and img.get('src'):
                        cover_image_url = img.get('src')
                        # Make absolute URL if relative
                        if cover_image_url and not cover_image_url.startswith('http'):
                            cover_image_url = urljoin(self.base_url, cover_image_url)
        
        # Try alternative selectors if first method didn't work
        if not cover_image_url:
            # Look for common book cover image patterns
            img = soup.find('img', class_=re.compile(r'book|cover|image', re.I))
            if not img:
                img = soup.find('img', id=re.compile(r'book|cover', re.I))
            if img and img.get('src'):
                cover_image_url = img.get('src')
                if cover_image_url and not cover_image_url.startswith('http'):
                    cover_image_url = urljoin(self.base_url, cover_image_url)
        
        # Try to get chapters from AJAX endpoint (most reliable method)
        truyen_id = self.get_truyen_id(soup)
        all_chapter_links = []
        
        if truyen_id:
            print(f"Found truyen-id: {truyen_id}. Fetching chapters from AJAX endpoint...")
            ajax_chapters = self.get_chapters_from_ajax(truyen_id, story_url)
            if ajax_chapters:
                print(f"Found {len(ajax_chapters)} chapters from AJAX endpoint")
                all_chapter_links = ajax_chapters
            else:
                print("AJAX endpoint returned no chapters, trying pagination method...")
                # Fallback to pagination
                all_chapter_links = self.get_chapters_from_page(soup, self.base_url)
                pagination_links = self.find_pagination_links(soup, story_url)
                if pagination_links:
                    print(f"Found {len(pagination_links)} additional chapter pages. Fetching all chapters...")
                    for page_url in pagination_links:
                        page_html = self.get_page(page_url)
                        if page_html:
                            page_soup = BeautifulSoup(page_html, 'html.parser')
                            page_chapters = self.get_chapters_from_page(page_soup, self.base_url)
                            existing_urls = {ch['url'] for ch in all_chapter_links}
                            for chapter in page_chapters:
                                if chapter['url'] not in existing_urls:
                                    all_chapter_links.append(chapter)
                                    existing_urls.add(chapter['url'])
        else:
            # Fallback to pagination if truyen-id not found
            print("truyen-id not found, using pagination method...")
            all_chapter_links = self.get_chapters_from_page(soup, self.base_url)
            pagination_links = self.find_pagination_links(soup, story_url)
            if pagination_links:
                print(f"Found {len(pagination_links)} additional chapter pages. Fetching all chapters...")
                for page_url in pagination_links:
                    page_html = self.get_page(page_url)
                    if page_html:
                        page_soup = BeautifulSoup(page_html, 'html.parser')
                        page_chapters = self.get_chapters_from_page(page_soup, self.base_url)
                        existing_urls = {ch['url'] for ch in all_chapter_links}
                        for chapter in page_chapters:
                            if chapter['url'] not in existing_urls:
                                all_chapter_links.append(chapter)
                                existing_urls.add(chapter['url'])
        
        # Sort chapters by URL to maintain order
        def chapter_sort_key(ch):
            match = re.search(r'/chuong-(\d+)|/chapter-(\d+)', ch['url'], re.I)
            if match:
                return int(match.group(1) or match.group(2))
            return 0
        
        all_chapter_links.sort(key=chapter_sort_key)
        
        # If truyen_id not found, generate a fallback ID from story URL
        if not truyen_id:
            # Use a hash of the story URL as fallback ID
            import hashlib
            truyen_id = hashlib.md5(story_url.encode()).hexdigest()[:8]
            print(f"Warning: truyen-id not found, using fallback ID: {truyen_id}")
        
        return {
            'title': title,
            'author': author,
            'description': description,
            'chapters': all_chapter_links,
            'cover_image_url': cover_image_url,
            'truyen_id': truyen_id
        }
    
    def get_chapter_content(self, chapter_url):
        """Extract chapter content"""
        # Auto-detect site adapter if not set
        if not self.site_adapter:
            self.site_adapter = SiteDetector.detect_site(chapter_url, self.session, self.delay, self.password)

        # Use site adapter if available
        if self.site_adapter:
            return self.site_adapter.get_chapter_content(chapter_url, self.get_page)

        # Fallback to legacy method
        return self.get_chapter_content_legacy(chapter_url)

    def get_chapter_content_legacy(self, chapter_url):
        """Legacy method - Extract chapter content (TruyenFull only)"""
        html = self.get_page(chapter_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        
        # Find chapter title
        title_elem = soup.find('a', class_='chapter-title') or soup.find('h2', class_='chapter-title')
        if not title_elem:
            title_elem = soup.find('h1')
        chapter_title = title_elem.get_text(strip=True) if title_elem else "Unknown Chapter"
        
        # Find chapter content - try multiple selectors
        content_elem = None
        selectors = [
            ('div', {'id': 'chapter-content'}),
            ('div', {'class': 'chapter-content'}),
            ('div', {'class': 'chapter-c'}),
            ('div', {'class': 'chapter-text'}),
            ('div', {'id': 'chapter-text'}),
        ]
        
        for tag, attrs in selectors:
            content_elem = soup.find(tag, attrs)
            if content_elem:
                break
        
        # If still not found, try finding main content area
        if not content_elem:
            # Look for div containing multiple paragraphs (likely content)
            main_content = soup.find('div', class_=re.compile(r'content|chapter|text', re.I))
            if main_content:
                content_elem = main_content
        
        if content_elem:
            # Remove unwanted elements
            for elem in content_elem.find_all(['script', 'style', 'nav', 'header', 'footer']):
                elem.decompose()

            # Remove ads and comments
            for elem in content_elem.find_all(['div', 'p', 'span'], class_=re.compile(r'ads|advertisement|comment|quang-cao', re.I)):
                elem.decompose()

            # Replace <br> tags with newlines to preserve line breaks
            for br in content_elem.find_all('br'):
                br.replace_with('\n')

            # Get text content
            paragraphs = content_elem.find_all('p')
            if paragraphs:
                # Process each paragraph and preserve internal line breaks
                para_texts = []
                for p in paragraphs:
                    # Replace <br> with newline in each paragraph
                    for br in p.find_all('br'):
                        br.replace_with('\n')
                    text = p.get_text(strip=False)
                    # Clean up excessive whitespace while preserving single line breaks
                    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
                    text = re.sub(r'\n[ \t]+', '\n', text)  # Remove spaces after newlines
                    text = re.sub(r'[ \t]+\n', '\n', text)  # Remove spaces before newlines
                    text = text.strip()
                    if text:
                        para_texts.append(text)
                content = '\n\n'.join(para_texts)
            else:
                # No <p> tags, get all text and preserve line breaks
                content = content_elem.get_text(separator='', strip=False)
                # Clean up excessive whitespace
                content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces/tabs to single space
                content = re.sub(r'\n[ \t]+', '\n', content)  # Remove spaces after newlines
                content = re.sub(r'[ \t]+\n', '\n', content)  # Remove spaces before newlines
                content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 newlines
                content = content.strip()
        else:
            content = "Content not found"
        
        return {
            'title': chapter_title,
            'content': content
        }
    
    def download_story(self, story_url, output_dir=None, start_chapter=1, end_chapter=None, is_downloading=None):
        """
        Download a complete story
        
        Args:
            story_url: URL of the story page or chapter page
            output_dir: Directory to save the story (default: current directory)
            start_chapter: Chapter number to start from (1-indexed)
            end_chapter: Chapter number to end at (None for all)
            is_downloading: Optional callable that returns True if download should continue
        """
        # Auto-detect site adapter if not set
        if not self.site_adapter:
            self.site_adapter = SiteDetector.detect_site(story_url, self.session, self.delay)
            if not self.site_adapter:
                print(f"Error: URL is not from a supported site")
                print(f"Received URL: {story_url}")
                print("\nSupported sites:")
                for site in SiteDetector.get_supported_sites():
                    print(f"  - {site['name']}: {', '.join(site['domains'])}")
                return False

        print(f"Using {self.site_adapter.site_name} adapter")

        # Normalize URL - convert chapter URL to story URL if needed
        normalized_url, was_chapter = self.normalize_url(story_url)
        
        if was_chapter:
            print(f"Detected chapter URL. Extracting story from: {normalized_url}")
        else:
            print(f"Fetching story information from {normalized_url}...")
        
        story_info = self.get_story_info(normalized_url)
        
        if not story_info:
            print("Failed to fetch story information")
            return False
        
        print(f"Found: {story_info['title']}")
        print(f"Author: {story_info['author']}")
        print(f"Total chapters: {len(story_info['chapters'])}")
        
        if not story_info['chapters']:
            print("No chapters found. The story might be empty or the page structure is different.")
            return False
        
        # Set output directory - use story ID for directory name
        # Root directory for EPUB files
        if not output_dir:
            # Use default directory
            root_dir = get_default_download_dir()
        else:
            # Expand user path (handle ~)
            root_dir = os.path.expanduser(output_dir)
        
        # Story-specific directory using truyen_id (for txt and json files)
        truyen_id = story_info.get('truyen_id')
        if not truyen_id:
            # Fallback: use hash of story URL
            import hashlib
            truyen_id = hashlib.md5(normalized_url.encode()).hexdigest()[:8]
            story_info['truyen_id'] = truyen_id  # Store it for later use
        
        story_dir = os.path.join(root_dir, truyen_id)
        os.makedirs(story_dir, exist_ok=True)
        os.makedirs(root_dir, exist_ok=True)  # Ensure root exists for EPUB
        
        # Determine chapter range
        total_chapters = len(story_info['chapters'])
        start_idx = max(0, start_chapter - 1)
        end_idx = end_chapter if end_chapter else total_chapters
        end_idx = min(end_idx, total_chapters)
        
        chapters_to_download = story_info['chapters'][start_idx:end_idx]
        
        print(f"\nDownloading chapters {start_chapter} to {end_idx}...")
        
        # Download each chapter
        all_chapters = []
        skipped_count = 0
        for idx, chapter_info in enumerate(chapters_to_download, start=start_chapter):
            chapter_filename = f"chapter_{idx:04d}.txt"
            chapter_path = os.path.join(story_dir, chapter_filename)
            
            # Check if chapter file already exists
            if os.path.exists(chapter_path):
                print(f"Skipping chapter {idx}/{end_idx} (file exists): {chapter_info['title']}")
                # Read existing chapter from file
                try:
                    with open(chapter_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # Parse the file: first line is title, rest is content
                    lines = content.split('\n', 1)
                    if len(lines) >= 2:
                        chapter_title = lines[0].strip()
                        chapter_content = lines[1].strip()
                    else:
                        # Fallback: use title from chapter_info
                        chapter_title = chapter_info['title']
                        chapter_content = content.strip()
                    
                    chapter_data = {
                        'title': chapter_title,
                        'content': chapter_content
                    }
                    all_chapters.append(chapter_data)
                    skipped_count += 1
                except Exception as e:
                    print(f"  Warning: Could not read existing file, re-downloading: {e}")
                    # Fall through to download
                    chapter_data = self.get_chapter_content(chapter_info['url'])
                    if chapter_data:
                        all_chapters.append(chapter_data)
                        with open(chapter_path, 'w', encoding='utf-8') as f:
                            f.write(f"{chapter_data['title']}\n\n")
                            f.write(chapter_data['content'])
            else:
                # File doesn't exist, download it
                # Check if download should continue
                if is_downloading and not is_downloading():
                    print(f"\nDownload stopped by user")
                    break
                
                print(f"Downloading chapter {idx}/{end_idx}: {chapter_info['title']}")
                chapter_data = self.get_chapter_content(chapter_info['url'])
                
                if chapter_data:
                    all_chapters.append(chapter_data)
                    
                    # Save individual chapter
                    with open(chapter_path, 'w', encoding='utf-8') as f:
                        f.write(f"{chapter_data['title']}\n\n")
                        f.write(chapter_data['content'])
                
                # Check again after download
                if is_downloading and not is_downloading():
                    print(f"\nDownload stopped by user")
                    break
        
        if skipped_count > 0:
            print(f"\nSkipped {skipped_count} existing chapter(s)")
        
        # Save complete story
        complete_path = os.path.join(story_dir, "complete_story.txt")
        with open(complete_path, 'w', encoding='utf-8') as f:
            f.write(f"{story_info['title']}\n")
            f.write(f"Tác giả: {story_info['author']}\n")
            f.write("=" * 80 + "\n\n")
            if story_info['description']:
                f.write(f"{story_info['description']}\n\n")
                f.write("=" * 80 + "\n\n")
            
            for chapter in all_chapters:
                f.write(f"\n\n{chapter['title']}\n")
                f.write("-" * 80 + "\n\n")
                f.write(chapter['content'])
                f.write("\n\n")
        
        # Save metadata
        metadata_path = os.path.join(story_dir, "metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump({
                'title': story_info['title'],
                'author': story_info['author'],
                'description': story_info['description'],
                'url': story_url,
                'total_chapters': len(all_chapters),
                'downloaded_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)
        
        # Generate EPUB file (save to root directory)
        if EPUB_AVAILABLE:
            print("\nGenerating EPUB file...")
            # Create safe filename from story title for EPUB
            safe_title = re.sub(r'[^\w\s-]', '', story_info['title']).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            epub_path = self.create_epub(story_info, all_chapters, root_dir, epub_filename_base=safe_title)
            if epub_path:
                print(f"  EPUB created: {epub_path}")
        else:
            print("\n⚠ EPUB generation skipped (ebooklib not installed)")
            print("  Install with: pip install ebooklib")
        
        downloaded_count = len(all_chapters) - skipped_count
        print(f"\n✓ Download complete!")
        print(f"  Story files saved to: {os.path.abspath(story_dir)}")
        print(f"  EPUB saved to: {os.path.abspath(root_dir)}")
        print(f"  Total chapters: {len(all_chapters)} (downloaded: {downloaded_count}, skipped: {skipped_count})")
        
        return True
    
    def download_image(self, image_url, output_path):
        """Download an image file"""
        try:
            time.sleep(self.delay)  # Be respectful
            response = self.session.get(image_url, timeout=10, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            print(f"  Warning: Could not download cover image: {e}")
            return False
    
    def create_epub(self, story_info, chapters, output_dir, epub_filename_base=None):
        """Create an EPUB file with table of contents
        
        Args:
            story_info: Story metadata
            chapters: List of chapter data
            output_dir: Directory to save EPUB (root directory)
            epub_filename_base: Base filename for EPUB (default: story title)
        """
        try:
            # Create EPUB book
            book = epub.EpubBook()
            
            # Set metadata
            book.set_identifier(f"truyenfull_{story_info['title']}_{int(time.time())}")
            book.set_title(story_info['title'])
            book.set_language('vi')
            
            if story_info['author'] and story_info['author'] != "Unknown Author":
                book.add_author(story_info['author'])
            else:
                book.add_author("TruyenFull")
            
            if story_info['description']:
                book.add_metadata('DC', 'description', story_info['description'])
            
            # Download and add cover image (save to story directory)
            cover_image_path = None
            if story_info.get('cover_image_url'):
                print("  Downloading cover image...")
                cover_ext = os.path.splitext(story_info['cover_image_url'])[1] or '.jpg'
                if cover_ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                    cover_ext = '.jpg'
                # Save cover to story directory (where chapters are)
                story_dir = os.path.join(output_dir, story_info.get('truyen_id', 'unknown'))
                os.makedirs(story_dir, exist_ok=True)
                cover_image_path = os.path.join(story_dir, f"cover{cover_ext}")
                
                if self.download_image(story_info['cover_image_url'], cover_image_path):
                    if os.path.exists(cover_image_path):
                        # Read image and add to EPUB
                        with open(cover_image_path, 'rb') as f:
                            cover_image_data = f.read()
                        
                        # Determine MIME type
                        if cover_ext in ['.jpg', '.jpeg']:
                            mime_type = 'image/jpeg'
                        elif cover_ext == '.png':
                            mime_type = 'image/png'
                        elif cover_ext == '.gif':
                            mime_type = 'image/gif'
                        else:
                            mime_type = 'image/jpeg'
                        
                        # Add cover image to EPUB
                        # Note: set_cover() internally creates and adds the EpubItem,
                        # so we don't need to manually add it to avoid duplicates
                        book.set_cover(f"cover{cover_ext}", cover_image_data)
                        print("  Cover image added to EPUB")
            
            # Add cover page (optional)
            # Create CSS for styling
            style = '''
            @namespace epub "http://www.idpf.org/2007/ops";
            body {
                font-family: "Times New Roman", serif;
                line-height: 1.6;
                margin: 1em;
            }
            h1 {
                font-size: 2em;
                text-align: center;
                margin-bottom: 0.5em;
            }
            h2 {
                font-size: 1.5em;
                margin-top: 1.5em;
                margin-bottom: 0.5em;
                border-bottom: 1px solid #ccc;
                padding-bottom: 0.3em;
            }
            p {
                text-indent: 1.5em;
                margin: 0.5em 0;
            }
            '''
            
            nav_css = epub.EpubItem(
                uid="style_nav",
                file_name="style/nav.css",
                media_type="text/css",
                content=style
            )
            book.add_item(nav_css)
            
            # Create title page
            title_content = f'''<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{story_info['title']}</title>
    <link rel="stylesheet" type="text/css" href="style/nav.css"/>
</head>
<body>'''
            
            # Add cover image to title page if available
            if cover_image_path and os.path.exists(cover_image_path):
                cover_ext = os.path.splitext(cover_image_path)[1]
                title_content += f'''
    <div style="text-align: center; margin-bottom: 2em;">
        <img src="cover{cover_ext}" alt="Cover" style="max-width: 300px; max-height: 400px;"/>
    </div>'''
            
            title_content += f'''
    <h1>{story_info['title']}</h1>
    <p style="text-align: center; font-size: 1.2em; margin-top: 2em;">
        <strong>Tác giả:</strong> {story_info['author']}
    </p>'''
            
            if story_info['description']:
                # Clean description HTML
                desc = story_info['description'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                title_content += f'''
    <div style="margin-top: 2em; padding: 1em; border: 1px solid #ccc; border-radius: 5px;">
        <h2 style="border: none; margin-top: 0;">Giới thiệu</h2>
        <p style="text-indent: 0;">{desc}</p>
    </div>'''
            
            title_content += '''
</body>
</html>'''
            
            title_page = epub.EpubHtml(
                title='Giới thiệu',
                file_name='title.xhtml',
                lang='vi'
            )
            title_page.content = title_content
            title_page.add_item(nav_css)
            book.add_item(title_page)
            
            # Create chapters
            chapter_items = []
            toc_links = []
            
            for idx, chapter in enumerate(chapters, start=1):
                # Clean chapter title for filename
                safe_title = re.sub(r'[^\w\s-]', '', chapter['title']).strip()
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                if not safe_title:
                    safe_title = f"chapter-{idx}"
                
                # Format chapter content
                # Escape chapter title
                chapter_title_escaped = chapter['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                chapter_html = f'''<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{chapter_title_escaped}</title>
    <link rel="stylesheet" type="text/css" href="style/nav.css"/>
</head>
<body>
    <h1>{chapter_title_escaped}</h1>
    <div>
'''
                # Convert text content to paragraphs
                paragraphs = chapter['content'].split('\n\n')
                for para in paragraphs:
                    para = para.strip()
                    if para:
                        # Escape HTML
                        para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        chapter_html += f'        <p>{para}</p>\n'
                
                chapter_html += '''    </div>
</body>
</html>'''
                
                # Create chapter item
                chapter_file = epub.EpubHtml(
                    title=chapter['title'],
                    file_name=f'chapter_{idx:04d}.xhtml',
                    lang='vi'
                )
                chapter_file.content = chapter_html
                chapter_file.add_item(nav_css)
                book.add_item(chapter_file)
                chapter_items.append(chapter_file)
                toc_links.append(chapter_file)
            
            # Create table of contents - Title Page and chapters on same level
            book.toc = [epub.Link('title.xhtml', 'Giới thiệu', 'title')] + toc_links
            
            # Add navigation files
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            
            # Define spine (reading order)
            spine = ['nav', title_page] + chapter_items
            book.spine = spine
            
            # Save EPUB file to root directory
            if epub_filename_base:
                safe_story_title = epub_filename_base
            else:
                # Normalize filename - convert Vietnamese to ASCII
                import unicodedata

                # First normalize unicode to decomposed form (NFD)
                safe_story_title = unicodedata.normalize('NFD', story_info['title'])

                # Remove combining characters (accents/diacritics)
                safe_story_title = ''.join(
                    char for char in safe_story_title
                    if unicodedata.category(char) != 'Mn'
                )

                # Handle special Vietnamese characters that don't decompose properly
                vietnamese_map = {
                    'đ': 'd', 'Đ': 'D',
                    'ð': 'd', 'Ð': 'D',  # Alternative forms
                }
                for viet_char, ascii_char in vietnamese_map.items():
                    safe_story_title = safe_story_title.replace(viet_char, ascii_char)

                # Replace special dashes/hyphens with regular hyphen
                safe_story_title = safe_story_title.replace('–', '-').replace('—', '-').replace('―', '-')

                # Remove characters that are invalid in filenames
                safe_story_title = re.sub(r'[<>:"/\\|?*\[\]\(\)\{\}]', '', safe_story_title)

                # Remove other problematic punctuation
                safe_story_title = re.sub(r'[.,!?;:\'""`~@#$%^&*+=]', '', safe_story_title)

                # Replace multiple spaces/hyphens with single hyphen
                safe_story_title = re.sub(r'[-\s]+', '-', safe_story_title)

                # Remove leading/trailing hyphens and spaces
                safe_story_title = safe_story_title.strip('-').strip()

                # Limit filename length to avoid filesystem issues
                if len(safe_story_title) > 200:
                    safe_story_title = safe_story_title[:200].strip('-')
            epub_filename = f"{safe_story_title}.epub"
            epub_path = os.path.join(output_dir, epub_filename)
            
            epub.write_epub(epub_path, book, {})
            
            return epub_path
            
        except Exception as e:
            print(f"  Error creating EPUB: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    parser = argparse.ArgumentParser(
        description='Download stories from truyenfull.vn',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python truyenfull_downloader.py https://truyenfull.vn/ten-truyen/
  python truyenfull_downloader.py https://truyenfull.vn/ten-truyen/ -o my_story
  python truyenfull_downloader.py https://truyenfull.vn/ten-truyen/ --start 10 --end 20
        """
    )
    
    parser.add_argument('url', help='URL of the story page on truyenfull.vn')
    parser.add_argument('-o', '--output', help='Output directory (default: story title)')
    parser.add_argument('--start', type=int, default=1, help='Start chapter number (default: 1)')
    parser.add_argument('--end', type=int, help='End chapter number (default: all)')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests in seconds (minimum: 2.0, default: 2.0)')
    
    args = parser.parse_args()
    
    downloader = TruyenFullDownloader(delay=args.delay)
    success = downloader.download_story(
        args.url,
        output_dir=args.output,
        start_chapter=args.start,
        end_chapter=args.end
    )
    
    exit(0 if success else 1)


if __name__ == '__main__':
    main()

