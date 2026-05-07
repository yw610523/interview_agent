"""
URLScanner 模块测试。
"""

from unittest.mock import patch, Mock

from app.services.url_scanner import URLScanner, ScanResult


# 测试用示例 HTML 内容
SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <meta name="description" content="This is a test page">
    <meta name="keywords" content="test, page, example">
    <link rel="stylesheet" href="/styles/main.css">
    <script src="/scripts/app.js"></script>
</head>
<body>
    <h1>Main Heading</h1>
    <h2>Sub Heading</h2>
    <p>This is a test paragraph with some content.</p>
    <a href="/internal-page">Internal Link</a>
    <a href="https://external.com/page">External Link</a>
    <img src="/images/logo.png" alt="Logo">
</body>
</html>
"""


class TestScanResult:
    """ScanResult 类的测试用例。"""

    def test_init(self):
        """测试 ScanResult 初始化。"""
        result = ScanResult("https://example.com/page")
        assert result.url == "https://example.com/page"
        assert result.status_code is None
        assert result.title is None
        assert result.error is None

    def test_to_dict(self):
        """测试将 ScanResult 转换为字典。"""
        result = ScanResult("https://example.com/page")
        result.status_code = 200
        result.title = "Test Page"

        data = result.to_dict()
        assert data['url'] == "https://example.com/page"
        assert data['status_code'] == 200
        assert data['title'] == "Test Page"


class TestURLScanner:
    """URLScanner 类的测试用例。"""

    def test_init(self):
        """测试扫描器初始化。"""
        scanner = URLScanner(
            timeout=10,
            follow_redirects=False,
            verify_ssl=False,
        )
        assert scanner.timeout == 10
        assert scanner.follow_redirects is False
        assert scanner.verify_ssl is False

    @patch('app.services.url_scanner.requests.Session')
    def test_scan_success(self, mock_session_class):
        """测试成功的 URL 扫描。"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.text = SAMPLE_HTML
        mock_session.get.return_value = mock_response

        scanner = URLScanner()
        result = scanner.scan("https://example.com/page")

        assert result.status_code == 200
        assert result.content_type == 'text/html'
        assert result.title == "Test Page"
        assert result.meta_description == "This is a test page"
        assert result.error is None

    @patch('app.services.url_scanner.requests.Session')
    def test_scan_timeout(self, mock_session_class):
        """测试超时错误的扫描。"""
        import requests
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = requests.exceptions.Timeout()

        scanner = URLScanner(timeout=5)
        result = scanner.scan("https://example.com/page")

        assert result.error is not None
        assert "timed out" in result.error.lower()

    @patch('app.services.url_scanner.requests.Session')
    def test_scan_extract_links(self, mock_session_class):
        """测试从 HTML 提取链接。"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.text = SAMPLE_HTML
        mock_session.get.return_value = mock_response

        scanner = URLScanner()
        result = scanner.scan("https://example.com/page")

        assert len(result.links['internal']) >= 1
        assert len(result.links['external']) >= 1
        assert len(result.links['images']) >= 1

    @patch('app.services.url_scanner.requests.Session')
    def test_scan_extract_headings(self, mock_session_class):
        """测试从 HTML 提取标题。"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.text = SAMPLE_HTML
        mock_session.get.return_value = mock_response

        scanner = URLScanner()
        result = scanner.scan("https://example.com/page")

        assert 'h1' in result.headings
        assert 'h2' in result.headings
        assert "Main Heading" in result.headings['h1']

    @patch('app.services.url_scanner.requests.Session')
    def test_scan_batch(self, mock_session_class):
        """测试批量扫描多个 URL。"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.text = SAMPLE_HTML
        mock_session.get.return_value = mock_response

        scanner = URLScanner()
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
        ]

        callback_called = False

        def callback(result, current, total):
            nonlocal callback_called
            callback_called = True

        results = scanner.scan_batch(urls, callback=callback)

        assert len(results) == 2
        assert callback_called is True

    @patch('app.services.url_scanner.requests.Session')
    def test_check_robots_txt(self, mock_session_class):
        """测试 robots.txt 获取。"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nDisallow: /admin"
        mock_session.get.return_value = mock_response

        scanner = URLScanner()
        robots_txt = scanner.check_robots_txt("https://example.com")

        assert robots_txt is not None
        assert "User-agent" in robots_txt

    def test_get_sitemap_urls_from_robots(self):
        """测试从 robots.txt 提取站点地图 URL。"""
        robots_txt = """User-agent: *
Disallow: /admin
Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap-news.xml
"""
        scanner = URLScanner()
        sitemaps = scanner.get_sitemap_urls_from_robots(robots_txt)

        assert len(sitemaps) == 2
        assert "https://example.com/sitemap.xml" in sitemaps
        assert "https://example.com/sitemap-news.xml" in sitemaps
