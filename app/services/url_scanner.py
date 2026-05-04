"""
URL 扫描器模块

此模块提供扫描/爬取单个 URL 的功能，
从网页中提取内容、链接和元数据。
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Set, Any
from urllib.parse import urljoin, urlparse
import re
import logging

logger = logging.getLogger(__name__)


class ScanResult:
    """表示 URL 扫描结果。"""

    def __init__(self, url: str):
        self.url = url
        self.status_code: Optional[int] = None
        self.content_type: Optional[str] = None
        self.title: Optional[str] = None
        self.meta_description: Optional[str] = None
        self.meta_keywords: Optional[str] = None
        self.headings: Dict[str, List[str]] = {}
        self.links: Dict[str, List[str]] = {
            'internal': [],
            'external': [],
            'images': [],
            'scripts': [],
            'stylesheets': [],
        }
        self.word_count: int = 0
        self.load_time: float = 0.0
        self.error: Optional[str] = None
        self.html_content: Optional[str] = None
        self.text_content: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """将扫描结果转换为字典。"""
        return {
            'url': self.url,
            'status_code': self.status_code,
            'content_type': self.content_type,
            'title': self.title,
            'meta_description': self.meta_description,
            'meta_keywords': self.meta_keywords,
            'headings': self.headings,
            'links': self.links,
            'word_count': self.word_count,
            'load_time': self.load_time,
            'error': self.error,
        }


class URLScanner:
    """用于爬取和分析单个 URL 的扫描器。"""

    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    def __init__(
        self,
        timeout: int = 30,
        follow_redirects: bool = True,
        verify_ssl: bool = True,
        max_content_length: int = 10 * 1024 * 1024,  # 10MB
    ):
        """
        初始化 URL 扫描器。

        参数:
            timeout: 请求超时时间（秒）
            follow_redirects: 是否跟随重定向
            verify_ssl: 是否验证 SSL 证书
            max_content_length: 最大下载内容长度
        """
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.verify_ssl = verify_ssl
        self.max_content_length = max_content_length
        self._session = requests.Session()
        self._session.headers.update(self.DEFAULT_HEADERS)

    def scan(self, url: str) -> ScanResult:
        """
        扫描单个 URL 并提取信息。

        参数:
            url: 要扫描的 URL

        返回:
            包含扫描数据的 ScanResult 对象
        """
        result = ScanResult(url)
        import time
        start_time = time.time()

        try:
            response = self._session.get(
                url,
                timeout=self.timeout,
                allow_redirects=self.follow_redirects,
                verify=self.verify_ssl,
                stream=True,
            )

            # Check content length
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > self.max_content_length:
                result.error = f"Content too large: {content_length} bytes"
                result.load_time = time.time() - start_time
                return result

            result.status_code = response.status_code
            result.content_type = response.headers.get('Content-Type', '')
            
            # 确保使用正确的编码，优先使用响应头中的编码，否则使用 UTF-8
            response.encoding = response.apparent_encoding or 'utf-8'
            result.html_content = response.text
            result.load_time = time.time() - start_time

            # Parse HTML content
            self._parse_html(url, response.text, result)

        except requests.exceptions.Timeout:
            result.error = f"Request timed out after {self.timeout} seconds"
        except requests.exceptions.TooManyRedirects:
            result.error = "Too many redirects"
        except requests.exceptions.SSLError as e:
            result.error = f"SSL error: {str(e)}"
        except requests.exceptions.RequestException as e:
            result.error = f"Request failed: {str(e)}"
        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"

        return result

    def _parse_html(self, url: str, html_content: str, result: ScanResult) -> None:
        """
        解析 HTML 内容并提取元数据和链接。

        参数:
            url: 用于解析相对链接的基础 URL
            html_content: 要解析的 HTML 内容
            result: 要填充的 ScanResult 对象
        """
        soup = BeautifulSoup(html_content, 'lxml')

        # Extract text content
        result.text_content = soup.get_text(separator=' ', strip=True)
        result.word_count = len(result.text_content.split())

        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            result.title = title_tag.get_text(strip=True)

        # Extract meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            content = meta.get('content', '')
            if name == 'description':
                result.meta_description = content
            elif name == 'keywords':
                result.meta_keywords = content

        # Extract headings
        for level in range(1, 7):
            heading_tags = soup.find_all(f'h{level}')
            if heading_tags:
                result.headings[f'h{level}'] = [
                    tag.get_text(strip=True) for tag in heading_tags
                ]

        # Extract links
        parsed_base = urlparse(url)
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue

            absolute_url = urljoin(url, href)
            link_parsed = urlparse(absolute_url)

            # Classify as internal or external
            if link_parsed.netloc == parsed_base.netloc:
                if absolute_url not in result.links['internal']:
                    result.links['internal'].append(absolute_url)
            else:
                if absolute_url not in result.links['external']:
                    result.links['external'].append(absolute_url)

        # Extract images
        for img in soup.find_all('img', src=True):
            src = urljoin(url, img['src'].strip())
            if src not in result.links['images']:
                result.links['images'].append(src)

        # Extract scripts
        for script in soup.find_all('script', src=True):
            src = urljoin(url, script['src'].strip())
            if src not in result.links['scripts']:
                result.links['scripts'].append(src)

        # Extract stylesheets
        for link in soup.find_all('link', rel='stylesheet', href=True):
            href = urljoin(url, link['href'].strip())
            if href not in result.links['stylesheets']:
                result.links['stylesheets'].append(href)

    def scan_batch(self, urls: List[str], callback=None) -> List[ScanResult]:
        """
        扫描多个 URL。

        参数:
            urls: 要扫描的 URL 列表
            callback: 每次扫描后调用的可选回调函数

        返回:
            ScanResult 对象列表
        """
        results = []
        for i, url in enumerate(urls):
            logger.info(f"Scanning URL {i+1}/{len(urls)}: {url}")
            result = self.scan(url)
            results.append(result)
            if callback:
                callback(result, i + 1, len(urls))
        return results

    def check_robots_txt(self, base_url: str, robots_path: str = "/robots.txt") -> Optional[str]:
        """
        获取并返回域名的 robots.txt 内容。

        参数:
            base_url: 域名的基础 URL
            robots_path: robots.txt 的路径，默认为 /robots.txt

        返回:
            robots.txt 内容，如果未找到返回 None
        """
        parsed = urlparse(base_url)
        if not robots_path.startswith('/'):
            robots_path = '/' + robots_path
        robots_url = f"{parsed.scheme}://{parsed.netloc}{robots_path}"

        try:
            response = self._session.get(robots_url, timeout=10)
            if response.status_code == 200:
                return response.text
        except requests.exceptions.RequestException:
            pass
        return None

    def get_sitemap_urls_from_robots(self, robots_txt: str) -> List[str]:
        """
        从 robots.txt 内容中提取站点地图 URL。

        参数:
            robots_txt: robots.txt 内容

        返回:
            站点地图 URL 列表
        """
        sitemaps = []
        for line in robots_txt.splitlines():
            line = line.strip()
            if line.lower().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                sitemaps.append(sitemap_url)
        return sitemaps