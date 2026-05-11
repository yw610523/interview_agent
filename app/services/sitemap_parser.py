"""
Sitemap 解析器模块

此模块提供解析 XML 站点地图并提取 URL 的功能。
使用 ultimate-sitemap-parser 库自动处理嵌套索引和命名空间。
"""

import logging
from typing import List, Optional
from urllib.parse import urlparse

import requests
from usp.tree import sitemap_tree_for_homepage

logger = logging.getLogger(__name__)


class SitemapParser:
    """XML 站点地图解析器（基于 ultimate-sitemap-parser）。"""

    def __init__(self, sitemap_url: str):
        """
        初始化站点地图解析器。

        参数:
            sitemap_url: 站点地图 XML 文件的 URL
        """
        self.sitemap_url = sitemap_url
        self._urls: Optional[List[str]] = None
        self._urls_with_metadata: Optional[List[dict]] = None

    def fetch_sitemap(self) -> str:
        """
        从 URL 获取站点地图 XML 内容（兼容性方法）。

        注意：ultimate-sitemap-parser 会在 parse() 时自动获取，
        此方法仅用于保持 API 兼容性。

        返回:
            空字符串（实际获取在 parse() 中进行）

        抛出:
            requests.RequestException: 请求失败时
        """
        # 验证 URL 可访问性
        response = requests.get(self.sitemap_url, timeout=30)
        response.raise_for_status()
        return ""

    def parse(self) -> List[str]:
        """
        解析站点地图并提取所有 URL。
        支持递归解析 sitemap 索引页（由 ultimate-sitemap-parser 自动处理）。

        返回:
            站点地图中找到的 URL 列表

        抛出:
            Exception: 解析失败时
        """
        if self._urls is not None:
            return self._urls

        try:
            logger.info(f"使用 ultimate-sitemap-parser 解析: {self.sitemap_url}")

            # 从 sitemap URL 提取域名
            parsed = urlparse(self.sitemap_url)
            homepage_url = f"{parsed.scheme}://{parsed.netloc}"

            # 构建 sitemap tree（自动处理索引页和命名空间）
            tree = sitemap_tree_for_homepage(homepage_url)

            # 提取所有页面 URL
            all_urls = []
            for page in tree.all_pages():
                url = page.url
                if url:
                    all_urls.append(url)

            # 去重
            self._urls = list(set(all_urls))

            logger.info(f"解析完成，共找到 {len(self._urls)} 个URL")
            if self._urls:
                logger.info(f"示例URL: {self._urls[:5]}")

            return self._urls

        except Exception as e:
            logger.error(f"Sitemap 解析失败: {str(e)}")
            logger.error(f"尝试解析的 URL: {self.sitemap_url}")
            raise

    def get_urls_with_metadata(self) -> List[dict]:
        """
        解析站点地图并提取带元数据的 URL。

        注意：ultimate-sitemap-parser 不直接支持元数据提取，
        此方法返回基本 URL 信息以保持 API 兼容性。

        返回:
            包含 url 的字典列表
        """
        if self._urls_with_metadata is not None:
            return self._urls_with_metadata

        # 如果没有解析过，先解析
        if self._urls is None:
            self.parse()

        # 构建简化的元数据结构（仅包含 URL）
        self._urls_with_metadata = [{'url': url} for url in (self._urls or [])]

        return self._urls_with_metadata

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        验证字符串是否为有效 URL。

        参数:
            url: 要验证的 URL 字符串

        返回:
            如果是有效 URL 返回 True，否则返回 False
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
