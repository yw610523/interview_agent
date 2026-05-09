"""
爬虫配置模块

此模块为站点地图爬虫提供配置管理功能。
"""

import json
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class CrawlerConfig:
    """
    站点地图爬虫的配置类。

    属性:
        sitemap_url: 要爬取的站点地图 URL 或域名
        root_url: 网站根路径前缀（如 /blog），用于拼接 sitemap 和 robots.txt
        sitemap_path: sitemap 文件路径（当 sitemap_url 为域名时使用）
        robots_path: robots.txt 路径
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
    root_url: str = ""  # 网站根路径前缀，如 /blog
    sitemap_path: str = "/sitemap.xml"
    robots_path: str = "/robots.txt"
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

    # Firecrawl MCP 配置
    use_firecrawl: bool = False  # 是否启用 Firecrawl（详细配置在 firecrawl.yaml 中）

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
        """将配置保存到 JSON 文件（已废弃，请使用 to_yaml）。"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_yaml(cls, filepath: str) -> 'CrawlerConfig':
        """从 YAML 文件加载配置。"""
        try:
            import yaml
        except ImportError:
            raise ImportError("请安装 pyyaml: pip install pyyaml")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    def to_yaml(self, filepath: str) -> None:
        """将配置保存到 YAML 文件。"""
        try:
            import yaml
        except ImportError:
            raise ImportError("请安装 pyyaml: pip install pyyaml")

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True)

    def update(self, **kwargs) -> 'CrawlerConfig':
        """用新值更新配置并返回自身。"""
        valid_keys = set(self.__dataclass_fields__.keys())
        for key, value in kwargs.items():
            if key in valid_keys:
                setattr(self, key, value)
        return self


# 默认配置实例
default_config = CrawlerConfig()


def load_crawler_config(config_path: Optional[str] = None) -> CrawlerConfig:
    """
    加载爬虫配置，优先使用 config_manager（支持多文件模式），兼容旧的文件路径。

    Args:
        config_path: 配置文件路径，如果为 None 则使用默认路径

    Returns:
        CrawlerConfig 实例
    """
    # 如果指定了自定义路径，使用原有逻辑
    if config_path:
        path = Path(config_path)
        if path.suffix in ('.yaml', '.yml'):
            return CrawlerConfig.from_yaml(str(path))
        elif path.suffix == '.json':
            return CrawlerConfig.from_json(str(path))
        else:
            try:
                return CrawlerConfig.from_yaml(str(path))
            except Exception:
                return CrawlerConfig.from_json(str(path))

    # 未指定路径时，使用 config_manager
    from app.config.config_manager import config_manager
    crawler_data = config_manager.get_config('crawler')
    if crawler_data:
        return CrawlerConfig.from_dict(crawler_data)

    # 如果没有配置，返回默认配置
    return CrawlerConfig()


def get_scheduler_config() -> dict:
    """
    从 config_manager 加载定时任务配置。

    返回:
        包含定时任务配置的字典，包含 hour 和 minute 字段
    """
    from app.config.config_manager import config_manager

    # 从 config_manager 读取
    scheduler_config = config_manager.get_config('crawler').get('scheduler', {})

    return {
        'hour': scheduler_config.get('hour', 22),
        'minute': scheduler_config.get('minute', 0)
    }
