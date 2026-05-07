"""
爬虫配置模块

此模块为站点地图爬虫提供配置管理功能。
"""

import json
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any


@dataclass
class CrawlerConfig:
    """
    站点地图爬虫的配置类。

    属性:
        sitemap_url: 要爬取的站点地图 URL
        timeout: 请求超时时间（秒）
        max_urls: 最大爬取 URL 数量（None 表示无限制）
        delay_between_requests: 请求之间的延迟（秒）
        output_dir: 爬取结果保存目录
        user_agent: 自定义 User-Agent 字符串
        verify_ssl: 是否验证 SSL 证书
        follow_redirects: 是否跟随重定向
        max_content_length: 最大下载内容长度（字节）
        check_robots_txt: 是否检查 robots.txt
        save_results: 是否保存结果到文件
        verbose: 是否打印详细输出
        url_include_patterns: URL包含模式列表（正则表达式），只爬取匹配的URL
        url_exclude_patterns: URL排除模式列表（正则表达式），不爬取匹配的URL
    """
    sitemap_url: str = ""
    sitemap_path: str = ""
    robots_path: str = ""
    timeout: int = 30
    max_urls: Optional[int] = None
    delay_between_requests: float = 0.5
    output_dir: str = "./crawl_results"
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    verify_ssl: bool = True
    follow_redirects: bool = True
    max_content_length: int = 10 * 1024 * 1024  # 10MB
    check_robots_txt: bool = True
    save_results: bool = True
    verbose: bool = True
    url_include_patterns: list = field(default_factory=list)
    url_exclude_patterns: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CrawlerConfig':
        """从字典创建配置。"""
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    @classmethod
    def from_json(cls, filepath: str) -> 'CrawlerConfig':
        """从 JSON 文件加载配置。"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_json(self, filepath: str) -> None:
        """将配置保存到 JSON 文件。"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)

    def update(self, **kwargs) -> 'CrawlerConfig':
        """用新值更新配置并返回自身。"""
        valid_keys = set(self.__dataclass_fields__.keys())
        for key, value in kwargs.items():
            if key in valid_keys:
                setattr(self, key, value)
        return self


# 默认配置实例
default_config = CrawlerConfig()


def get_config_from_env() -> CrawlerConfig:
    """
    从环境变量加载配置。

    返回:
        包含环境变量的值的 CrawlerConfig 实例
    """
    import os
    import json
    from dotenv import load_dotenv
    import logging

    load_dotenv()

    config = CrawlerConfig()

    if sitemap_url := os.getenv('SITEMAP_URL'):
        config.sitemap_url = sitemap_url

    if timeout := os.getenv('CRAWLER_TIMEOUT'):
        config.timeout = int(timeout)

    if max_urls := os.getenv('CRAWLER_MAX_URLS'):
        config.max_urls = int(max_urls)

    if delay := os.getenv('CRAWLER_DELAY'):
        config.delay_between_requests = float(delay)

    if output_dir := os.getenv('CRAWLER_OUTPUT_DIR'):
        config.output_dir = output_dir

    if user_agent := os.getenv('CRAWLER_USER_AGENT'):
        config.user_agent = user_agent

    # 从环境变量读取URL过滤规则
    if include_patterns := os.getenv('CRAWLER_URL_INCLUDE_PATTERNS'):
        try:
            config.url_include_patterns = json.loads(include_patterns)
        except json.JSONDecodeError as e:
            logging.warning(f"解析CRAWLER_URL_INCLUDE_PATTERNS失败: {str(e)}")

    if exclude_patterns := os.getenv('CRAWLER_URL_EXCLUDE_PATTERNS'):
        try:
            config.url_exclude_patterns = json.loads(exclude_patterns)
        except json.JSONDecodeError as e:
            logging.warning(f"解析CRAWLER_URL_EXCLUDE_PATTERNS失败: {str(e)}")

    return config


def get_scheduler_config() -> dict:
    """
    从环境变量加载定时任务配置。

    返回:
        包含定时任务配置的字典，包含 hour 和 minute 字段
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    return {
        'hour': int(os.getenv('SCHEDULER_HOUR', 22)),
        'minute': int(os.getenv('SCHEDULER_MINUTE', 0))
    }
