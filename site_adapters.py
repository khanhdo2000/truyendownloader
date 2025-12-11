#!/usr/bin/env python3
"""
Site Adapters for Multi-Site Novel Downloader
Defines the interface and implementations for different novel websites
"""

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse


class SiteAdapter(ABC):
    """Base class for site-specific adapters"""

    def __init__(self, session, delay=2.0):
        """
        Initialize adapter

        Args:
            session: requests.Session object
            delay: Delay between requests in seconds
        """
        self.session = session
        self.delay = delay

    @property
    @abstractmethod
    def site_name(self):
        """Return the name of the site"""
        pass

    @property
    @abstractmethod
    def supported_domains(self):
        """Return list of supported domain patterns"""
        pass

    @abstractmethod
    def normalize_url(self, url):
        """
        Normalize URL and extract story main page if chapter URL is provided

        Returns:
            tuple: (story_url, is_chapter_url)
        """
        pass

    @abstractmethod
    def get_story_info(self, story_url, get_page_func):
        """
        Extract story information from the story page

        Args:
            story_url: URL of the story page
            get_page_func: Function to fetch page content

        Returns:
            dict: Story information including title, author, description, chapters, cover_image_url, truyen_id
        """
        pass

    @abstractmethod
    def get_chapter_content(self, chapter_url, get_page_func):
        """
        Extract chapter content

        Args:
            chapter_url: URL of the chapter page
            get_page_func: Function to fetch page content

        Returns:
            dict: Chapter data with 'title' and 'content'
        """
        pass

    def supports_url(self, url):
        """Check if this adapter supports the given URL"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return any(pattern in domain for pattern in self.supported_domains)


class TruyenFullAdapter(SiteAdapter):
    """Adapter for truyenfull.vision"""

    @property
    def site_name(self):
        return "TruyenFull"

    @property
    def supported_domains(self):
        return ['truyenfull.vision', 'truyenfull.vn']

    def normalize_url(self, url):
        """Normalize URL and extract story main page if chapter URL is provided"""
        parsed = urlparse(url)

        # Check if it's a chapter URL
        if '/chuong-' in url or '/chapter-' in url:
            # Extract story main page URL by removing chapter part
            path_parts = parsed.path.strip('/').split('/')

            # Remove chapter part (last part if it starts with 'chuong-' or 'chapter-')
            if path_parts and ('chuong-' in path_parts[-1] or 'chapter-' in path_parts[-1]):
                story_path = '/'.join(path_parts[:-1])
                story_url = f"{parsed.scheme}://{parsed.netloc}/{story_path}/"
                return story_url, True

        return url, False

    def get_story_info(self, story_url, get_page_func):
        """Extract story information from the story page"""
        html = get_page_func(story_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        base_url = f"{urlparse(story_url).scheme}://{urlparse(story_url).netloc}"

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
        cover_image_url = self._extract_cover_image(soup, base_url)

        # Get chapters
        truyen_id = self._get_truyen_id(soup)
        all_chapter_links = []

        if truyen_id:
            print(f"Found truyen-id: {truyen_id}. Fetching chapters from AJAX endpoint...")
            ajax_chapters = self._get_chapters_from_ajax(truyen_id, story_url, base_url, get_page_func)
            if ajax_chapters:
                print(f"Found {len(ajax_chapters)} chapters from AJAX endpoint")
                all_chapter_links = ajax_chapters
            else:
                print("AJAX endpoint returned no chapters, trying pagination method...")
                all_chapter_links = self._get_chapters_pagination(soup, story_url, base_url, get_page_func)
        else:
            print("truyen-id not found, using pagination method...")
            all_chapter_links = self._get_chapters_pagination(soup, story_url, base_url, get_page_func)

        # Sort chapters by URL to maintain order
        all_chapter_links.sort(key=lambda ch: self._extract_chapter_number(ch['url']))

        # Generate fallback ID if needed
        if not truyen_id:
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

    def get_chapter_content(self, chapter_url, get_page_func):
        """Extract chapter content"""
        html = get_page_func(chapter_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Find chapter title
        title_elem = soup.find('a', class_='chapter-title') or soup.find('h2', class_='chapter-title')
        if not title_elem:
            title_elem = soup.find('h1')
        chapter_title = title_elem.get_text(strip=True) if title_elem else "Unknown Chapter"

        # Find chapter content
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

        if not content_elem:
            main_content = soup.find('div', class_=re.compile(r'content|chapter|text', re.I))
            if main_content:
                content_elem = main_content

        if content_elem:
            # Remove unwanted elements
            for elem in content_elem.find_all(['script', 'style', 'nav', 'header', 'footer']):
                elem.decompose()

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

    def _extract_cover_image(self, soup, base_url):
        """Extract cover image URL"""
        cover_image_url = None
        info_holder = soup.find('div', class_='info-holder')
        if info_holder:
            books_div = info_holder.find('div', class_='books')
            if books_div:
                inner_div = books_div.find('div')
                if inner_div:
                    img = inner_div.find('img')
                    if img and img.get('src'):
                        cover_image_url = img.get('src')
                        if cover_image_url and not cover_image_url.startswith('http'):
                            cover_image_url = urljoin(base_url, cover_image_url)

        if not cover_image_url:
            img = soup.find('img', class_=re.compile(r'book|cover|image', re.I))
            if not img:
                img = soup.find('img', id=re.compile(r'book|cover', re.I))
            if img and img.get('src'):
                cover_image_url = img.get('src')
                if cover_image_url and not cover_image_url.startswith('http'):
                    cover_image_url = urljoin(base_url, cover_image_url)

        return cover_image_url

    def _get_truyen_id(self, soup):
        """Extract truyen-id from hidden input field"""
        truyen_id_input = soup.find('input', {'id': 'truyen-id'})
        if truyen_id_input:
            truyen_id = truyen_id_input.get('value', '')
            if truyen_id:
                return truyen_id
        return None

    def _get_chapters_from_ajax(self, truyen_id, story_url, base_url, get_page_func):
        """Fetch all chapters from AJAX endpoint"""
        ajax_url = f"{base_url}/ajax.php?type=chapter_option&data={truyen_id}"
        html = get_page_func(ajax_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        chapter_links = []
        options = soup.find_all('option', value=True)

        parsed = urlparse(story_url)
        story_path = parsed.path.rstrip('/')

        for option in options:
            chapter_value = option.get('value', '').strip()
            if not chapter_value or chapter_value in ['', '0']:
                continue

            if chapter_value.startswith('/'):
                full_url = urljoin(base_url, chapter_value)
            else:
                full_url = f"{base_url}{story_path}/{chapter_value}/"

            chapter_title = option.get_text(strip=True)
            if chapter_title:
                chapter_links.append({
                    'url': full_url,
                    'title': chapter_title
                })

        return chapter_links

    def _get_chapters_pagination(self, soup, story_url, base_url, get_page_func):
        """Get chapters using pagination method"""
        all_chapter_links = self._get_chapters_from_page(soup, base_url)
        pagination_links = self._find_pagination_links(soup, story_url, base_url)

        if pagination_links:
            print(f"Found {len(pagination_links)} additional chapter pages. Fetching all chapters...")
            for page_url in pagination_links:
                page_html = get_page_func(page_url)
                if page_html:
                    page_soup = BeautifulSoup(page_html, 'html.parser')
                    page_chapters = self._get_chapters_from_page(page_soup, base_url)
                    existing_urls = {ch['url'] for ch in all_chapter_links}
                    for chapter in page_chapters:
                        if chapter['url'] not in existing_urls:
                            all_chapter_links.append(chapter)
                            existing_urls.add(chapter['url'])

        return all_chapter_links

    def _get_chapters_from_page(self, soup, base_url):
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

        if not chapter_links:
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

    def _find_pagination_links(self, soup, story_url, base_url):
        """Find pagination links for chapter pages"""
        pagination_links = []
        pagination = soup.find('div', class_=re.compile(r'pagination|phan-trang', re.I))
        if not pagination:
            pagination = soup.find('nav', class_=re.compile(r'pagination', re.I))
        if not pagination:
            pagination = soup.find('ul', class_=re.compile(r'pagination', re.I))

        if pagination:
            links = pagination.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if re.search(r'/trang-\d+|/page-\d+|/p/\d+', href, re.I):
                    full_url = urljoin(base_url, href)
                    if full_url not in pagination_links:
                        pagination_links.append(full_url)

        next_links = soup.find_all('a', href=True, string=re.compile(r'next|sau|tiếp', re.I))
        for link in next_links:
            href = link.get('href', '')
            if '/trang-' in href or '/page-' in href:
                full_url = urljoin(base_url, href)
                if full_url not in pagination_links:
                    pagination_links.append(full_url)

        pagination_links.sort(key=lambda url: self._extract_page_number(url))
        return pagination_links

    def _extract_page_number(self, url):
        """Extract page number from URL"""
        match = re.search(r'/trang-(\d+)|/page-(\d+)', url, re.I)
        return int(match.group(1) or match.group(2)) if match else 0

    def _extract_chapter_number(self, url):
        """Extract chapter number from URL"""
        match = re.search(r'/chuong-(\d+)|/chapter-(\d+)', url, re.I)
        return int(match.group(1) or match.group(2)) if match else 0


class TangThuVienAdapter(SiteAdapter):
    """Adapter for truyen.tangthuvien.vn"""

    @property
    def site_name(self):
        return "TangThuVien"

    @property
    def supported_domains(self):
        return ['tangthuvien.vn', 'truyen.tangthuvien.vn']

    def normalize_url(self, url):
        """Normalize URL and extract story main page if chapter URL is provided"""
        parsed = urlparse(url)

        # TangThuVien chapter URLs: /doc-truyen/ten-truyen/chuong-X
        if '/chuong-' in url.lower():
            path_parts = parsed.path.strip('/').split('/')
            # Remove chapter part
            if path_parts and 'chuong-' in path_parts[-1].lower():
                story_path = '/'.join(path_parts[:-1])
                story_url = f"{parsed.scheme}://{parsed.netloc}/{story_path}"
                return story_url, True

        return url, False

    def get_story_info(self, story_url, get_page_func):
        """Extract story information from TangThuVien"""
        html = get_page_func(story_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        base_url = f"{urlparse(story_url).scheme}://{urlparse(story_url).netloc}"

        # Extract title - TangThuVien uses h1 or h3.title
        title_elem = soup.find('h1') or soup.find('h3', class_='title') or soup.find('div', class_='book-title')
        if not title_elem:
            title_elem = soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Story"
        # Clean up title
        if ' - ' in title:
            title = title.split(' - ')[0].strip()

        # Extract author using CSS selector
        author = "Unknown Author"
        try:
            # Try the specific CSS selector first: #authorId > p > a
            author_elem = soup.select_one('#authorId > p > a')
            if author_elem:
                author = author_elem.get_text(strip=True)
            else:
                # Fallback to alternative selectors
                author_elem = soup.find('a', itemprop='author') or soup.find('span', itemprop='author')
                if not author_elem:
                    author_elem = soup.find('a', href=re.compile(r'/tac-gia/|/author/'))
                if author_elem:
                    author = author_elem.get_text(strip=True)
        except Exception as e:
            print(f"Warning: Error extracting author with CSS selector: {e}")
            # Fallback
            author_elem = soup.find('a', itemprop='author') or soup.find('span', itemprop='author')
            if not author_elem:
                author_elem = soup.find('a', href=re.compile(r'/tac-gia/|/author/'))
            if author_elem:
                author = author_elem.get_text(strip=True)

        # Extract description
        desc_elem = soup.find('div', class_='book-intro') or soup.find('div', itemprop='description')
        if not desc_elem:
            desc_elem = soup.find('div', class_='content-desc')
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Extract cover image
        cover_image_url = None
        img = soup.find('img', class_='book-cover') or soup.find('img', itemprop='image')
        if not img:
            img = soup.find('div', class_='book-img')
            if img:
                img = img.find('img')
        if img and img.get('src'):
            cover_image_url = img.get('src')
            if cover_image_url and not cover_image_url.startswith('http'):
                cover_image_url = urljoin(base_url, cover_image_url)

        # Get chapters - TangThuVien usually has chapter list
        chapter_links = []

        # Try to find chapter list container
        chapter_list = soup.find('ul', class_='list-chapter') or soup.find('div', class_='list-chapter')
        if not chapter_list:
            chapter_list = soup.find('ul', id='list-chapter') or soup.find('div', id='list-chapter')

        if chapter_list:
            links = chapter_list.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if '/chuong-' in href.lower() or '/chapter' in href.lower():
                    full_url = urljoin(base_url, href)
                    chapter_title = link.get_text(strip=True)
                    if full_url not in [ch['url'] for ch in chapter_links]:
                        chapter_links.append({
                            'url': full_url,
                            'title': chapter_title
                        })

        # If no chapters found, try alternative methods
        if not chapter_links:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if '/chuong-' in href.lower():
                    full_url = urljoin(base_url, href)
                    chapter_title = link.get_text(strip=True)
                    if chapter_title and full_url not in [ch['url'] for ch in chapter_links]:
                        chapter_links.append({
                            'url': full_url,
                            'title': chapter_title
                        })

        # Sort chapters
        chapter_links.sort(key=lambda ch: self._extract_chapter_number(ch['url']))

        # Generate truyen_id
        import hashlib
        truyen_id = hashlib.md5(story_url.encode()).hexdigest()[:8]

        return {
            'title': title,
            'author': author,
            'description': description,
            'chapters': chapter_links,
            'cover_image_url': cover_image_url,
            'truyen_id': truyen_id
        }

    def get_chapter_content(self, chapter_url, get_page_func):
        """Extract chapter content from TangThuVien"""
        html = get_page_func(chapter_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Find chapter title
        title_elem = soup.find('h2') or soup.find('h1', class_='chapter-title')
        if not title_elem:
            title_elem = soup.find('a', class_='chapter-title')
        chapter_title = title_elem.get_text(strip=True) if title_elem else "Unknown Chapter"

        # Find chapter content
        content_elem = soup.find('div', class_='box-chap') or soup.find('div', id='chapter-content')
        if not content_elem:
            content_elem = soup.find('div', class_='chapter-content')

        if content_elem:
            # Remove unwanted elements
            for elem in content_elem.find_all(['script', 'style', 'nav', 'header', 'footer', 'iframe']):
                elem.decompose()

            # Remove ads
            for elem in content_elem.find_all(['div', 'p'], class_=re.compile(r'ads|advertisement|banner', re.I)):
                elem.decompose()

            # TangThuVien uses <br> tags for line breaks - replace them with newlines
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

    def _extract_chapter_number(self, url):
        """Extract chapter number from URL"""
        match = re.search(r'/chuong-(\d+)|/chapter-(\d+)', url, re.I)
        return int(match.group(1) or match.group(2)) if match else 0


class LaoPhatGiaAdapter(SiteAdapter):
    """Adapter for laophatgia.net"""

    @property
    def site_name(self):
        return "LaoPhatGia"

    @property
    def supported_domains(self):
        return ['laophatgia.net', 'www.laophatgia.net']

    def normalize_url(self, url):
        """Normalize URL and extract story main page if chapter URL is provided"""
        parsed = urlparse(url)

        # LaoPhatGia chapter URLs: /truyen/ten-truyen/chuong-X.html or /manga/ten-truyen/chuong-X.html
        if '/chuong-' in url.lower() or '/chap-' in url.lower() or '/chapter-' in url.lower():
            path_parts = parsed.path.strip('/').split('/')
            # Remove chapter part (usually the last part)
            if path_parts and ('chuong-' in path_parts[-1].lower() or 'chap-' in path_parts[-1].lower() or 'chapter-' in path_parts[-1].lower()):
                story_path = '/'.join(path_parts[:-1])
                story_url = f"{parsed.scheme}://{parsed.netloc}/{story_path}"
                return story_url, True

        return url, False

    def get_story_info(self, story_url, get_page_func):
        """Extract story information from LaoPhatGia"""
        html = get_page_func(story_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        base_url = f"{urlparse(story_url).scheme}://{urlparse(story_url).netloc}"

        # Extract title
        title_elem = soup.find('h1', class_='title') or soup.find('h1') or soup.find('h2', class_='title')
        if not title_elem:
            title_elem = soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Story"
        # Clean title
        if ' - ' in title:
            title = title.split(' - ')[0].strip()

        # Extract author using CSS selector
        author = "Unknown Author"
        try:
            # Navigate to the author element manually since nth-child() may not work well
            # Path: body > div.wrap > div > div.site-content > div > div.profile-manga.summary-layout-1 > 
            #       div > div > div > div.tab-summary > div.summary_content_wrap > div > div.post-content > 
            #       div:nth-child(5) > div.summary-content > div
            post_content = soup.select_one('div.summary_content_wrap div.post-content')
            if post_content:
                # Get all direct div children and take the 5th one (index 4)
                div_children = [child for child in post_content.children if hasattr(child, 'name') and child.name == 'div']
                if len(div_children) >= 5:
                    fifth_div = div_children[4]  # 0-indexed, so 5th element is index 4
                    summary_content = fifth_div.find('div', class_='summary-content')
                    if summary_content:
                        author_div = summary_content.find('div')
                        if author_div:
                            author = author_div.get_text(strip=True)
            
            # Fallback to alternative selectors if CSS selector doesn't work
            if author == "Unknown Author":
                author_elem = soup.find('a', href=re.compile(r'/tac-gia/|/author/'))
                if not author_elem:
                    # Try alternative selectors
                    info_div = soup.find('div', class_='info')
                    if info_div:
                        author_elem = info_div.find('a')
                if author_elem:
                    author = author_elem.get_text(strip=True)
        except Exception as e:
            print(f"Warning: Error extracting author with CSS selector: {e}")
            # Fallback
            author_elem = soup.find('a', href=re.compile(r'/tac-gia/|/author/'))
            if author_elem:
                author = author_elem.get_text(strip=True)

        # Extract description
        desc_elem = soup.find('div', class_='desc') or soup.find('div', class_='intro')
        if not desc_elem:
            desc_elem = soup.find('div', class_='content-intro')
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Extract cover image using CSS selector
        cover_image_url = None
        try:
            # Try the specific CSS selector first
            cover_selectors = [
                'body > div.wrap > div > div.site-content > div > div.profile-manga.summary-layout-1 > div > div > div > div.tab-summary > div.summary_image > a > img',
                'div.summary_image > a > img',
                'div.summary_image img',
                'div.profile-manga div.summary_image img',
            ]
            for selector in cover_selectors:
                img_elems = soup.select(selector)
                if img_elems:
                    img_elem = img_elems[0]
                    # Prioritize data-src for lazy-loaded images, then check src
                    # Filter out placeholder images like dflazy.jpg
                    cover_image_url = (img_elem.get('data-src') or 
                                      img_elem.get('data-lazy-src') or
                                      img_elem.get('data-original') or
                                      img_elem.get('src'))
                    
                    # Filter out placeholder images
                    if cover_image_url:
                        placeholder_patterns = ['dflazy.jpg', 'placeholder', 'loading', 'lazy']
                        if any(pattern in cover_image_url.lower() for pattern in placeholder_patterns):
                            cover_image_url = None
                    
                    if cover_image_url:
                        # Clean up the URL (remove query parameters that might cause issues)
                        if '?' in cover_image_url:
                            cover_image_url = cover_image_url.split('?')[0]
                        if cover_image_url and not cover_image_url.startswith('http'):
                            cover_image_url = urljoin(base_url, cover_image_url)
                        break
            
            # Fallback: Manual DOM navigation following the exact path
            if not cover_image_url:
                try:
                    # Navigate manually: div.profile-manga.summary-layout-1 > div > div > div > div.tab-summary > div.summary_image > a > img
                    profile_manga = soup.find('div', class_='profile-manga')
                    if profile_manga:
                        # Find tab-summary
                        tab_summary = profile_manga.find('div', class_='tab-summary')
                        if tab_summary:
                            summary_image = tab_summary.find('div', class_='summary_image')
                            if summary_image:
                                # Find the link and then the image
                                link = summary_image.find('a')
                                if link:
                                    img = link.find('img')
                                else:
                                    img = summary_image.find('img')
                                
                                if img:
                                    # Prioritize data-src for lazy-loaded images
                                    cover_image_url = (img.get('data-src') or 
                                                      img.get('data-lazy-src') or
                                                      img.get('data-original') or
                                                      img.get('src'))
                                    
                                    # Filter out placeholder images
                                    if cover_image_url:
                                        placeholder_patterns = ['dflazy.jpg', 'placeholder', 'loading', 'lazy']
                                        if any(pattern in cover_image_url.lower() for pattern in placeholder_patterns):
                                            cover_image_url = None
                                    
                                    if cover_image_url:
                                        if '?' in cover_image_url:
                                            cover_image_url = cover_image_url.split('?')[0]
                                        if cover_image_url and not cover_image_url.startswith('http'):
                                            cover_image_url = urljoin(base_url, cover_image_url)
                except Exception as e:
                    pass
            
            # Final fallback: Try finding by class or id
            if not cover_image_url:
                # Try finding by class or id
                img = soup.find('img', class_=re.compile(r'cover|summary|image', re.I))
                if not img:
                    img = soup.find('div', class_='book-img') or soup.find('div', class_='summary_image')
                    if img:
                        img = img.find('img')
                
                if img:
                    # Prioritize data-src for lazy-loaded images
                    cover_image_url = (img.get('data-src') or 
                                      img.get('data-lazy-src') or
                                      img.get('data-original') or
                                      img.get('src'))
                    
                    # Filter out placeholder images
                    if cover_image_url:
                        placeholder_patterns = ['dflazy.jpg', 'placeholder', 'loading', 'lazy']
                        if any(pattern in cover_image_url.lower() for pattern in placeholder_patterns):
                            cover_image_url = None
                    
                    if cover_image_url:
                        # Clean up the URL
                        if '?' in cover_image_url:
                            cover_image_url = cover_image_url.split('?')[0]
                        if cover_image_url and not cover_image_url.startswith('http'):
                            cover_image_url = urljoin(base_url, cover_image_url)
        except Exception as e:
            print(f"Warning: Error extracting cover image with CSS selector: {e}")
            # Fallback
            try:
                img = soup.find('img', class_=re.compile(r'cover|summary', re.I))
                if img:
                    # Prioritize data-src for lazy-loaded images
                    cover_image_url = (img.get('data-src') or 
                                      img.get('data-lazy-src') or
                                      img.get('data-original') or
                                      img.get('src'))
                    
                    # Filter out placeholder images
                    if cover_image_url:
                        placeholder_patterns = ['dflazy.jpg', 'placeholder', 'loading', 'lazy']
                        if any(pattern in cover_image_url.lower() for pattern in placeholder_patterns):
                            cover_image_url = None
                    
                    if cover_image_url and not cover_image_url.startswith('http'):
                        cover_image_url = urljoin(base_url, cover_image_url)
            except:
                pass

        # Get chapters
        chapter_links = []

        # LaoPhatGia uses: div.page-content-listing > div > ul > li > a
        # Try to find the chapter list container
        chapter_container = soup.find('div', class_='page-content-listing')
        if not chapter_container:
            chapter_container = soup.find('div', class_='list-chapter')

        if chapter_container:
            # Find all <li> items with chapter links
            list_items = chapter_container.find_all('li')
            for li in list_items:
                link = li.find('a', href=True)
                if link:
                    href = link.get('href', '')
                    # LaoPhatGia uses various patterns: /chuong-, /chap-, /chapter-
                    if any(pattern in href.lower() for pattern in ['/chuong-', '/chap-', '/chapter-']):
                        full_url = urljoin(base_url, href)
                        chapter_title = link.get_text(strip=True)
                        if full_url not in [ch['url'] for ch in chapter_links]:
                            chapter_links.append({
                                'url': full_url,
                                'title': chapter_title
                            })

        # If no chapters found, try alternative selectors
        if not chapter_links:
            selectors = [
                ('div', {'class': 'list-chapter'}),
                ('ul', {'class': 'list-chapter'}),
                ('div', {'id': 'list-chapter'}),
                ('div', {'class': 'chapter-list'}),
                ('ul', {'class': 'chapter-list'}),
                ('div', {'class': 'episodes'}),
                ('ul', {'class': 'episodes'}),
                ('div', {'id': 'chapters'}),
            ]

            for tag, attrs in selectors:
                chapter_list = soup.find(tag, attrs)
                if chapter_list:
                    links = chapter_list.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if any(pattern in href.lower() for pattern in ['/chuong-', '/chap-', '/chapter-']):
                            full_url = urljoin(base_url, href)
                            chapter_title = link.get_text(strip=True)
                            if full_url not in [ch['url'] for ch in chapter_links]:
                                chapter_links.append({
                                    'url': full_url,
                                    'title': chapter_title
                                })
                    if chapter_links:
                        break

        # If still no chapters found, try broader search
        if not chapter_links:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                # Look for chapter patterns anywhere in href
                if any(pattern in href.lower() for pattern in ['/chuong-', '/chap-', '/chapter-']):
                    full_url = urljoin(base_url, href)
                    chapter_title = link.get_text(strip=True)
                    if chapter_title and full_url not in [ch['url'] for ch in chapter_links]:
                        chapter_links.append({
                            'url': full_url,
                            'title': chapter_title
                        })

        # Sort chapters
        chapter_links.sort(key=lambda ch: self._extract_chapter_number(ch['url']))

        # Generate truyen_id
        import hashlib
        truyen_id = hashlib.md5(story_url.encode()).hexdigest()[:8]

        return {
            'title': title,
            'author': author,
            'description': description,
            'chapters': chapter_links,
            'cover_image_url': cover_image_url,
            'truyen_id': truyen_id
        }

    def get_chapter_content(self, chapter_url, get_page_func):
        """Extract chapter content from LaoPhatGia"""
        html = get_page_func(chapter_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Find chapter title
        title_elem = soup.find('h2', class_='chapter-title') or soup.find('h1')
        if not title_elem:
            title_elem = soup.find('a', class_='chapter-title')
        chapter_title = title_elem.get_text(strip=True) if title_elem else "Unknown Chapter"

        # Find chapter content - try multiple selectors
        content_elem = None
        content_selectors = [
            ('div', {'id': 'chapter-content'}),
            ('div', {'class': 'chapter-content'}),
            ('div', {'class': 'content'}),
            ('div', {'class': 'reading-content'}),
            ('div', {'class': 'chapter-c'}),
            ('article', {'class': 'chapter-content'}),
        ]

        for tag, attrs in content_selectors:
            content_elem = soup.find(tag, attrs)
            if content_elem:
                break

        # If still not found, try broader search
        if not content_elem:
            content_elem = soup.find('div', class_=re.compile(r'content|chapter', re.I))

        if content_elem:
            # Remove unwanted elements
            for elem in content_elem.find_all(['script', 'style', 'nav', 'header', 'footer', 'iframe']):
                elem.decompose()

            # Remove ads
            for elem in content_elem.find_all(['div', 'p'], class_=re.compile(r'ads|advertisement|banner|quang-cao', re.I)):
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

    def _extract_chapter_number(self, url):
        """Extract chapter number from URL"""
        # Try multiple patterns: /chuong-X, /chap-X, /chapter-X
        match = re.search(r'/chuong-(\d+)|/chap-(\d+)|/chapter-(\d+)', url, re.I)
        if match:
            return int(match.group(1) or match.group(2) or match.group(3))
        return 0


class WordPressAdapter(SiteAdapter):
    """Adapter for WordPress-based story sites"""

    @property
    def site_name(self):
        return "WordPress"

    @property
    def supported_domains(self):
        # Return common WordPress indicators for initial detection
        # The supports_url method will do more thorough checking
        return ['wordpress.com']

    def __init__(self, session, delay=2.0, password=None):
        super().__init__(session, delay)
        self.password = password

    def supports_url(self, url):
        """
        Check if this is a WordPress site by looking for WordPress-specific indicators
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Quick check: if it's a wordpress.com subdomain, it's definitely WordPress
        if 'wordpress.com' in domain:
            return True

        # For other domains, we need to check the page content
        # Look for WordPress-specific patterns
        try:
            if self.session:
                import time
                time.sleep(self.delay)
                response = self.session.get(url, timeout=10)
                html = response.text.lower()

                # Check for common WordPress indicators in the HTML
                wordpress_indicators = [
                    'wp-content',           # WordPress content directory
                    'wp-includes',          # WordPress includes directory
                    'wordpress',            # Direct WordPress mention
                    'wp-json',              # WordPress REST API
                    'class="entry-content"',  # Common WordPress theme class
                    'class="post-',         # WordPress post classes
                    '/wp-login.php',        # WordPress login page
                    'generator" content="wordpress',  # WordPress generator meta tag
                ]

                # If we find multiple indicators, it's likely WordPress
                found_count = sum(1 for indicator in wordpress_indicators if indicator in html)
                if found_count >= 2:
                    return True

        except Exception:
            # If we can't fetch the page, fall back to domain check
            pass

        # Fall back to basic domain check
        return any(pattern in domain for pattern in self.supported_domains)

    def normalize_url(self, url):
        """
        WordPress chapter URLs contain the full post URL
        Try to detect if this is a chapter URL and find the main story page
        """
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Check if this is a chapter URL (contains 'chuong', 'chapter', 'chap')
        is_chapter = any(word in path for word in ['chuong-', 'chapter-', 'chap-'])

        if is_chapter:
            # For WordPress, we need to find the main story page
            # This is usually a page that lists all chapters
            # We'll try to extract it from the URL or fetch it from the chapter page
            try:
                if self.session:
                    response = self._get_page(url)
                    soup = BeautifulSoup(response, 'html.parser')

                    # Look for a link to the main story page in the content
                    # Usually it's the first link or a link with "on-going" or story title
                    entry_content = soup.find('div', class_='entry-content')
                    if entry_content:
                        # Find all links in the content
                        links = entry_content.find_all('a', href=True)
                        for link in links:
                            href = link['href']
                            # Look for a link that seems like a main story page
                            if 'on-going' in href.lower() or 'hoan' in href.lower():
                                return href, True

                    # If we can't find the main page, return the chapter URL
                    return url, True
            except Exception as e:
                print(f"Warning: Could not fetch main story page: {e}")
                return url, True

        return url, False

    def get_story_info(self, story_url, get_page_func):
        """Extract story information and chapter list from WordPress page"""
        html = get_page_func(story_url)
        soup = BeautifulSoup(html, 'html.parser')

        # Extract title - usually in entry-title or post-title
        title = ''
        title_elem = soup.find('h1', class_='entry-title') or soup.find('h1', class_='post-title')
        if title_elem:
            title = title_elem.get_text(strip=True)
            # Remove [ON-GOING], [HOÀN], etc. from title
            title = re.sub(r'\s*[\[\(](ON-GOING|HOÀN|COMPLETE|Hoàn)[\]\)]', '', title, flags=re.I)

        if not title:
            title_elem = soup.find('title')
            if title_elem:
                title = title_elem.get_text(strip=True)

        # Extract author - look for common patterns
        author = 'Unknown'
        # Look for author in meta or content
        author_patterns = [
            soup.find('meta', {'name': 'author'}),
            soup.find('span', class_='author'),
            soup.find('a', rel='author')
        ]
        for pattern in author_patterns:
            if pattern:
                if pattern.name == 'meta':
                    author = pattern.get('content', 'Unknown')
                else:
                    author = pattern.get_text(strip=True)
                break

        # Also try to find author in the content
        if author == 'Unknown':
            entry_content = soup.find('div', class_='entry-content')
            if entry_content:
                # Look for common Vietnamese author labels
                text = entry_content.get_text()
                author_match = re.search(r'(Tác giả|Author|Nguyên tác):\s*([^\n]+)', text, re.I)
                if author_match:
                    author = author_match.group(2).strip()

        # Extract description
        description = ''
        entry_content = soup.find('div', class_='entry-content')
        if entry_content:
            # Get the first few paragraphs as description
            paragraphs = entry_content.find_all('p', limit=5)
            desc_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                # Skip if it's just navigation or links
                if text and len(text) > 20 and not text.startswith('Chương'):
                    desc_parts.append(text)
                    if len(' '.join(desc_parts)) > 200:
                        break
            description = '\n'.join(desc_parts)

        # Extract cover image - look for images with 'poster' in URL
        cover_image_url = None
        if entry_content:
            images = entry_content.find_all('img')
            for img in images:
                src = img.get('src', '') or img.get('data-src', '')
                if 'poster' in src.lower():
                    cover_image_url = src
                    break

            # If no poster found, use the first image that's not a GIF
            if not cover_image_url:
                for img in images:
                    src = img.get('src', '') or img.get('data-src', '')
                    if src and not src.lower().endswith('.gif'):
                        cover_image_url = src
                        break

        # Extract chapters - look for all links in the content
        chapters = []
        if entry_content:
            links = entry_content.find_all('a', href=True)
            for link in links:
                href = link['href']
                text = link.get_text(strip=True)

                # Check if this looks like a chapter link
                if any(word in href.lower() for word in ['chuong-', 'chapter-', 'chap-']):
                    # Extract chapter number from text or URL
                    chapter_num_match = re.search(r'(\d+)', text)
                    if chapter_num_match or 'chuong' in href.lower():
                        chapters.append({
                            'url': href,
                            'title': text or f"Chương {len(chapters) + 1}"
                        })

        # Generate truyen_id from URL
        truyen_id = re.sub(r'[^a-z0-9]+', '-', story_url.lower())
        truyen_id = truyen_id.strip('-')

        return {
            'title': title,
            'author': author,
            'description': description,
            'chapters': chapters,
            'cover_image_url': cover_image_url,
            'truyen_id': truyen_id
        }

    def get_chapter_content(self, chapter_url, get_page_func):
        """Extract chapter content from WordPress page"""
        html = get_page_func(chapter_url, password=self.password)
        soup = BeautifulSoup(html, 'html.parser')

        # Check if password protected
        if soup.find('form', class_='post-password-form'):
            if not self.password:
                raise ValueError(f"Chapter is password protected: {chapter_url}\nPlease provide a password.")
            # If we have a password, the get_page_func should handle it
            # If we're still seeing the form, the password is wrong
            raise ValueError(f"Incorrect password for chapter: {chapter_url}")

        # Extract title
        title = ''
        title_elem = soup.find('h1', class_='entry-title') or soup.find('h1', class_='post-title')
        if title_elem:
            full_title = title_elem.get_text(strip=True)
            # Remove story name prefix and privacy markers
            # Examples: "Ẩn Thần Tân Thê – Chương 10" -> "Chương 10"
            #           "Riêng Tư: Story Name – Chapter 1" -> "Chapter 1"

            # Remove "Riêng Tư:" prefix if present
            if full_title.startswith('Riêng Tư:'):
                full_title = full_title.replace('Riêng Tư:', '').strip()

            # Try to extract just the chapter part after "–" or "-"
            if '–' in full_title:
                title = full_title.split('–')[-1].strip()
            elif ' - ' in full_title:
                title = full_title.split(' - ')[-1].strip()
            else:
                title = full_title

        # Extract content
        content = ''
        entry_content = soup.find('div', class_='entry-content')

        if entry_content:
            # Remove unwanted elements
            for elem in entry_content.find_all(['script', 'style', 'nav', 'header', 'footer']):
                elem.decompose()

            # Remove sharing buttons and related posts
            for selector in ['.sharedaddy', '.jetpack-related-posts', '#comments',
                           '.navigation', '.nav-links', '.post-navigation']:
                for elem in entry_content.select(selector):
                    elem.decompose()

            # Remove GIF images
            for img in entry_content.find_all('img'):
                src = img.get('src', '') or img.get('data-src', '')
                if src.lower().endswith('.gif'):
                    img.decompose()

            # Extract text content while preserving line breaks
            # First, handle line breaks by replacing <br> tags with newlines
            for br in entry_content.find_all('br'):
                br.replace_with('\n')

            # Get text from paragraphs, preserving structure
            paragraphs = []
            for elem in entry_content.find_all(['p', 'div'], recursive=False):
                # Get text but preserve internal newlines from <br> tags
                text = elem.get_text(separator='\n', strip=False)

                # Skip navigation text
                if text and not any(skip in text.lower() for skip in ['← ', 'chương trước', 'chương sau', 'navigation']):
                    # Clean up but preserve line breaks
                    # Remove excessive spaces on each line
                    lines = text.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        cleaned_line = ' '.join(line.split())  # Normalize spaces within line
                        if cleaned_line:  # Only keep non-empty lines
                            cleaned_lines.append(cleaned_line)
                    if cleaned_lines:
                        paragraphs.append('\n'.join(cleaned_lines))

            content = '\n\n'.join(paragraphs)  # Separate paragraphs with double newline

            # Final cleanup - limit excessive newlines to maximum 2
            content = re.sub(r'\n{3,}', '\n\n', content)
            content = content.strip()

        return {
            'title': title,
            'content': content
        }

    def _extract_chapter_number(self, url):
        """Extract chapter number from URL"""
        match = re.search(r'/chuong-(\d+)|/chap-(\d+)|/chapter-(\d+)', url, re.I)
        if match:
            return int(match.group(1) or match.group(2) or match.group(3))
        return 0


class SiteDetector:
    """Detect and return appropriate site adapter for a URL"""

    # Registry of all available adapters
    ADAPTERS = [
        TruyenFullAdapter,
        TangThuVienAdapter,
        LaoPhatGiaAdapter,
        WordPressAdapter,
    ]

    @classmethod
    def detect_site(cls, url, session, delay=2.0, password=None):
        """
        Detect which site adapter to use based on URL

        Args:
            url: URL to check
            session: requests.Session object
            delay: Delay between requests
            password: Optional password for password-protected content

        Returns:
            SiteAdapter instance or None if no adapter found
        """
        for adapter_class in cls.ADAPTERS:
            # Pass password to WordPress adapter
            if adapter_class.__name__ == 'WordPressAdapter' and password:
                adapter = adapter_class(session, delay, password=password)
            else:
                adapter = adapter_class(session, delay)
            if adapter.supports_url(url):
                print(f"Detected site: {adapter.site_name}")
                return adapter

        return None

    @classmethod
    def get_supported_sites(cls):
        """Get list of all supported sites"""
        sites = []
        for adapter_class in cls.ADAPTERS:
            adapter = adapter_class(None, 2.0)
            sites.append({
                'name': adapter.site_name,
                'domains': adapter.supported_domains
            })
        return sites
