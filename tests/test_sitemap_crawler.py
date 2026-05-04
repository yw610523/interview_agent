"""
SitemapCrawler 模块测试。
"""

import pytest
from unittest.mock import patch, Mock
from app.services.sitemap_crawler import SitemapCrawler, CrawlConfig, CrawlStats
from app.services.url_scanner import ScanResult


class TestCrawlConfig:
    """CrawlConfig 类的测试用例。"""

    def test_default_config(self):
        """测试默认配置值。"""
        config = CrawlConfig()
        assert config.timeout == 30
        assert config.max_urls is None
        assert config.delay_between_requests == 0.0
        assert config.verify_ssl is True
        assert config.follow_redirects is True

    def test_from_dict(self):
        """测试从字典创建配置。"""
        data = {
            'sitemap_url': 'https://example.com/sitemap.xml',
            'timeout': 60,
            'max_urls': 100,
        }
        config = CrawlConfig.from_dict(data)
        assert config.sitemap_url == 'https://example.com/sitemap.xml'
        assert config.timeout == 60
        assert config.max_urls == 100

    def test_to_dict(self):
        """测试将配置转换为字典。"""
        config = CrawlConfig(sitemap_url='https://example.com/sitemap.xml')
        data = config.to_dict()
        assert data['sitemap_url'] == 'https://example.com/sitemap.xml'
        assert 'timeout' in data


class TestCrawlStats:
    """CrawlStats 类的测试用例。"""

    def test_default_stats(self):
        """测试默认统计值。"""
        stats = CrawlStats()
        assert stats.total_urls == 0
        assert stats.successful_scans == 0
        assert stats.failed_scans == 0
        assert stats.total_load_time == 0.0

    def test_to_dict(self):
        """测试将统计信息转换为字典。"""
        stats = CrawlStats()
        stats.total_urls = 10
        stats.successful_scans = 8
        stats.failed_scans = 2

        data = stats.to_dict()
        assert data['total_urls'] == 10
        assert data['successful_scans'] == 8
        assert data['failed_scans'] == 2


class TestSitemapCrawler:
    """SitemapCrawler 类的测试用例。"""

    def test_init_with_config(self):
        """测试使用配置初始化爬虫。"""
        config = CrawlConfig(sitemap_url='https://example.com/sitemap.xml')
        crawler = SitemapCrawler(config=config)
        assert crawler.config.sitemap_url == 'https://example.com/sitemap.xml'

    def test_init_with_kwargs(self):
        """测试使用关键字参数初始化爬虫。"""
        crawler = SitemapCrawler(
            sitemap_url='https://example.com/sitemap.xml',
            timeout=60,
            max_urls=50,
        )
        assert crawler.config.timeout == 60
        assert crawler.config.max_urls == 50

    def test_init_without_url_raises(self):
        """测试没有 URL 时爬取会引发错误。"""
        crawler = SitemapCrawler()

        with pytest.raises(ValueError, match="sitemap_url must be provided"):
            crawler.crawl()

    @patch('app.services.sitemap_crawler.SitemapParser')
    @patch('app.services.sitemap_crawler.URLScanner')
    def test_crawl(self, mock_scanner_class, mock_parser_class):
        """测试爬取操作。"""
        # Mock parser
        mock_parser = Mock()
        mock_parser.parse.return_value = [
            'https://example.com/page1',
            'https://example.com/page2',
        ]
        mock_parser_class.return_value = mock_parser

        # Mock scanner
        mock_scanner = Mock()
        mock_result1 = ScanResult('https://example.com/page1')
        mock_result1.status_code = 200
        mock_result2 = ScanResult('https://example.com/page2')
        mock_result2.status_code = 200
        mock_scanner.scan.side_effect = [mock_result1, mock_result2]
        mock_scanner_class.return_value = mock_scanner

        crawler = SitemapCrawler(sitemap_url='https://example.com/sitemap.xml')
        results = crawler.crawl()

        assert len(results) == 2
        assert crawler.stats.total_urls == 2
        assert crawler.stats.successful_scans == 2

    @patch('app.services.sitemap_crawler.SitemapParser')
    @patch('app.services.sitemap_crawler.URLScanner')
    def test_crawl_with_max_urls(self, mock_scanner_class, mock_parser_class):
        """测试带 max_urls 限制的爬取。"""
        mock_parser = Mock()
        mock_parser.parse.return_value = [
            'https://example.com/page1',
            'https://example.com/page2',
            'https://example.com/page3',
            'https://example.com/page4',
        ]
        mock_parser_class.return_value = mock_parser

        mock_scanner = Mock()
        mock_result = ScanResult('https://example.com/page1')
        mock_result.status_code = 200
        mock_scanner.scan.return_value = mock_result
        mock_scanner_class.return_value = mock_scanner

        crawler = SitemapCrawler(
            sitemap_url='https://example.com/sitemap.xml',
            max_urls=2,
        )
        results = crawler.crawl()

        assert len(results) == 2
        assert crawler.stats.total_urls == 2

    @patch('app.services.sitemap_crawler.SitemapParser')
    @patch('app.services.sitemap_crawler.URLScanner')
    def test_crawl_with_progress_callback(self, mock_scanner_class, mock_parser_class):
        """测试带进度回调的爬取。"""
        mock_parser = Mock()
        mock_parser.parse.return_value = ['https://example.com/page1']
        mock_parser_class.return_value = mock_parser

        mock_scanner = Mock()
        mock_result = ScanResult('https://example.com/page1')
        mock_result.status_code = 200
        mock_scanner.scan.return_value = mock_result
        mock_scanner_class.return_value = mock_scanner

        callback_called = False

        def callback(result, current, total):
            nonlocal callback_called
            callback_called = True

        crawler = SitemapCrawler(sitemap_url='https://example.com/sitemap.xml')
        crawler.crawl(progress_callback=callback)

        assert callback_called is True

    def test_crawl_urls(self):
        """测试爬取指定的 URL（无需站点地图）。"""
        with patch('app.services.sitemap_crawler.URLScanner') as mock_scanner_class:
            mock_scanner = Mock()
            mock_result = ScanResult('https://example.com/page1')
            mock_result.status_code = 200
            mock_scanner.scan.return_value = mock_result
            mock_scanner_class.return_value = mock_scanner

            crawler = SitemapCrawler()
            results = crawler.crawl_urls(['https://example.com/page1'])

            assert len(results) == 1
            assert crawler.stats.total_urls == 1

    def test_get_summary(self):
        """测试获取爬取摘要。"""
        crawler = SitemapCrawler(sitemap_url='https://example.com/sitemap.xml')
        crawler.stats.total_urls = 2
        crawler.stats.successful_scans = 1
        crawler.stats.failed_scans = 1

        summary = crawler.get_summary()

        assert 'statistics' in summary
        assert 'urls_by_status' in summary
        assert 'avg_load_time' in summary