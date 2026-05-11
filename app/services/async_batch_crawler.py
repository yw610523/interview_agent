"""
异步批量爬虫模块

提供基于多线程/异步的批量URL爬取功能，防止系统瘫痪
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any
from urllib.parse import urlparse

from app.config.crawler_config import CrawlerConfig
from app.config.firecrawl_config import get_firecrawl_config
from .firecrawl_mcp import FirecrawlMCPService
from .url_filter import URLFilter
from .url_scanner import URLScanner, ScanResult

logger = logging.getLogger(__name__)


@dataclass
class AsyncCrawlStats:
    """异步爬取统计信息"""
    total_urls: int = 0
    successful_scans: int = 0
    failed_scans: int = 0
    total_load_time: float = 0.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    active_threads: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_urls': self.total_urls,
            'successful_scans': self.successful_scans,
            'failed_scans': self.failed_scans,
            'total_load_time': self.total_load_time,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'active_threads': self.active_threads,
        }


class AsyncBatchCrawler:
    """
    异步批量爬虫，使用多线程/异步方式爬取多个URL
    
    特点：
    - 并发爬取，提高整体效率
    - 单个URL失败不影响其他URL
    - 支持进度回调和停止控制
    - 防止系统瘫痪
    """

    def __init__(self, config: Optional[CrawlerConfig] = None, **kwargs):
        """
        初始化异步批量爬虫
        
        参数:
            config: 爬虫配置对象
            max_workers: 最大并发线程数（默认5）
            timeout_per_url: 每个URL的超时时间（秒）
            **kwargs: 其他配置参数
        """
        if config is None:
            config = CrawlerConfig()
        
        # 设置默认并发数
        self.max_workers = kwargs.get('max_workers', 5)
        self.timeout_per_url = kwargs.get('timeout_per_url', config.timeout)
        
        self.config = config
        self.stats = AsyncCrawlStats()
        self._results: List[ScanResult] = []
        self._url_scanner: Optional[URLScanner] = None
        self._url_filter: Optional[URLFilter] = None
        self._firecrawl_service: Optional[FirecrawlMCPService] = None
        self._stop_flag = False
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

    def _init_scanner(self):
        """初始化URL扫描器"""
        firecrawl_cfg = get_firecrawl_config()
        self._url_scanner = URLScanner(
            timeout=self.timeout_per_url,
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

    def _scan_single_url(self, url: str, index: int, total: int) -> ScanResult:
        """
        扫描单个URL（在线程中执行）
        
        参数:
            url: 要扫描的URL
            index: 当前URL索引
            total: 总URL数量
            
        返回:
            ScanResult对象
        """
        if self._stop_flag:
            result = ScanResult(url)
            result.error = "任务已停止"
            return result

        logger.info(f"开始扫描 [{index + 1}/{total}]: {url}")
        
        try:
            scanner = URLScanner(
                timeout=self.timeout_per_url,
                follow_redirects=self.config.follow_redirects,
                verify_ssl=self.config.verify_ssl,
                max_content_length=self.config.max_content_length,
                use_firecrawl=self.config.use_firecrawl,
                firecrawl_api_url=get_firecrawl_config().api_url,
                firecrawl_api_key=get_firecrawl_config().api_key,
                firecrawl_timeout=get_firecrawl_config().timeout,
                firecrawl_api_version=get_firecrawl_config().api_version,
                firecrawl_only_main_content=get_firecrawl_config().only_main_content,
            )
            
            result = scanner.scan(url)
            
            if result.error:
                logger.warning(f"扫描失败 [{index + 1}/{total}] {url}: {result.error}")
            else:
                logger.info(f"扫描成功 [{index + 1}/{total}] {url}: {result.title}")
            
            return result
            
        except Exception as e:
            logger.error(f"扫描异常 [{index + 1}/{total}] {url}: {str(e)}")
            result = ScanResult(url)
            result.error = f"扫描异常: {str(e)}"
            return result

    def crawl_batch(
        self,
        urls: List[str],
        progress_callback: Optional[Callable[[ScanResult, int, int], None]] = None,
        page_processed_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        stop_flag=None,
    ) -> List[ScanResult]:
        """
        批量爬取URL列表（多线程并发）
        
        参数:
            urls: 要爬取的URL列表
            progress_callback: 进度回调函数
            page_processed_callback: 页面处理完成回调
            stop_flag: 停止标志（threading.Event）
            
        返回:
            ScanResult对象列表
        """
        from datetime import datetime
        
        self.stats = AsyncCrawlStats()
        self.stats.start_time = datetime.now().isoformat()
        self.stats.total_urls = len(urls)
        self._results = []
        self._stop_flag = False
        
        if stop_flag:
            self._external_stop_flag = stop_flag
        
        logger.info(f"开始异步批量爬取，共 {len(urls)} 个URL，并发数: {self.max_workers}")
        
        # 应用URL过滤
        if self.config.url_include_patterns or self.config.url_exclude_patterns:
            self._url_filter = URLFilter.from_config(self.config)
            original_count = len(urls)
            urls = self._url_filter.filter_urls(urls)
            filtered_count = original_count - len(urls)
            if filtered_count > 0:
                logger.info(f"URL过滤: 原始={original_count}, 过滤后={len(urls)}, 排除={filtered_count}")
        
        # 限制最大URL数量
        if self.config.max_urls and len(urls) > self.config.max_urls:
            urls = urls[:self.config.max_urls]
            logger.info(f"限制为 {self.config.max_urls} 个URL")
        
        self.stats.total_urls = len(urls)
        
        # 提交所有任务到线程池
        future_to_url = {}
        for i, url in enumerate(urls):
            if self._should_stop():
                logger.info(f"爬取任务被中断 (已提交 {i}/{len(urls)} 个URL)")
                break
                
            future = self.executor.submit(self._scan_single_url, url, i, len(urls))
            future_to_url[future] = (url, i)
        
        # 收集结果
        completed = 0
        for future in as_completed(future_to_url):
            if self._should_stop():
                logger.info("检测到停止信号，取消剩余任务")
                # 取消未完成的 futures
                for f in future_to_url:
                    if not f.done():
                        f.cancel()
                break
            
            url, index = future_to_url[future]
            try:
                result = future.result(timeout=self.timeout_per_url + 10)
                self._results.append(result)
                
                if result.error:
                    self.stats.failed_scans += 1
                else:
                    self.stats.successful_scans += 1
                
                self.stats.total_load_time += result.load_time
                completed += 1
                
                # 更新活动线程数
                self.stats.active_threads = sum(1 for f in future_to_url if not f.done())
                
                # 调用进度回调
                if progress_callback:
                    progress_callback(result, completed, len(urls))
                
                # 调用页面处理回调
                if page_processed_callback and not result.error:
                    try:
                        page_data = result.to_dict()
                        page_processed_callback(page_data)
                    except Exception as e:
                        logger.error(f"页面处理回调失败: {str(e)}")
                
                logger.info(f"进度: {completed}/{len(urls)} ({completed * 100 // len(urls)}%)")
                
            except Exception as e:
                logger.error(f"处理结果时出错 {url}: {str(e)}")
                self.stats.failed_scans += 1
                completed += 1
        
        self.stats.end_time = datetime.now().isoformat()
        self.stats.active_threads = 0
        
        logger.info(
            f"异步批量爬取完成: 成功={self.stats.successful_scans}, "
            f"失败={self.stats.failed_scans}, 总耗时={self.stats.total_load_time:.2f}s"
        )
        
        return self._results

    def _should_stop(self) -> bool:
        """检查是否应该停止"""
        if self._stop_flag:
            return True
        if hasattr(self, '_external_stop_flag') and self._external_stop_flag:
            return self._external_stop_flag.is_set()
        return False

    def stop(self):
        """停止爬取任务"""
        self._stop_flag = True
        logger.info("已请求停止异步批量爬取任务")

    def get_results(self) -> List[ScanResult]:
        """获取爬取结果"""
        return self._results

    def get_stats(self) -> AsyncCrawlStats:
        """获取统计信息"""
        return self.stats

    def shutdown(self):
        """关闭线程池"""
        self.executor.shutdown(wait=False)
        logger.info("异步批量爬虫线程池已关闭")
