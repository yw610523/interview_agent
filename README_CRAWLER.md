# Sitemap 爬虫

一个基于 Python 的网络爬虫，用于解析 XML 站点地图并扫描每个 URL 以提取内容、元数据和链接。

## 功能特性

- **站点地图解析**: 支持标准站点地图 XML 和站点地图索引文件
- **URL 扫描**: 提取内容、元数据、标题、链接、图片、脚本和样式表
- **可配置**: 通过 CLI 参数、JSON 配置文件或环境变量进行灵活配置
- **进度跟踪**: 实时进度回调和统计信息
- **输出**: 将结果保存到 JSON 文件以供进一步分析
- **Robots.txt 支持**: 自动检查 robots.txt 中的站点地图 URL

## 安装

1. 安装依赖项：
   ```bash
   pip install -r requirements.txt
   ```

2. 爬虫需要以下包（已添加到 requirements.txt）：
   - `requests` - HTTP 请求
   - `beautifulsoup4` - HTML 解析
   - `lxml` - XML 解析

## 使用方法

### 命令行界面

```bash
# 基本用法
python -m app.main_crawler --sitemap-url https://example.com/sitemap.xml

# 带选项
python -m app.main_crawler \
    --sitemap-url https://example.com/sitemap.xml \
    --max-urls 100 \
    --timeout 60 \
    --delay 1.0 \
    --output-dir ./results

# 使用配置文件
python -m app.main_crawler --config app/config/crawler_config.json
```

### CLI 选项

| 选项 | 描述 | 默认值 |
|--------|-------------|---------|
| `--sitemap-url, -u` | 要爬取的站点地图 URL | 必填 |
| `--config, -c` | JSON 配置文件路径 | - |
| `--timeout, -t` | 请求超时时间（秒） | 30 |
| `--max-urls, -m` | 最大爬取 URL 数量 | 无限制 |
| `--delay, -d` | 请求间隔时间（秒） | 0.5 |
| `--no-ssl-verify` | 禁用 SSL 证书验证 | False |
| `--no-follow-redirects` | 不跟随重定向 | False |
| `--output-dir, -o` | 结果保存目录 | ./crawl_results |
| `--no-save` | 不保存结果到文件 | False |
| `--quiet, -q` | 禁用详细输出 | False |
| `--verbose, -v` | 启用调试日志 | False |

### Python API

```python
from app.services.sitemap_crawler import SitemapCrawler, CrawlConfig

# 使用配置对象
config = CrawlConfig(
    sitemap_url="https://example.com/sitemap.xml",
    timeout=30,
    max_urls=100,
    delay_between_requests=0.5,
    output_dir="./crawl_results",
)

crawler = SitemapCrawler(config=config)
results = crawler.crawl()

# 打印摘要
crawler.print_report()

# 获取摘要字典
summary = crawler.get_summary()

# 保存结果
crawler.save_results()
```

### 使用独立组件

```python
from app.services.sitemap_parser import SitemapParser
from app.services.url_scanner import URLScanner

# 解析站点地图
parser = SitemapParser("https://example.com/sitemap.xml")
parser.fetch_sitemap()
urls = parser.parse()

# 扫描单个 URL
scanner = URLScanner(timeout=30)
for url in urls:
    result = scanner.scan(url)
    print(f"URL: {result.url}")
    print(f"状态: {result.status_code}")
    print(f"标题: {result.title}")
    print(f"链接: {len(result.links['internal'])} 内部链接, {len(result.links['external'])} 外部链接")
```

## 配置文件
# Sitemap 爬虫

一个基于 Python 的网络爬虫，用于解析 XML 站点地图并扫描每个 URL 以提取内容、元数据和链接。

## 功能特性

- **站点地图解析**: 支持标准站点地图 XML 和站点地图索引文件
- **URL 扫描**: 提取内容、元数据、标题、链接、图片、脚本和样式表
- **可配置**: 通过 CLI 参数、JSON 配置文件或环境变量进行灵活配置
- **进度跟踪**: 实时进度回调和统计信息
- **输出**: 将结果保存到 JSON 文件以供进一步分析
- **Robots.txt 支持**: 自动检查 robots.txt 中的站点地图 URL

## 安装

1. 安装依赖项：
   ```bash
   pip install -r requirements.txt
   ```

2. 爬虫需要以下包（已添加到 requirements.txt）：
   - `requests` - HTTP 请求
   - `beautifulsoup4` - HTML 解析
   - `lxml` - XML 解析

## 使用方法

### 命令行界面

```bash
# 基本用法
python -m app.main_crawler --sitemap-url https://example.com/sitemap.xml

# 带选项
python -m app.main_crawler \
    --sitemap-url https://example.com/sitemap.xml \
    --max-urls 100 \
    --timeout 60 \
    --delay 1.0 \
    --output-dir ./results

# 使用配置文件
python -m app.main_crawler --config app/config/crawler_config.json
```

### CLI 选项

| 选项 | 描述 | 默认值 |
|--------|-------------|---------|
| `--sitemap-url, -u` | 要爬取的站点地图 URL | 必填 |
| `--config, -c` | JSON 配置文件路径 | - |
| `--timeout, -t` | 请求超时时间（秒） | 30 |
| `--max-urls, -m` | 最大爬取 URL 数量 | 无限制 |
| `--delay, -d` | 请求间隔时间（秒） | 0.5 |
| `--no-ssl-verify` | 禁用 SSL 证书验证 | False |
| `--no-follow-redirects` | 不跟随重定向 | False |
| `--output-dir, -o` | 结果保存目录 | ./crawl_results |
| `--no-save` | 不保存结果到文件 | False |
| `--quiet, -q` | 禁用详细输出 | False |
| `--verbose, -v` | 启用调试日志 | False |

### Python API

```python
from app.services.sitemap_crawler import SitemapCrawler, CrawlConfig

# 使用配置对象
config = CrawlConfig(
    sitemap_url="https://example.com/sitemap.xml",
    timeout=30,
    max_urls=100,
    delay_between_requests=0.5,
    output_dir="./crawl_results",
)

crawler = SitemapCrawler(config=config)
results = crawler.crawl()

# 打印摘要
crawler.print_report()

# 获取摘要字典
summary = crawler.get_summary()

# 保存结果
crawler.save_results()
```

### 使用独立组件

```python
from app.services.sitemap_parser import SitemapParser
from app.services.url_scanner import URLScanner

# 解析站点地图
parser = SitemapParser("https://example.com/sitemap.xml")
parser.fetch_sitemap()
urls = parser.parse()

# 扫描单个 URL
scanner = URLScanner(timeout=30)
for url in urls:
    result = scanner.scan(url)
    print(f"URL: {result.url}")
    print(f"状态: {result.status_code}")
    print(f"标题: {result.title}")
    print(f"链接: {len(result.links['internal'])} 内部链接, {len(result.links['external'])} 外部链接")
```

## 配置文件

创建 JSON 配置文件：

```json
{
  "sitemap_url": "https://example.com/sitemap.xml",
  "timeout": 30,
  "max_urls": 100,
  "delay_between_requests": 0.5,
  "output_dir": "./crawl_results",
  "verify_ssl": true,
  "follow_redirects": true,
  "max_content_length": 10485760,
  "check_robots_txt": true,
  "save_results": true,
  "verbose": true
}
```

## 环境变量

您也可以使用环境变量配置爬虫（创建 `.env` 文件）：

```bash
SITEMAP_URL=https://example.com/sitemap.xml
CRAWLER_TIMEOUT=30
CRAWLER_MAX_URLS=100
CRAWLER_DELAY=0.5
CRAWLER_OUTPUT_DIR=./crawl_results
CRAWLER_USER_AGENT="Mozilla/5.0..."
```

## 输出格式

爬虫将结果保存为 JSON 格式，结构如下：

```json
{
  "statistics": {
    "total_urls": 100,
    "successful_scans": 95,
    "failed_scans": 5,
    "total_load_time": 123.45,
    "start_time": "2024-01-01T10:00:00",
    "end_time": "2024-01-01T10:05:00"
  },
  "config": { ... },
  "results": [
    {
      "url": "https://example.com/page1",
      "status_code": 200,
      "content_type": "text/html",
      "title": "页面标题",
      "meta_description": "页面描述",
      "headings": { "h1": ["标题 1"], "h2": ["标题 2"] },
      "links": {
        "internal": ["https://example.com/page2"],
        "external": ["https://other.com/page"],
        "images": ["https://example.com/image.jpg"],
        "scripts": ["https://example.com/app.js"],
        "stylesheets": ["https://example.com/style.css"]
      },
      "word_count": 500,
      "load_time": 1.23,
      "error": null
    }
  ]
}
```

## 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_sitemap_parser.py

# 带覆盖率运行
pytest --cov=app tests/
```

## 项目结构

```
interview_agent/
├── app/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── crawler_config.py      # 配置管理
│   │   └── crawler_config.json    # 默认配置
│   ├── services/
│   │   ├── __init__.py
│   │   ├── sitemap_parser.py      # 站点地图 XML 解析器
│   │   ├── url_scanner.py         # URL 扫描器/爬虫
│   │   └── sitemap_crawler.py     # 主协调器
│   └── main_crawler.py            # CLI 入口点
├── tests/
│   ├── test_sitemap_parser.py
│   ├── test_url_scanner.py
│   └── test_sitemap_crawler.py
├── requirements.txt
└── README_CRAWLER.md
```

## 许可证

MIT

创建 JSON 配置文件：

```json
{
  "sitemap_url": "https://example.com/sitemap.xml",
  "timeout": 30,
  "max_urls": 100,
  "delay_between_requests": 0.5,
  "output_dir": "./crawl_results",
  "verify_ssl": true,
  "follow_redirects": true,
  "max_content_length": 10485760,
  "check_robots_txt": true,
  "save_results": true,
  "verbose": true
}
```

## 环境变量

您也可以使用环境变量配置爬虫（创建 `.env` 文件）：

```bash
SITEMAP_URL=https://example.com/sitemap.xml
CRAWLER_TIMEOUT=30
CRAWLER_MAX_URLS=100
CRAWLER_DELAY=0.5
CRAWLER_OUTPUT_DIR=./crawl_results
CRAWLER_USER_AGENT="Mozilla/5.0..."
```

## 输出格式

爬虫将结果保存为 JSON 格式，结构如下：

```json
{
  "statistics": {
    "total_urls": 100,
    "successful_scans": 95,
    "failed_scans": 5,
    "total_load_time": 123.45,
    "start_time": "2024-01-01T10:00:00",
    "end_time": "2024-01-01T10:05:00"
  },
  "config": { ... },
  "results": [
    {
      "url": "https://example.com/page1",
      "status_code": 200,
      "content_type": "text/html",
      "title": "页面标题",
      "meta_description": "页面描述",
      "headings": { "h1": ["标题 1"], "h2": ["标题 2"] },
      "links": {
        "internal": ["https://example.com/page2"],
        "external": ["https://other.com/page"],
        "images": ["https://example.com/image.jpg"],
        "scripts": ["https://example.com/app.js"],
        "stylesheets": ["https://example.com/style.css"]
      },
      "word_count": 500,
      "load_time": 1.23,
      "error": null
    }
  ]
}
```

## 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_sitemap_parser.py

# 带覆盖率运行
pytest --cov=app tests/
```

## 项目结构

```
interview_agent/
├── app/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── crawler_config.py      # 配置管理
│   │   └── crawler_config.json    # 默认配置
│   ├── services/
│   │   ├── __init__.py
│   │   ├── sitemap_parser.py      # 站点地图 XML 解析器
│   │   ├── url_scanner.py         # URL 扫描器/爬虫
│   │   └── sitemap_crawler.py     # 主协调器
│   └── main_crawler.py            # CLI 入口点
├── tests/
│   ├── test_sitemap_parser.py
│   ├── test_url_scanner.py
│   └── test_sitemap_crawler.py
├── requirements.txt
└── README_CRAWLER.md
```

## 许可证

MIT