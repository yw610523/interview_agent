"""
URL过滤器模块

用于根据include/exclude规则过滤URL
"""

import logging
import re
from dataclasses import dataclass
from typing import List
from urllib.parse import unquote

logger = logging.getLogger(__name__)


@dataclass
class URLFilterConfig:
    """
    URL过滤器配置

    属性:
        include_patterns: URL包含模式列表（正则表达式），只爬取匹配的URL
        exclude_patterns: URL排除模式列表（正则表达式），不爬取匹配的URL
    """
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None

    def __post_init__(self):
        if self.include_patterns is None:
            self.include_patterns = []
        if self.exclude_patterns is None:
            self.exclude_patterns = []


class URLFilter:
    """
    URL过滤器

    使用规则:
    1. 如果定义了include_patterns，URL必须匹配至少一个include模式
    2. 如果URL匹配任何exclude模式，则被排除
    3. 如果没有定义include_patterns，默认允许所有URL（除非被exclude排除）
    """

    def __init__(self, config: URLFilterConfig = None):
        """
        初始化URL过滤器

        参数:
            config: URL过滤器配置
        """
        if config is None:
            config = URLFilterConfig()

        self.config = config
        self.compiled_include = self._compile_patterns(config.include_patterns)
        self.compiled_exclude = self._compile_patterns(config.exclude_patterns)

        logger.info(
            f"URL过滤器初始化: "
            f"include_patterns={len(config.include_patterns)}, "
            f"exclude_patterns={len(config.exclude_patterns)}"
        )

    def _compile_patterns(self, patterns: List[str]) -> List[re.Pattern]:
        r"""
        编译正则表达式模式
        
        支持两种格式:
        1. 路径前缀匹配(推荐): /ai, /ai/, /ai/* 都表示匹配 /ai 路径下的所有URL
        2. 通配符模式: *.pdf, /docs/**/*.html
        3. 正则表达式: \/ai\/.*, .*\.pdf$

        参数:
            patterns: 正则表达式字符串列表

        返回:
            编译后的正则表达式对象列表
        """
        compiled = []
        for pattern in patterns:
            try:
                # 保持原始格式（编码），与 sitemap URL 格式一致
                # 这样可以直接匹配，无需解码，保证与缓存 key 逻辑一致
                
                # 检测是否为简单的路径前缀(如 /ai, /ai/, /docs)
                # 特征: 以 / 开头,不包含通配符和复杂正则符号
                is_simple_path = (
                        pattern.startswith('/') and
                        '*' not in pattern and
                        not any(c in pattern for c in ['^', '$', '+', '?', '[', ']', '(', ')', '{', '}', '|'])
                )

                if is_simple_path:
                    # 路径前缀匹配: /ai 或 /ai/ 都转换为 /ai(/.*)?$
                    # 去除末尾的 /
                    clean_path = pattern.rstrip('/')
                    # 构建正则: 匹配URL中包含 /ai 后面跟 / 任意内容,或者就是 /ai 结尾
                    # 使用 (?=/|\?|#|$) 确保匹配的是完整路径段
                    regex_pattern = f"{clean_path}(/|\\?|#|$)"
                    compiled_pattern = re.compile(regex_pattern, re.IGNORECASE)
                    logger.debug(f"路径前缀转换: {pattern} -> {regex_pattern}")
                elif '*' in pattern and not any(
                        c in pattern for c in ['^', '$', '+', '?', '[', ']', '(', ')', '{', '}', '|', '\\']):
                    # 通配符模式: 将 * 转换为 .*
                    # 特殊处理: 如果模式以 /* 结尾(如 /ai/*),则也匹配不带子路径的情况
                    regex_pattern = re.escape(pattern)
                    regex_pattern = regex_pattern.replace(r'\*', '.*')

                    # 如果原始模式是 /xxx/* 形式，让它也能匹配 /xxx 本身
                    if pattern.endswith('/*'):
                        base_path = pattern[:-2]  # 去掉 /*
                        # 构建: /ai(/.*)?$ 的形式
                        regex_pattern = f"{base_path}(/|\\?|#|$)"

                    compiled_pattern = re.compile(regex_pattern, re.IGNORECASE)
                    logger.debug(f"通配符模式转换: {pattern} -> {regex_pattern}")
                else:
                    # 直接使用正则表达式
                    compiled_pattern = re.compile(pattern, re.IGNORECASE)
                    logger.debug(f"编译正则表达式成功: {pattern}")

                compiled.append(compiled_pattern)
            except re.error as e:
                logger.error(f"编译正则表达式失败: {pattern}, 错误: {str(e)}")
        return compiled

    def should_crawl(self, url: str) -> bool:
        """
        判断是否应该爬取指定的URL

        参数:
            url: 要检查的URL

        返回:
            True表示应该爬取，False表示应该跳过
        """
        # 使用原始 URL 格式（编码），与 include_patterns 保持一致
        # 避免解码带来的格式不一致问题
        
        # 首先检查exclude规则
        if self.compiled_exclude:
            for pattern in self.compiled_exclude:
                if pattern.search(url):
                    logger.debug(f"URL被exclude规则排除: {url}, 匹配模式: {pattern.pattern}")
                    return False

        # 然后检查include规则
        if self.compiled_include:
            for pattern in self.compiled_include:
                if pattern.search(url):
                    logger.debug(f"URL匹配include规则: {url}, 匹配模式: {pattern.pattern}")
                    return True
            # 如果有include规则但没有匹配，返回False
            logger.debug(f"URL未匹配任何include规则: {url}")
            return False

        # 如果没有include规则，默认允许
        logger.debug(f"URL通过过滤（无include限制）: {url}")
        return True

    def filter_urls(self, urls: List[str]) -> List[str]:
        """
        过滤URL列表

        参数:
            urls: URL列表

        返回:
            过滤后的URL列表
        """
        filtered = [url for url in urls if self.should_crawl(url)]

        logger.info(
            f"URL过滤完成: 原始={len(urls)}, 过滤后={len(filtered)}, 排除={len(urls) - len(filtered)}"
        )

        return filtered

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'URLFilter':
        """
        从字典创建URL过滤器

        参数:
            config_dict: 配置字典，包含include_patterns和exclude_patterns

        返回:
            URLFilter实例
        """
        config = URLFilterConfig(
            include_patterns=config_dict.get('include_patterns', []),
            exclude_patterns=config_dict.get('exclude_patterns', [])
        )
        return cls(config)

    @classmethod
    def from_config(cls, crawler_config) -> 'URLFilter':
        """
        从爬虫配置创建URL过滤器

        参数:
            crawler_config: CrawlerConfig实例

        返回:
            URLFilter实例
        """
        config = URLFilterConfig(
            include_patterns=getattr(crawler_config, 'url_include_patterns', []),
            exclude_patterns=getattr(crawler_config, 'url_exclude_patterns', [])
        )
        return cls(config)
