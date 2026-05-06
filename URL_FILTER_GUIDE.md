# URL 过滤规则使用指南

## 概述

URL 过滤功能允许您通过定义 include/exclude 规则来灵活控制哪些页面需要爬取。这对于大型网站特别有用，可以避免爬取不必要的页面，提高爬取效率。

## 配置方式

### 1. 通过 JSON 配置文件

在 `app/config/crawler_config.json` 中添加：

```json
{
  "url_include_patterns": ["/docs/", "/api/"],
  "url_exclude_patterns": ["/admin/", "/private/", "\\.pdf$"]
}
```

### 2. 通过环境变量

在 `.env` 文件中添加：

```bash
# 只爬取包含这些路径的URL
CRAWLER_URL_INCLUDE_PATTERNS=["/docs/", "/api/"]

# 排除包含这些路径的URL
CRAWLER_URL_EXCLUDE_PATTERNS=["/admin/", "/private/", "\\.pdf$"]
```

**注意**: 环境变量值必须是有效的 JSON 数组格式。

### 3. 通过代码直接配置

```python
from app.config.crawler_config import CrawlerConfig

config = CrawlerConfig(
    sitemap_url="https://example.com",
    url_include_patterns=["/docs/", "/api/"],
    url_exclude_patterns=["/admin/", "/private/"]
)
```

## 过滤规则说明

### Include Patterns（包含规则）

- **作用**: 如果定义了 include_patterns，URL **必须匹配至少一个** include 模式才会被爬取
- **未定义时**: 如果没有定义 include_patterns，默认允许所有 URL（除非被 exclude 排除）
- **示例**:
  - `["/docs/"]` - 只爬取包含 `/docs/` 路径的 URL
  - `["/docs/", "/api/"]` - 爬取包含 `/docs/` 或 `/api/` 路径的 URL

### Exclude Patterns（排除规则）

- **作用**: 如果 URL 匹配任何 exclude 模式，则**不会被爬取**
- **优先级**: exclude 规则优先于 include 规则检查
- **示例**:
  - `["/admin/"]` - 排除包含 `/admin/` 路径的 URL
  - `["\\.pdf$"]` - 排除以 `.pdf` 结尾的 URL
  - `["/admin/", "/private/", "\\.pdf$"]` - 排除多种类型的 URL

## 正则表达式示例

URL 过滤规则支持正则表达式，以下是一些常用示例：

### 路径匹配

```json
{
  "url_include_patterns": [
    "/docs/",           // 包含 /docs/ 路径
    "/api/v[0-9]+/"     // 包含 /api/v1/, /api/v2/ 等路径
  ]
}
```

### 文件类型过滤

```json
{
  "url_exclude_patterns": [
    "\\.pdf$",          // 排除 PDF 文件
    "\\.jpg$",          // 排除 JPG 图片
    "\\.png$",          // 排除 PNG 图片
    "\\.(pdf|jpg|png)$" // 排除多种文件类型
  ]
}
```

### 复杂模式

```json
{
  "url_exclude_patterns": [
    "/admin/",          // 排除管理后台
    "/private/",        // 排除私有页面
    "/test/",           // 排除测试页面
    "\\?page=[0-9]+$"   // 排除分页参数（避免重复爬取）
  ]
}
```

## 工作流程

1. **首先检查 exclude 规则**: 如果 URL 匹配任何 exclude 模式，立即排除
2. **然后检查 include 规则**: 
   - 如果定义了 include_patterns，URL 必须匹配至少一个 include 模式
   - 如果没有定义 include_patterns，默认允许（只要没被 exclude 排除）

## 实际示例

### 示例 1: 技术文档网站

假设您要爬取一个技术文档网站，但只想爬取文档部分，排除管理后台和附件：

```json
{
  "sitemap_url": "https://docs.example.com",
  "url_include_patterns": ["/docs/", "/guide/", "/tutorial/"],
  "url_exclude_patterns": ["/admin/", "/assets/", "\\.(pdf|zip)$"]
}
```

**结果**:
- ✓ `https://docs.example.com/docs/intro.html` - 爬取
- ✓ `https://docs.example.com/guide/getting-started.html` - 爬取
- ✗ `https://docs.example.com/admin/dashboard.html` - 排除（匹配 exclude）
- ✗ `https://docs.example.com/assets/logo.png` - 排除（匹配 exclude）
- ✗ `https://docs.example.com/blog/post.html` - 排除（不匹配 include）

### 示例 2: API 文档网站

只爬取 API 文档，排除其他所有内容：

```json
{
  "sitemap_url": "https://api.example.com",
  "url_include_patterns": ["/api/"],
  "url_exclude_patterns": []
}
```

**结果**:
- ✓ `https://api.example.com/api/users.html` - 爬取
- ✓ `https://api.example.com/api/v2/endpoints.html` - 爬取
- ✗ `https://api.example.com/about.html` - 排除（不匹配 include）
- ✗ `https://api.example.com/blog/news.html` - 排除（不匹配 include）

### 示例 3: 排除特定文件类型

爬取所有页面，但排除图片和文档附件：

```json
{
  "sitemap_url": "https://example.com",
  "url_include_patterns": [],
  "url_exclude_patterns": ["\\.(jpg|jpeg|png|gif|pdf|zip|tar\\.gz)$"]
}
```

**结果**:
- ✓ `https://example.com/page1.html` - 爬取
- ✓ `https://example.com/docs/readme.md` - 爬取
- ✗ `https://example.com/images/photo.jpg` - 排除（匹配 exclude）
- ✗ `https://example.com/files/manual.pdf` - 排除（匹配 exclude）

## 日志输出

启用详细日志后，您可以看到每个 URL 的过滤决策过程：

```
2026-05-06 14:51:06,978 - app.services.url_filter - INFO - URL过滤器初始化: include_patterns=2, exclude_patterns=3
2026-05-06 14:51:06,979 - app.services.url_filter - DEBUG - URL被exclude规则排除: https://example.com/admin/dashboard.html, 匹配模式: /admin/
2026-05-06 14:51:06,979 - app.services.url_filter - DEBUG - URL匹配include规则: https://example.com/docs/intro.html, 匹配模式: /docs/
2026-05-06 14:51:06,979 - app.services.url_filter - INFO - URL过滤完成: 原始=45, 过滤后=30, 排除=15
```

## 注意事项

1. **正则表达式语法**: 使用 Python 标准正则表达式语法
2. **大小写不敏感**: 所有模式匹配都是大小写不敏感的
3. **性能考虑**: 复杂的正则表达式可能影响性能，建议保持模式简洁
4. **转义字符**: 在 JSON 中，反斜杠需要双重转义（例如 `\\.` 表示 `\.`）
5. **测试规则**: 建议使用 `tests/test_url_filter.py` 测试您的过滤规则

## 测试

运行测试脚本验证 URL 过滤功能：

```bash
python -m tests.test_url_filter
```

## 常见问题

### Q: 如何排除所有带查询参数的 URL？

A: 使用以下 exclude 模式：
```json
{
  "url_exclude_patterns": ["\\?.+"]
}
```

### Q: 如何只爬取特定域名下的 URL？

A: 使用 include 模式匹配域名：
```json
{
  "url_include_patterns": ["https://docs\\.example\\.com/"]
}
```

### Q: 如何处理相对路径和绝对路径？

A: URL 过滤器会匹配完整的 URL 字符串，所以无论相对还是绝对路径都能正常工作。

### Q: 可以动态修改过滤规则吗？

A: 当前实现需要在爬取前配置好规则。如需动态修改，可以在代码中创建新的 `URLFilter` 实例。
