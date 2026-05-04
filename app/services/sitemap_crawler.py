"""
Sitemap 爬虫模块

此模块提供了爬取网站的主协调器，
通过解析站点地图并扫描找到的每个 URL。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict

from .sitemap_parser import SitemapParser
from .url_scanner import URLScanner, ScanResult

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


@dataclass
class CrawlConfig:
    """站点地图爬虫的配置。"""
    # 站点地图设置
    sitemap_url: str = ""
    check_robots_txt: bool = True

    # 扫描器设置
    timeout: int = 30
    follow_redirects: bool = True
    verify_ssl: bool = True
    max_content_length: int = 10 * 1024 * 1024  # 10MB

    # 爬取设置
    max_urls: Optional[int] = None  # 限制爬取的 URL 数量
    delay_between_requests: float = 0.0  # 请求之间的延迟（秒）

    # 输出设置
    output_dir: Optional[str] = None
    save_results: bool = True
    verbose: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CrawlConfig':
        """从字典创建配置。"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SitemapCrawler:
    """
    主爬虫，协调站点地图解析和 URL 扫描。

    使用方法:
        crawler = SitemapCrawler(sitemap_url="https://example.com/sitemap.xml")
        results = crawler.crawl()
    """

    def __init__(self, config: Optional[CrawlConfig] = None, **kwargs):
        """
        初始化站点地图爬虫。

        参数:
            config: 包含设置的 CrawlConfig 对象
            **kwargs: 用于覆盖配置的额外设置
        """
        if config is None:
            config = CrawlConfig()

        # Override config with kwargs
        if kwargs:
            config_dict = asdict(config)
            config_dict.update(kwargs)
            config = CrawlConfig.from_dict(config_dict)

        self.config = config
        self.stats = CrawlStats()
        self._results: List[ScanResult] = []
        self._sitemap_parser: Optional[SitemapParser] = None
        self._url_scanner: Optional[URLScanner] = None

    @property
    def results(self) -> List[ScanResult]:
        """获取爬取结果。"""
        return self._results

    @property
    def statistics(self) -> CrawlStats:
        """获取爬取统计信息。"""
        return self.stats

    def crawl(
        self,
        sitemap_url: Optional[str] = None,
        progress_callback: Optional[Callable[[ScanResult, int, int], None]] = None,
    ) -> List[ScanResult]:
        """
        开始爬取操作。

        参数:
            sitemap_url: 可选的站点地图 URL（覆盖配置）
            progress_callback: 可选的进度更新回调函数

        返回:
            ScanResult 对象列表
        """
        sitemap_url = sitemap_url or self.config.sitemap_url
        if not sitemap_url:
            raise ValueError("sitemap_url must be provided")

        self.stats = CrawlStats()
        self.stats.start_time = datetime.now().isoformat()
        self._results = []

        logger.info(f"Starting crawl for sitemap: {sitemap_url}")

        # Initialize parser and scanner
        self._sitemap_parser = SitemapParser(sitemap_url)
        self._url_scanner = URLScanner(
            timeout=self.config.timeout,
            follow_redirects=self.config.follow_redirects,
            verify_ssl=self.config.verify_ssl,
            max_content_length=self.config.max_content_length,
        )

        # Fetch and parse sitemap
        logger.info("Fetching sitemap...")
        self._sitemap_parser.fetch_sitemap()

        logger.info("Parsing sitemap...")
        urls = self._sitemap_parser.parse()
        logger.info(f"Found {len(urls)} URLs in sitemap")

        # Apply max_urls limit
        if self.config.max_urls and len(urls) > self.config.max_urls:
            urls = urls[:self.config.max_urls]
            logger.info(f"Limited to {self.config.max_urls} URLs")

        self.stats.total_urls = len(urls)

        # Check robots.txt if enabled
        if self.config.check_robots_txt and urls:
            base_url = urls[0]
            robots_txt = self._url_scanner.check_robots_txt(base_url)
            if robots_txt:
                logger.info("Found robots.txt")

        # Scan each URL
        logger.info("Starting URL scans...")
        for i, url in enumerate(urls):
            if self.config.verbose:
                logger.info(f"Scanning URL {i+1}/{len(urls)}: {url}")

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

            # Delay between requests
            if self.config.delay_between_requests > 0 and i < len(urls) - 1:
                import time
                time.sleep(self.config.delay_between_requests)

        self.stats.end_time = datetime.now().isoformat()

        # Save results if configured
        if self.config.save_results and self.config.output_dir:
            self.save_results()

        logger.info(f"Crawl completed: {self.stats.successful_scans} successful, "
                   f"{self.stats.failed_scans} failed")

        return self._results

    def crawl_urls(self, urls: List[str]) -> List[ScanResult]:
        """
        爬取指定的 URL 列表，无需解析站点地图。

        参数:
            urls: 要爬取的 URL 列表

        返回:
            ScanResult 对象列表
        """
        self.stats = CrawlStats()
        self.stats.start_time = datetime.now().isoformat()
        self._results = []
        self.stats.total_urls = len(urls)

        self._url_scanner = URLScanner(
            timeout=self.config.timeout,
            follow_redirects=self.config.follow_redirects,
            verify_ssl=self.config.verify_ssl,
            max_content_length=self.config.max_content_length,
        )

        for i, url in enumerate(urls):
            logger.info(f"Scanning URL {i+1}/{len(urls)}: {url}")
            result = self._url_scanner.scan(url)
            self._results.append(result)

            if result.error:
                self.stats.failed_scans += 1
            else:
                self.stats.successful_scans += 1

            self.stats.total_load_time += result.load_time

        self.stats.end_time = datetime.now().isoformat()

        if self.config.save_results and self.config.output_dir:
            self.save_results()

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