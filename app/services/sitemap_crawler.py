"""
Sitemap 爬虫模块

此模块提供了爬取网站的主协调器，
通过解析站点地图并扫描找到的每个 URL。
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import urlparse

from app.config.crawler_config import CrawlerConfig
from app.config.firecrawl_config import get_firecrawl_config
from .sitemap_parser import SitemapParser
from .url_filter import URLFilter
from .url_scanner import URLScanner, ScanResult
from .firecrawl_mcp import FirecrawlMCPService

logger = logging.getLogger(__name__)


@dataclass
class CrawlStats:
    """爬取操作的统计信息。"""
    total_urls: int = 0
    successful_scans: int = 0
    failed_scans: int = 0
    total_load_time: float = 0.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SitemapCrawler:
    """
    主爬虫，协调站点地图解析和 URL 扫描。

    使用方法:
        crawler = SitemapCrawler(sitemap_url="https://example.com/sitemap.xml")
        results = crawler.crawl()
    """

    def __init__(self, config: Optional[CrawlerConfig] = None, **kwargs):
        """
        初始化站点地图爬虫。

        参数:
            config: 包含设置的 CrawlerConfig 对象
            **kwargs: 用于覆盖配置的额外设置
        """
        if config is None:
            config = CrawlerConfig()

        # Override config with kwargs
        if kwargs:
            config_dict = asdict(config)
            config_dict.update(kwargs)
            config = CrawlerConfig.from_dict(config_dict)

        self.config = config
        self.stats = CrawlStats()
        self._results: List[ScanResult] = []
        self._sitemap_parser: Optional[SitemapParser] = None
        self._url_scanner: Optional[URLScanner] = None
        self._url_filter: Optional[URLFilter] = None
        self._firecrawl_service: Optional[FirecrawlMCPService] = None

    def _init_firecrawl(self):
        """
        初始化 Firecrawl MCP 服务（如果配置启用）。
        """
        if not self.config.use_firecrawl:
            return

        try:
            # 从 firecrawl.yaml 读取详细配置
            firecrawl_cfg = get_firecrawl_config()
            
            firecrawl_config = {
                "firecrawl_api_url": firecrawl_cfg.api_url,
                "firecrawl_api_key": firecrawl_cfg.api_key,
                "firecrawl_timeout": firecrawl_cfg.timeout,
                "firecrawl_api_version": firecrawl_cfg.api_version,
            }
            self._firecrawl_service = FirecrawlMCPService.from_config(firecrawl_config)

            # 检查服务是否可用
            if self._firecrawl_service.is_available():
                logger.info("Firecrawl MCP 服务已连接")
            else:
                logger.warning("Firecrawl MCP 服务不可用，将回退到传统爬取方式")
                self._firecrawl_service = None
        except Exception as e:
            logger.error(f"初始化 Firecrawl 失败: {str(e)}")
            self._firecrawl_service = None

    async def _scan_with_firecrawl(self, url: str) -> ScanResult:
        """
        使用 Firecrawl 扫描单个 URL（异步）。

        参数:
            url: 要扫描的 URL

        返回:
            ScanResult 对象
        """
        result = ScanResult(url)
        import time
        start_time = time.time()

        try:
            if not self._firecrawl_service:
                result.error = "Firecrawl 服务未初始化"
                result.load_time = time.time() - start_time
                return result

            # 调用 Firecrawl 进行爬取
            firecrawl_cfg = get_firecrawl_config()
            firecrawl_result = await self._firecrawl_service.scrape_url(
                url=url,
                formats=["markdown", "html"],
                only_main_content=firecrawl_cfg.only_main_content,
            )

            if firecrawl_result.success and firecrawl_result.markdown:
                result.status_code = 200
                result.content_type = "text/html"
                result.title = firecrawl_result.title
                result.text_content = firecrawl_result.markdown
                result.html_content = firecrawl_result.html
                result.word_count = len(result.text_content.split())
                result.meta_description = firecrawl_result.metadata.get("description")
                result.meta_keywords = firecrawl_result.metadata.get("keywords")
                result.load_time = time.time() - start_time
                logger.info(f"Firecrawl 成功解析: {url}")
            else:
                result.error = firecrawl_result.error or "Firecrawl 解析失败"
                result.load_time = time.time() - start_time
                logger.warning(f"Firecrawl 解析失败 {url}: {result.error}")

        except Exception as e:
            result.error = f"Firecrawl 异常: {str(e)}"
            result.load_time = time.time() - start_time
            logger.error(f"Firecrawl 扫描错误: {str(e)}")

        return result

    @property
    def results(self) -> List[ScanResult]:
        """获取爬取结果。"""
        return self._results

    @property
    def statistics(self) -> CrawlStats:
        """获取爬取统计信息。"""
        return self.stats

    def _normalize_sitemap_url(self, url: str) -> str:
        """
        标准化站点地图 URL。
        如果输入只是域名，自动补充 https 协议、root_url 和配置的 sitemap 路径。

        参数:
            url: 输入的 URL 或域名

        返回:
            标准化后的完整站点地图 URL
        
        示例:
            - 输入: "example.com", root_url: "/blog"
              输出: "https://example.com/blog/sitemap.xml"
            - 输入: "example.com/docs", root_url: ""
              输出: "https://example.com/docs/sitemap.xml"
        """
        url = url.strip()

        # 如果没有协议，自动补充 https
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        # 解析 URL
        parsed = urlparse(url)
        
        # 如果只是域名（没有路径），添加 root_url 和 sitemap 路径
        if not parsed.path or parsed.path == '/':
            # 构建完整路径：root_url + sitemap_path
            root_url = self.config.root_url.rstrip('/')
            sitemap_path = self.config.sitemap_path
            
            # 确保 sitemap_path 以 / 开头
            if not sitemap_path.startswith('/'):
                sitemap_path = '/' + sitemap_path
            
            # 拼接：root_url + sitemap_path
            full_path = f"{root_url}{sitemap_path}" if root_url else sitemap_path
            
            url = f"{parsed.scheme}://{parsed.netloc}{full_path}"

        return url

    def _is_allowed_by_robots(self, robots_txt: str, user_agent: str = '*') -> bool:
        """
        检查 robots.txt 是否允许指定的用户代理爬取。

        参数:
            robots_txt: robots.txt 内容
            user_agent: 用户代理字符串，默认为 '*'

        返回:
            如果允许爬取返回 True，否则返回 False
        """
        if not robots_txt:
            return True

        current_agent = None
        allow_all = True
        disallowed_paths = []

        for line in robots_txt.splitlines():
            line = line.strip()

            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue

            # 处理 User-agent 行
            if line.lower().startswith('user-agent:'):
                agent = line.split(':', 1)[1].strip()
                current_agent = agent
                # 如果匹配到指定的 user_agent 或通用 '*'，重置允许状态
                if agent == user_agent or agent == '*':
                    allow_all = True
                    disallowed_paths = []
                else:
                    current_agent = None

            # 只处理当前匹配的 user_agent 的规则
            if current_agent is None:
                continue

            # 处理 Disallow 行
            if line.lower().startswith('disallow:'):
                path = line.split(':', 1)[1].strip()
                if path == '/':
                    allow_all = False
                else:
                    disallowed_paths.append(path)

            # 处理 Allow 行（重置特定路径的禁止状态）
            if line.lower().startswith('allow:'):
                path = line.split(':', 1)[1].strip()
                if path in disallowed_paths:
                    disallowed_paths.remove(path)

        return allow_all

    def crawl(
            self,
            sitemap_url: Optional[str] = None,
            progress_callback: Optional[Callable[[ScanResult, int, int], None]] = None,
            page_processed_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
            stop_flag=None,  # 新增：停止标志
    ) -> List[ScanResult]:
        """
        开始爬取操作。

        参数:
            sitemap_url: 可选的站点地图 URL（覆盖配置）
            progress_callback: 可选的进度更新回调函数
            page_processed_callback: 可选的页面处理完成回调函数，每扫描完一个URL立即调用
            stop_flag: 可选的停止标志(threading.Event)，设置时中断爬取

        返回:
            ScanResult 对象列表
        """
        sitemap_url = sitemap_url or self.config.sitemap_url
        if not sitemap_url:
            raise ValueError("sitemap_url must be provided")

        # 标准化 sitemap URL
        sitemap_url = self._normalize_sitemap_url(sitemap_url)
        logger.info(f"标准化后的站点地图 URL: {sitemap_url}")

        self.stats = CrawlStats()
        self.stats.start_time = datetime.now().isoformat()
        self._results = []

        logger.info(f"Starting crawl for sitemap: {sitemap_url}")

        # Initialize Firecrawl if enabled
        self._init_firecrawl()

        # Initialize scanner first for robots.txt check
        firecrawl_cfg = get_firecrawl_config()
        self._url_scanner = URLScanner(
            timeout=self.config.timeout,
            follow_redirects=self.config.follow_redirects,
            verify_ssl=self.config.verify_ssl,
            max_content_length=self.config.max_content_length,
            use_firecrawl=self.config.use_firecrawl,
            firecrawl_api_url=firecrawl_cfg.api_url,
            firecrawl_api_key=firecrawl_cfg.api_key,
            firecrawl_timeout=firecrawl_cfg.timeout,
            firecrawl_api_version=firecrawl_cfg.api_version,
            firecrawl_only_main_content=firecrawl_cfg.only_main_content,
        )

        # Check robots.txt first
        if self.config.check_robots_txt:
            logger.info("检查 robots.txt...")
            robots_txt = self._url_scanner.check_robots_txt(sitemap_url, self.config.robots_path)
            if robots_txt:
                logger.info("找到 robots.txt")
                if not self._is_allowed_by_robots(robots_txt):
                    logger.error("robots.txt 禁止爬取此网站")
                    raise PermissionError("robots.txt 禁止爬取此网站，请检查 robots.txt 设置")
                else:
                    logger.info("robots.txt 允许爬取")
            else:
                logger.info("未找到 robots.txt，继续爬取")

        # Initialize parser
        self._sitemap_parser = SitemapParser(sitemap_url)

        # Fetch and parse sitemap
        logger.info("获取站点地图...")
        self._sitemap_parser.fetch_sitemap()

        logger.info("解析站点地图...")
        urls = self._sitemap_parser.parse()
        logger.info(f"在站点地图中找到 {len(urls)} 个 URL")

        # 初始化URL过滤器并应用过滤规则
        self._url_filter = URLFilter.from_config(self.config)
        if self.config.url_include_patterns or self.config.url_exclude_patterns:
            logger.info("应用URL过滤规则...")
            original_count = len(urls)
            urls = self._url_filter.filter_urls(urls)
            filtered_count = original_count - len(urls)
            if filtered_count > 0:
                logger.info(f"URL过滤: 原始={original_count}, 过滤后={len(urls)}, 排除={filtered_count}")
            else:
                logger.info("所有URL都通过过滤规则")
        else:
            logger.info("未配置URL过滤规则，处理所有URL")

        # Apply max_urls limit
        if self.config.max_urls and len(urls) > self.config.max_urls:
            urls = urls[:self.config.max_urls]
            logger.info(f"限制为 {self.config.max_urls} 个 URL")

        self.stats.total_urls = len(urls)

        # Scan each URL
        logger.info("Starting URL scans...")
        for i, url in enumerate(urls):
            # 检查是否应该停止
            if stop_flag and stop_flag.is_set():
                logger.info(f"爬取任务被用户中断 (已处理 {i}/{len(urls)} 个URL)")
                break

            if self.config.verbose:
                logger.info(f"Scanning URL {i + 1}/{len(urls)}: {url}")

            # Use URLScanner (which internally uses Firecrawl if enabled)
            result = self._url_scanner.scan(url)

            self._results.append(result)

            if result.error:
                self.stats.failed_scans += 1
                logger.warning(f"Failed to scan {url}: {result.error}")
            else:
                self.stats.successful_scans += 1

            self.stats.total_load_time += result.load_time

            if progress_callback:
                progress_callback(result, i + 1, len(urls))

            # 如果提供了页面处理回调，立即调用
            if page_processed_callback and not result.error:
                try:
                    page_data = result.to_dict()
                    page_processed_callback(page_data)
                    logger.info(f"页面 {url} 已触发实时处理回调")
                except Exception as e:
                    logger.error(f"页面处理回调失败: {str(e)}")

            # Delay between requests
            if self.config.delay_between_requests > 0 and i < len(urls) - 1:
                import time
                time.sleep(self.config.delay_between_requests)

        self.stats.end_time = datetime.now().isoformat()

        # 禁用本地保存结果，避免磁盘空间暴涨
        # if self.config.save_results and self.config.output_dir:
        #     self.save_results()

        logger.info(f"Crawl completed: {self.stats.successful_scans} successful, "
                    f"{self.stats.failed_scans} failed")

        return self._results

    def crawl_urls(self, urls: List[str], stop_flag=None) -> List[ScanResult]:
        """
        爬取指定的 URL 列表，无需解析站点地图。

        参数:
            urls: 要爬取的 URL 列表
            stop_flag: 可选的停止标志(threading.Event)，设置时中断爬取

        返回:
            ScanResult 对象列表
        """
        self.stats = CrawlStats()
        self.stats.start_time = datetime.now().isoformat()
        self._results = []
        self.stats.total_urls = len(urls)

        # Initialize Firecrawl if enabled
        self._init_firecrawl()

        firecrawl_cfg = get_firecrawl_config()
        self._url_scanner = URLScanner(
            timeout=self.config.timeout,
            follow_redirects=self.config.follow_redirects,
            verify_ssl=self.config.verify_ssl,
            max_content_length=self.config.max_content_length,
            use_firecrawl=self.config.use_firecrawl,
            firecrawl_api_url=firecrawl_cfg.api_url,
            firecrawl_api_key=firecrawl_cfg.api_key,
            firecrawl_timeout=firecrawl_cfg.timeout,
            firecrawl_api_version=firecrawl_cfg.api_version,
            firecrawl_only_main_content=firecrawl_cfg.only_main_content,
        )

        for i, url in enumerate(urls):
            # 检查是否应该停止
            if stop_flag and stop_flag.is_set():
                logger.info(f"爬取任务被用户中断 (已处理 {i}/{len(urls)} 个URL)")
                break

            logger.info(f"Scanning URL {i + 1}/{len(urls)}: {url}")

            # Use URLScanner (which internally uses Firecrawl if enabled)
            result = self._url_scanner.scan(url)

            self._results.append(result)

            if result.error:
                self.stats.failed_scans += 1
            else:
                self.stats.successful_scans += 1

            self.stats.total_load_time += result.load_time

        self.stats.end_time = datetime.now().isoformat()

        # 禁用本地保存结果，避免磁盘空间暴涨
        # if self.config.save_results and self.config.output_dir:
        #     self.save_results()

        return self._results

    def save_results(self, filename: Optional[str] = None) -> str:
        """
        将爬取结果保存到 JSON 文件。

        参数:
            filename: 可选的文件名（默认: crawl_results_TIMESTAMP.json）

        返回:
            保存文件的路径
        """
        if not self.config.output_dir:
            raise ValueError("output_dir must be configured to save results")

        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crawl_results_{timestamp}.json"

        filepath = output_path / filename

        data = {
            'statistics': self.stats.to_dict(),
            'config': asdict(self.config),
            'results': [result.to_dict() for result in self._results],
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {filepath}")
        return str(filepath)

    def get_summary(self) -> Dict[str, Any]:
        """
        获取爬取结果的摘要。

        返回:
            包含爬取摘要的字典
        """
        summary = {
            'statistics': self.stats.to_dict(),
            'urls_by_status': {},
            'avg_load_time': 0.0,
        }

        # Group by status code
        for result in self._results:
            status = str(result.status_code) if result.status_code else 'error'
            if status not in summary['urls_by_status']:
                summary['urls_by_status'][status] = 0
            summary['urls_by_status'][status] += 1

        # Calculate average load time
        if self.stats.successful_scans > 0:
            summary['avg_load_time'] = (
                self.stats.total_load_time / self.stats.successful_scans
            )

        return summary

    def print_report(self) -> None:
        """打印人类可读的爬取结果报告。"""
        print("\n" + "=" * 60)
        print("CRAWL REPORT")
        print("=" * 60)

        summary = self.get_summary()

        print(f"\nStart Time: {self.stats.start_time}")
        print(f"End Time: {self.stats.end_time}")
        print(f"\nTotal URLs: {self.stats.total_urls}")
        print(f"Successful: {self.stats.successful_scans}")
        print(f"Failed: {self.stats.failed_scans}")
        print(f"Average Load Time: {summary['avg_load_time']:.2f}s")

        print("\nStatus Code Distribution:")
        for status, count in sorted(summary['urls_by_status'].items()):
            print(f"  {status}: {count}")

        if self.stats.failed_scans > 0:
            print("\nFailed URLs:")
            for result in self._results:
                if result.error:
                    print(f"  - {result.url}: {result.error}")

        print("\n" + "=" * 60)
