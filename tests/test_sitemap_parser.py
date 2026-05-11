"""
SitemapParser 模块测试。
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from app.services.sitemap_parser import SitemapParser


# 示例站点地图 XML 内容（保留用于兼容性测试）
SAMPLE_SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/page1</loc>
        <lastmod>2024-01-01</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>https://example.com/page2</loc>
        <lastmod>2024-01-02</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.6</priority>
    </url>
    <url>
        <loc>https://example.com/page3</loc>
    </url>
</urlset>
"""


class TestSitemapParser:
    """SitemapParser 类的测试用例。"""

    def test_init(self):
        """测试解析器初始化。"""
        parser = SitemapParser("https://example.com/sitemap.xml")
        assert parser.sitemap_url == "https://example.com/sitemap.xml"
        assert parser._urls is None
        assert parser._urls_with_metadata is None

    @patch('app.services.sitemap_parser.requests.get')
    def test_fetch_sitemap(self, mock_get):
        """测试从 URL 获取站点地图（兼容性方法）。"""
        mock_response = Mock()
        mock_response.text = SAMPLE_SITEMAP_XML
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        parser = SitemapParser("https://example.com/sitemap.xml")
        content = parser.fetch_sitemap()

        # fetch_sitemap 现在只验证可访问性，返回空字符串
        assert content == ""
        mock_get.assert_called_once_with(
            "https://example.com/sitemap.xml", timeout=30)

    @patch('app.services.sitemap_parser.sitemap_tree_for_homepage')
    def test_parse(self, mock_tree):
        """测试解析站点地图 URL。"""
        # Mock sitemap tree
        mock_page1 = Mock()
        mock_page1.url = "https://example.com/page1"
        mock_page2 = Mock()
        mock_page2.url = "https://example.com/page2"
        mock_page3 = Mock()
        mock_page3.url = "https://example.com/page3"
        
        mock_tree_instance = Mock()
        mock_tree_instance.all_pages.return_value = [mock_page1, mock_page2, mock_page3]
        mock_tree.return_value = mock_tree_instance

        parser = SitemapParser("https://example.com/sitemap.xml")
        urls = parser.parse()

        assert len(urls) == 3
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls
        assert "https://example.com/page3" in urls

    @patch('app.services.sitemap_parser.sitemap_tree_for_homepage')
    def test_parse_sitemap_index(self, mock_tree):
        """测试解析站点地图索引（自动处理嵌套）。"""
        # Mock sitemap tree with pages from multiple sitemaps
        mock_page1 = Mock()
        mock_page1.url = "https://example.com/page1"
        mock_page2 = Mock()
        mock_page2.url = "https://example.com/page2"
        
        mock_tree_instance = Mock()
        mock_tree_instance.all_pages.return_value = [mock_page1, mock_page2]
        mock_tree.return_value = mock_tree_instance

        parser = SitemapParser("https://example.com/sitemap-index.xml")
        urls = parser.parse()

        assert len(urls) == 2
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls

    @patch('app.services.sitemap_parser.sitemap_tree_for_homepage')
    def test_get_urls_with_metadata(self, mock_tree):
        """测试解析带元数据的 URL。"""
        # Mock sitemap tree
        mock_page1 = Mock()
        mock_page1.url = "https://example.com/page1"
        mock_page2 = Mock()
        mock_page2.url = "https://example.com/page2"
        
        mock_tree_instance = Mock()
        mock_tree_instance.all_pages.return_value = [mock_page1, mock_page2]
        mock_tree.return_value = mock_tree_instance

        parser = SitemapParser("https://example.com/sitemap.xml")
        urls_data = parser.get_urls_with_metadata()

        assert len(urls_data) == 2
        
        # Check URLs are present (order may vary due to set deduplication)
        urls = [item['url'] for item in urls_data]
        assert 'https://example.com/page1' in urls
        assert 'https://example.com/page2' in urls



    def test_validate_url(self):
        """测试 URL 验证。"""
        assert SitemapParser.validate_url("https://example.com/page") is True
        assert SitemapParser.validate_url("http://example.com") is True
        assert SitemapParser.validate_url("ftp://example.com/file") is True
        assert SitemapParser.validate_url("not-a-url") is False
        assert SitemapParser.validate_url("") is False
        assert SitemapParser.validate_url("https://") is False
