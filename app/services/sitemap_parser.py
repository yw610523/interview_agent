"""
Sitemap 解析器模块

此模块提供解析 XML 站点地图并提取 URL 的功能。
支持标准站点地图 XML 格式和站点地图索引文件。
"""

from typing import List, Optional
from urllib.parse import urlparse

import requests
from lxml import etree


class SitemapParser:
    """XML 站点地图解析器。"""

    # XML namespaces commonly used in sitemaps
    NAMESPACES = {
        'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
        'xhtml': 'http://www.w3.org/1999/xhtml',
        'image': 'http://www.google.com/schemas/sitemap-image/1.1',
        'video': 'http://www.google.com/schemas/sitemap-video/1.1',
    }

    def __init__(self, sitemap_url: str):
        """
        初始化站点地图解析器。

        参数:
            sitemap_url: 站点地图 XML 文件的 URL
        """
        self.sitemap_url = sitemap_url
        self._xml_content: Optional[str] = None
        self._root: Optional[etree.Element] = None

    def fetch_sitemap(self) -> str:
        """
        从 URL 获取站点地图 XML 内容。

        返回:
            XML 内容字符串

        抛出:
            requests.RequestException: 请求失败时
        """
        response = requests.get(self.sitemap_url, timeout=30)
        response.raise_for_status()
        self._xml_content = response.text
        return self._xml_content

    def parse(self) -> List[str]:
        """
        解析站点地图并提取所有 URL。

        返回:
            站点地图中找到的 URL 列表

        抛出:
            etree.XMLSyntaxError: XML 格式错误时
            ValueError: 站点地图尚未获取时
        """
        if self._xml_content is None:
            raise ValueError("Sitemap not fetched. Call fetch_sitemap() first.")

        self._root = etree.fromstring(self._xml_content.encode('utf-8'))
        urls = []

        # Check if this is a sitemap index (contains <sitemap> elements)
        is_index = self._root.find('.//sitemap:sitemap', namespaces=self.NAMESPACES) is not None

        if is_index:
            # Parse sitemap index - extract child sitemap URLs
            urls = self._parse_sitemap_index()
        else:
            # Parse regular sitemap - extract page URLs
            urls = self._parse_url_set()

        return urls

    def _parse_sitemap_index(self) -> List[str]:
        """
        解析站点地图索引文件并返回子站点地图 URL。

        返回:
            子站点地图 URL 列表
        """
        urls = []
        for sitemap_elem in self._root.findall('.//sitemap:sitemap', namespaces=self.NAMESPACES):
            loc_elem = sitemap_elem.find('sitemap:loc', namespaces=self.NAMESPACES)
            if loc_elem is not None and loc_elem.text:
                urls.append(loc_elem.text.strip())
        return urls

    def _parse_url_set(self) -> List[str]:
        """
        解析 URL 集合（常规站点地图）并返回页面 URL。

        返回:
            页面 URL 列表
        """
        urls = []
        for url_elem in self._root.findall('.//sitemap:url', namespaces=self.NAMESPACES):
            loc_elem = url_elem.find('sitemap:loc', namespaces=self.NAMESPACES)
            if loc_elem is not None and loc_elem.text:
                urls.append(loc_elem.text.strip())
        return urls

    def get_urls_with_metadata(self) -> List[dict]:
        """
        解析站点地图并提取带元数据的 URL。

        返回:
            包含 url、lastmod、changefreq 和 priority 的字典列表
        """
        if self._xml_content is None:
            raise ValueError("Sitemap not fetched. Call fetch_sitemap() first.")

        if self._root is None:
            self._root = etree.fromstring(self._xml_content.encode('utf-8'))

        urls_data = []
        for url_elem in self._root.findall('.//sitemap:url', namespaces=self.NAMESPACES):
            url_data = {}

            loc_elem = url_elem.find('sitemap:loc', namespaces=self.NAMESPACES)
            if loc_elem is not None and loc_elem.text:
                url_data['url'] = loc_elem.text.strip()

            lastmod_elem = url_elem.find('sitemap:lastmod', namespaces=self.NAMESPACES)
            if lastmod_elem is not None and lastmod_elem.text:
                url_data['lastmod'] = lastmod_elem.text.strip()

            changefreq_elem = url_elem.find('sitemap:changefreq', namespaces=self.NAMESPACES)
            if changefreq_elem is not None and changefreq_elem.text:
                url_data['changefreq'] = changefreq_elem.text.strip()

            priority_elem = url_elem.find('sitemap:priority', namespaces=self.NAMESPACES)
            if priority_elem is not None and priority_elem.text:
                url_data['priority'] = priority_elem.text.strip()

            if url_data:
                urls_data.append(url_data)

        return urls_data

    @staticmethod
    def is_sitemap_index(xml_content: str) -> bool:
        """
        检查 XML 内容是否为站点地图索引。

        参数:
            xml_content: XML 内容字符串

        返回:
            如果是站点地图索引返回 True，否则返回 False
        """
        try:
            root = etree.fromstring(xml_content.encode('utf-8'))
            return root.find('.//sitemap:sitemap', namespaces=SitemapParser.NAMESPACES) is not None
        except etree.XMLSyntaxError:
            return False

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
