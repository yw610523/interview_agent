"""
URL 扫描器模块

此模块提供扫描/爬取单个 URL 的功能，
从网页中提取内容、链接和元数据。
"""

import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

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
            "internal": [],
            "external": [],
            "images": [],
            "scripts": [],
            "stylesheets": [],
        }
        self.word_count: int = 0
        self.load_time: float = 0.0
        self.error: Optional[str] = None
        self.html_content: Optional[str] = None
        self.text_content: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """将扫描结果转换为字典。"""
        return {
            "url": self.url,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "title": self.title,
            "meta_description": self.meta_description,
            "meta_keywords": self.meta_keywords,
            "headings": self.headings,
            "links": self.links,
            "word_count": self.word_count,
            "load_time": self.load_time,
            "error": self.error,
            "html_content": self.html_content,
            "text_content": self.text_content,
        }


class URLScanner:
    """用于爬取和分析单个 URL 的扫描器。"""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    def __init__(
            self,
            timeout: int = 30,
            follow_redirects: bool = True,
            verify_ssl: bool = True,
            max_content_length: int = 10 * 1024 * 1024,  # 10MB
            use_firecrawl: bool = False,
            firecrawl_api_url: str = "http://localhost:3002",
            firecrawl_api_key: Optional[str] = None,
            firecrawl_timeout: int = 60,
            firecrawl_api_version: str = "v2",
            firecrawl_only_main_content: bool = True,
    ):
        """
        初始化 URL 扫描器。

        参数:
            timeout: 请求超时时间（秒）
            follow_redirects: 是否跟随重定向
            verify_ssl: 是否验证 SSL 证书
            max_content_length: 最大下载内容长度
            use_firecrawl: 是否启用 Firecrawl
            firecrawl_api_url: Firecrawl API URL
            firecrawl_api_key: Firecrawl API Key
            firecrawl_timeout: Firecrawl 超时时间
            firecrawl_api_version: Firecrawl API 版本（默认 v2）
            firecrawl_only_main_content: 是否只提取主要内容
        """
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.verify_ssl = verify_ssl
        self.max_content_length = max_content_length
        self.use_firecrawl = use_firecrawl
        self.firecrawl_api_url = firecrawl_api_url
        self.firecrawl_api_key = firecrawl_api_key
        self.firecrawl_timeout = firecrawl_timeout
        self.firecrawl_api_version = firecrawl_api_version
        self.firecrawl_only_main_content = firecrawl_only_main_content
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
            # 如果启用了 Firecrawl，优先使用 Firecrawl
            logger.info(
                f"URLScanner配置: use_firecrawl={self.use_firecrawl}, firecrawl_api_url={self.firecrawl_api_url}")
            if self.use_firecrawl and self.firecrawl_api_url:
                logger.info(f"使用 Firecrawl 爬取页面: {url}")
                firecrawl_result = self._scan_with_firecrawl(url)

                if firecrawl_result.success:
                    logger.info(f"Firecrawl 爬取成功: {firecrawl_result.title}")

                    result.status_code = 200
                    result.title = firecrawl_result.title
                    result.html_content = firecrawl_result.html or ""

                    # 直接使用 Markdown 内容
                    markdown_content = firecrawl_result.markdown or ""
                    result.text_content = markdown_content
                    result.word_count = len(result.text_content.split())
                    result.content_type = firecrawl_result.content_type or "text/html"
                    result.load_time = time.time() - start_time

                    # 解析 HTML 内容
                    if result.html_content:
                        self._parse_html(url, result.html_content, result)

                    return result
                else:
                    logger.warning(f"Firecrawl 爬取失败: {firecrawl_result.error}，降级使用传统爬虫")

            # 检测是否为微信公众号文章（需要 JavaScript 渲染）
            is_wechat = "weixin.qq.com" in url or "mp.weixin.qq.com" in url
            if is_wechat:
                logger.info(f"检测到微信公众号文章: {url}")
                logger.info("提示: 此类页面需要 JavaScript 渲染，建议启用 Firecrawl MCP 服务")

            response = self._session.get(
                url,
                timeout=self.timeout,
                allow_redirects=self.follow_redirects,
                verify=self.verify_ssl,
                stream=True,
            )

            # Check content length
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > self.max_content_length:
                result.error = f"Content too large: {content_length} bytes"
                result.load_time = time.time() - start_time
                return result

            result.status_code = response.status_code
            result.content_type = response.headers.get("Content-Type", "")

            # 确保使用正确的编码，优先使用响应头中的编码，否则使用 UTF-8
            response.encoding = response.apparent_encoding or "utf-8"
            result.html_content = response.text

            if "text/html" in result.content_type.lower():
                soup = BeautifulSoup(response.content, "html.parser")

                # 智能提取标题（支持多种来源）
                result.title = self._extract_title(soup, url)

                # 提取文本内容
                result.text_content = soup.get_text(separator="\n", strip=True)
                result.word_count = len(result.text_content.split())

                # 微信公众号文章内容验证（仅在使用传统爬虫时）
                if is_wechat and len(result.text_content) < 200:
                    logger.warning(
                        f"微信公众号文章内容过短({len(result.text_content)}字符)，"
                        f"可能是 JavaScript 渲染导致。建议启用 FIRECRAWL_ENABLED=true"
                    )

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
        soup = BeautifulSoup(html_content, "lxml")

        # Extract text content
        result.text_content = soup.get_text(separator=" ", strip=True)
        result.word_count = len(result.text_content.split())

        # Extract title (已在 scan 方法中处理)
        # Title extraction is handled in _extract_title method

        # Extract meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name")
            if isinstance(name, list):
                name = name[0] if name else ""
            if name is None:
                name = ""
            name = str(name).lower()
            content = meta.get("content", "")
            if isinstance(content, list):
                content = content[0] if content else ""
            content = str(content)
            if name == "description":
                result.meta_description = content
            elif name == "keywords":
                result.meta_keywords = content

        # Extract headings
        for level in range(1, 7):
            heading_tags = soup.find_all(f"h{level}")
            if heading_tags:
                result.headings[f"h{level}"] = [
                    tag.get_text(strip=True) for tag in heading_tags
                ]

        # Extract links
        parsed_base = urlparse(url)
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if isinstance(href, list):
                href = href[0] if href else ""
            href = str(href).strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            absolute_url = urljoin(url, href)
            link_parsed = urlparse(absolute_url)

            # Classify as internal or external
            if link_parsed.netloc == parsed_base.netloc:
                if absolute_url not in result.links["internal"]:
                    result.links["internal"].append(absolute_url)
            else:
                if absolute_url not in result.links["external"]:
                    result.links["external"].append(absolute_url)

        # Extract images
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if isinstance(src, list):
                src = src[0] if src else ""
            src = urljoin(url, str(src).strip())
            if src not in result.links["images"]:
                result.links["images"].append(src)

        # Extract scripts
        for script in soup.find_all("script", src=True):
            src = script["src"]
            if isinstance(src, list):
                src = src[0] if src else ""
            src = urljoin(url, str(src).strip())
            if src not in result.links["scripts"]:
                result.links["scripts"].append(src)

        # Extract stylesheets
        for link in soup.find_all("link", rel="stylesheet", href=True):
            href = link["href"]
            if isinstance(href, list):
                href = href[0] if href else ""
            href = urljoin(url, str(href).strip())
            if href not in result.links["stylesheets"]:
                result.links["stylesheets"].append(href)

    def _convert_relative_urls(self, markdown_content: str, base_url: str) -> str:
        """
        将 Markdown 内容中的相对 URL 转换为绝对 URL

        参数:
            markdown_content: Markdown 格式的内容
            base_url: 基础 URL，用于解析相对路径

        返回:
            转换后的 Markdown 内容
        """
        import re
        from urllib.parse import urljoin

        # 匹配 Markdown 图片语法: ![alt](url)
        def replace_image_url(match):
            alt_text = match.group(1)
            img_url = match.group(2)

            # 如果已经是绝对 URL，不处理
            if img_url.startswith(('http://', 'https://', 'data:')):
                return match.group(0)

            # 转换为绝对 URL
            absolute_url = urljoin(base_url, img_url)
            logger.debug(f"转换图片URL: {img_url} -> {absolute_url}")
            return f'![{alt_text}]({absolute_url})'

        # 替换图片 URL
        markdown_content = re.sub(r'!\[(.*?)\]\(([^)]+)\)', replace_image_url, markdown_content)

        # 匹配 Markdown 链接语法: [text](url)
        def replace_link_url(match):
            link_text = match.group(1)
            link_url = match.group(2)

            # 如果已经是绝对 URL 或锚点，不处理
            if link_url.startswith(('http://', 'https://', '#', 'mailto:', 'tel:')):
                return match.group(0)

            # 转换为绝对 URL
            absolute_url = urljoin(base_url, link_url)
            logger.debug(f"转换链接URL: {link_url} -> {absolute_url}")
            return f'[{link_text}]({absolute_url})'

        # 替换链接 URL
        markdown_content = re.sub(r'\[(.*?)\]\(([^)]+)\)', replace_link_url, markdown_content)

        return markdown_content

    def _extract_title(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """
        智能提取页面标题，支持多种来源和格式

        优先级：
        1. og:title (Open Graph)
        2. Twitter title
        3. <title> 标签
        4. 微信公众号专用标题选择器
        5. h1 标签
        """
        title = None

        # 1. 尝试 Open Graph title (最可靠)
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
            if title:
                logger.debug(f"从 og:title 提取标题: {title}")
                return title

        # 2. 尝试 Twitter title
        twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
        if twitter_title and twitter_title.get("content"):
            title = twitter_title["content"].strip()
            if title:
                logger.debug(f"从 twitter:title 提取标题: {title}")
                return title

        # 3. 尝试标准 <title> 标签
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip()
            if title:
                logger.debug(f"从 <title> 标签提取标题: {title}")
                return title

        # 4. 微信公众号特殊处理
        if "weixin.qq.com" in url or "mp.weixin.qq.com" in url:
            # 微信公众号文章标题通常在 id="activity-name" 或 class="rich_media_title" 中
            wechat_title = soup.find(id="activity-name")
            if not wechat_title:
                wechat_title = soup.find(class_="rich_media_title")
            if wechat_title:
                title = wechat_title.get_text(strip=True)
                if title:
                    logger.debug(f"从微信公众号专用选择器提取标题: {title}")
                    return title

        # 5. 尝试 h1 标签
        h1_tag = soup.find("h1")
        if h1_tag:
            title = h1_tag.get_text(strip=True)
            if title:
                logger.debug(f"从 <h1> 标签提取标题: {title}")
                return title

        # 6. 如果都没有，返回 None
        logger.warning(f"无法从页面提取标题: {url}")
        return None

    def _scan_with_firecrawl(self, url: str):
        """
        使用 Firecrawl 爬取页面（支持 JavaScript 渲染）。

        参数:
            url: 要爬取的 URL

        返回:
            FirecrawlResult 对象
        """
        import asyncio
        from app.services.firecrawl_mcp import FirecrawlMCPService
        import nest_asyncio

        # 创建 Firecrawl 服务实例
        firecrawl_service = FirecrawlMCPService(
            api_url=self.firecrawl_api_url,
            api_key=self.firecrawl_api_key,
            timeout=self.firecrawl_timeout,
            api_version=self.firecrawl_api_version,
        )

        # 定义异步爬取函数
        async def do_scrape():
            return await firecrawl_service.scrape_url(
                url=url,
                formats=["markdown", "html"],
                only_main_content=self.firecrawl_only_main_content,
            )

        try:
            # 尝试获取当前事件循环
            try:
                loop = asyncio.get_running_loop()
                # 如果已经有运行的循环，使用 nest_asyncio 允许嵌套
                logger.debug("检测到运行中的事件循环，应用 nest_asyncio")
                nest_asyncio.apply(loop)
                # 在当前循环中运行
                return loop.run_until_complete(do_scrape())
            except RuntimeError:
                # 没有运行的循环，创建新的
                logger.debug("未检测到运行中的事件循环，创建新循环")
                return asyncio.run(do_scrape())
        except Exception as e:
            logger.error(f"Firecrawl 爬取异常: {str(e)}")
            from app.services.firecrawl_mcp import FirecrawlResult
            return FirecrawlResult(success=False, error=str(e), url=url)

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
            logger.info(f"Scanning URL {i + 1}/{len(urls)}: {url}")
            result = self.scan(url)
            results.append(result)
            if callback:
                callback(result, i + 1, len(urls))
        return results

    def check_robots_txt(
            self, base_url: str, robots_path: str = "/robots.txt", root_url: str = ""
    ) -> Optional[str]:
        """
        获取并返回域名的 robots.txt 内容。

        参数:
            base_url: 域名的基础 URL
            robots_path: robots.txt 的路径，默认为 /robots.txt
            root_url: 网站根路径前缀（如 /blog），robots.txt 始终在网站根目录，不使用此参数

        返回:
            robots.txt 内容，如果未找到返回 None

        注意:
            robots.txt 始终位于网站根目录（https://domain.com/robots.txt）
            不受 root_url 影响。如果需要自定义路径，请使用 robots_path 参数。
        """
        parsed = urlparse(base_url)
        if not robots_path.startswith("/"):
            robots_path = "/" + robots_path
        # robots.txt 始终在根目录，不拼接 root_url
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
            if line.lower().startswith("sitemap:"):
                sitemap_url = line.split(":", 1)[1].strip()
                sitemaps.append(sitemap_url)
        return sitemaps
