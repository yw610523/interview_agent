"""
SitemapParser 模块测试。
"""

import pytest
from unittest.mock import patch, Mock
from app.services.sitemap_parser import SitemapParser


# 示例站点地图 XML 内容
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

# 示例站点地图索引 XML 内容
SAMPLE_SITEMAP_INDEX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <sitemap>
        <loc>https://example.com/sitemap1.xml</loc>
        <lastmod>2024-01-01</lastmod>
    </sitemap>
    <sitemap>
        <loc>https://example.com/sitemap2.xml</loc>
        <lastmod>2024-01-02</lastmod>
    </sitemap>
</sitemapindex>
"""


class TestSitemapParser:
    """SitemapParser 类的测试用例。"""

    def test_init(self):
        """测试解析器初始化。"""
        parser = SitemapParser("https://example.com/sitemap.xml")
        assert parser.sitemap_url == "https://example.com/sitemap.xml"
        assert parser._xml_content is None
        assert parser._root is None

    @patch('app.services.sitemap_parser.requests.get')
    def test_fetch_sitemap(self, mock_get):
        """测试从 URL 获取站点地图。"""
        mock_response = Mock()
        mock_response.text = SAMPLE_SITEMAP_XML
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        parser = SitemapParser("https://example.com/sitemap.xml")
        content = parser.fetch_sitemap()

        assert content == SAMPLE_SITEMAP_XML
        assert parser._xml_content == SAMPLE_SITEMAP_XML
        mock_get.assert_called_once_with(
            "https://example.com/sitemap.xml", timeout=30)

    @patch('app.services.sitemap_parser.requests.get')
    def test_parse(self, mock_get):
        """测试解析站点地图 URL。"""
        mock_response = Mock()
        mock_response.text = SAMPLE_SITEMAP_XML
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        parser = SitemapParser("https://example.com/sitemap.xml")
        parser.fetch_sitemap()
        urls = parser.parse()

        assert len(urls) == 3
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls
        assert "https://example.com/page3" in urls

    @patch('app.services.sitemap_parser.requests.get')
    def test_parse_sitemap_index(self, mock_get):
        """测试解析站点地图索引。"""
        mock_response = Mock()
        mock_response.text = SAMPLE_SITEMAP_INDEX_XML
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        parser = SitemapParser("https://example.com/sitemap-index.xml")
        parser.fetch_sitemap()
        urls = parser.parse()

        assert len(urls) == 2
        assert "https://example.com/sitemap1.xml" in urls
        assert "https://example.com/sitemap2.xml" in urls

    @patch('app.services.sitemap_parser.requests.get')
    def test_get_urls_with_metadata(self, mock_get):
        """测试解析带元数据的 URL。"""
        mock_response = Mock()
        mock_response.text = SAMPLE_SITEMAP_XML
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        parser = SitemapParser("https://example.com/sitemap.xml")
        parser.fetch_sitemap()
        urls_data = parser.get_urls_with_metadata()

        assert len(urls_data) == 3

        # Check first URL with full metadata
        assert urls_data[0]['url'] == 'https://example.com/page1'
        assert urls_data[0]['lastmod'] == '2024-01-01'
        assert urls_data[0]['changefreq'] == 'daily'
        assert urls_data[0]['priority'] == '0.8'

        # Check third URL without metadata
        assert urls_data[2]['url'] == 'https://example.com/page3'
        assert 'lastmod' not in urls_data[2]

    def test_parse_without_fetch(self):
        """测试未先获取就解析会引发错误。"""
        parser = SitemapParser("https://example.com/sitemap.xml")

        with pytest.raises(ValueError, match="Sitemap not fetched"):
            parser.parse()

    def test_is_sitemap_index(self):
        """测试站点地图索引检测。"""
        assert SitemapParser.is_sitemap_index(SAMPLE_SITEMAP_INDEX_XML) is True
        assert SitemapParser.is_sitemap_index(SAMPLE_SITEMAP_XML) is False
        assert SitemapParser.is_sitemap_index("invalid xml") is False

    def test_validate_url(self):
        """测试 URL 验证。"""
        assert SitemapParser.validate_url("https://example.com/page") is True
        assert SitemapParser.validate_url("http://example.com") is True
        assert SitemapParser.validate_url("ftp://example.com/file") is True
        assert SitemapParser.validate_url("not-a-url") is False
        assert SitemapParser.validate_url("") is False
        assert SitemapParser.validate_url("https://") is False
