# Interview AI Agent - 智能面试题管理系统

![CI Pipeline](https://github.com/your-username/interview_agent/actions/workflows/ci.yml/badge.svg)
![Docker Publish](https://github.com/your-username/interview_agent/actions/workflows/docker-publish.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)

一个基于大模型的智能面试题管理系统，支持自动爬取技术文档、AI识别面试题、向量存储和语义搜索。

## 功能特性

### 🤖 核心功能
- **智能爬虫**: 基于 Sitemap 的流式爬虫，边扫描边解析
- **AI 面试题识别**: 使用大模型自动从技术文档中识别和提取面试问题
- **向量数据库**: 基于 Redis Stack 的向量存储，支持语义搜索
- **URL 过滤**: 灵活的 include/exclude 规则，精确控制爬取范围
- **定时任务**: 支持每日自动执行爬取任务
- **RESTful API**: 完整的 API 接口，支持面试题管理和搜索

### 📊 数据处理流程
```
Sitemap → URL过滤 → 流式爬取 → AI识别 → 向量入库 → 语义搜索
```

## 📚 文档导航

为了保持项目结构清晰，所有文档已分类整理：

- **📖 项目文档**: [docs/README.md](docs/README.md) - 完整文档索引
- **🚀 部署配置**: [deploy/README.md](deploy/README.md) - 部署说明和快速参考
- **💻 开发指南**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - 系统架构设计
- **🕷️ 爬虫功能**: [docs/README_CRAWLER.md](docs/README_CRAWLER.md) - 爬虫详细说明
- **⚙️ CI/CD**: [.github/WORKFLOWS_GUIDE.md](.github/WORKFLOWS_GUIDE.md) - GitHub Actions 配置说明

> 💡 **提示**: 查看 [docs/README.md](docs/README.md) 获取所有文档的完整列表和推荐阅读路径。

## 快速开始

### 环境要求

- Python 3.10+
- pip
- Redis (可选，用于向量存储)

### 安装依赖

```bash
# 安装所有依赖
pip install -r requirements.txt
```

主要依赖包：
- `fastapi` + `uvicorn`: Web 框架
- `requests` + `beautifulsoup4` + `lxml`: 爬虫相关
- `openai`: 大模型 API
- `redis`: 向量数据库
- `langchain`: 大模型框架
- `json-repair`: JSON 修复工具
- `apscheduler`: 定时任务

### 配置环境变量

复制 `.env.template` 到 `.env` 并配置：

```bash
cp .env.template .env
```

编辑 `.env` 文件，配置以下内容：

#### 1. SMTP 配置（可选，用于邮件通知）
```ini
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_password
SMTP_TEST_USER=test@example.com
```

#### 2. 爬虫配置
```ini
# 站点地图配置
SITEMAP_URL=javaguide.cn  # 可以是域名或完整URL
CRAWLER_TIMEOUT=30
CRAWLER_MAX_URLS=         # 留空表示无限制
CRAWLER_DELAY=0.5
CRAWLER_OUTPUT_DIR=./crawl_results
CRAWLER_USER_AGENT=Mozilla/5.0...

# URL过滤规则（可选）
# CRAWLER_URL_INCLUDE_PATTERNS=["/docs/", "/api/"]  # 只爬取包含这些路径的URL
# CRAWLER_URL_EXCLUDE_PATTERNS=["/admin/", "/private/"]  # 排除包含这些路径的URL
```

#### 3. 大模型配置
```ini
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://api.openai.com/v1  # 或其他兼容API
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Token限制（可选，不配置则使用模型默认值）
# MODEL_MAX_INPUT_TOKENS=128000
# MODEL_MAX_OUTPUT_TOKENS=16384
```

#### 4. Redis 配置（向量数据库）
```ini
REDIS_URL=redis://localhost:6379
```

#### 5. 定时任务配置
```ini
SCHEDULER_HOUR=22    # 小时（0-23）
SCHEDULER_MINUTE=0   # 分钟（0-59）
```

### 启动服务

#### 1. 启动后端服务

```bash
python -m app.main
```

服务启动后访问：
- API文档：http://localhost:8000/docs
- 备用文档：http://localhost:8000/redoc

启动后会：
1. 初始化大模型服务和向量数据库
2. 启动定时任务调度器（默认每天22:00执行爬取）
3. 提供 RESTful API 接口

#### 2. 启动前端服务（可选）

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000 使用图形化界面。

前端功能：
- 🎯 爬虫配置管理（批量爬取、单页爬取）
- 🎲 面试题生成（指定类型、数量、难度等）
- 📊 系统状态监控

## ⚙️ CI/CD 自动化

本项目使用 GitHub Actions 实现完整的 CI/CD 自动化流程：

### 🔍 持续集成 (CI)

每次代码提交或 PR 时自动执行：
- ✅ 代码质量检查（flake8 + black）
- ✅ 单元测试（pytest，覆盖率 >60%）
- ✅ 前端构建验证
- ✅ Docker 镜像构建测试

### 📦 Docker 镜像发布

推送到 main 分支或创建 Release 时：
- 🐳 自动构建多平台 Docker 镜像（amd64/arm64）
- 📤 推送到 GitHub Container Registry (GHCR)
- 🏷️ 自动生成版本标签

```bash
# 拉取最新镜像
docker pull ghcr.io/<username>/interview_agent:latest
```

### 🚀 自动部署

支持手动触发或 Release 时自动部署：
- 🌐 多环境支持（production/staging）
- 🔒 SSH 安全部署
- ✔️ 健康检查和回滚机制

详细配置请参考：[.github/WORKFLOWS_GUIDE.md](.github/WORKFLOWS_GUIDE.md)

## API 接口

### 面试题管理

| 接口 | 方法 | 描述 |
|------|------|------|
| `/questions/ingest` | POST | 接收并存储面试题到向量数据库 |
| `/questions/search` | GET | 搜索面试题 |
| `/questions/{question_id}` | GET | 获取单个面试题详情 |
| `/questions/{question_id}` | DELETE | 删除面试题 |
| `/questions` | GET | 获取所有面试题（分页） |
| `/questions/count` | GET | 获取面试题总数 |
| `/questions/generate` | POST | 使用大模型生成答案 |
| `/questions/generate-batch` | POST | 批量生成随机面试题 |

### 爬虫管理

| 接口 | 方法 | 描述 |
|------|------|------|
| `/crawl/run` | GET | 手动触发爬虫任务（流式处理） |
| `/crawl/status` | GET | 获取最近一次爬取状态 |
| `/crawl/single-page` | POST | 智能爬取单个页面并提取面试问题 |
| `/api/config` | GET | 获取爬虫配置 |
| `/api/config` | PUT | 更新爬虫配置 |
| `/api/scheduler-config` | GET | 获取定时任务配置 |
| `/api/scheduler-config` | PUT | 更新定时任务配置 |

### 搜索功能

| 接口 | 方法 | 描述 |
|------|------|------|
| `/search` | POST | 语义搜索面试题 |

### 接口示例

#### 1. 手动触发爬虫

```bash
curl http://localhost:8000/crawl/run
```

响应示例：
```json
{
  "status": "success",
  "message": "爬取完成",
  "statistics": {
    "total_urls": 50,
    "successful_scans": 48,
    "failed_scans": 2
  },
  "result_count": 48,
  "parsed_questions": 120,
  "inserted_questions": 118
}
```

**说明**: 
- `parsed_questions`: AI识别出的问题总数
- `inserted_questions`: 成功插入向量数据库的问题数
- 采用**流式处理**模式，边扫描边解析，实时入库

#### 2. 获取爬取状态

```bash
curl http://localhost:8000/crawl/status
```

#### 3. 智能爬取单个页面

```bash
curl -X POST "http://localhost:8000/crawl/single-page?url=https://www.runoob.com/python3/python3-tutorial.html"
```

响应示例：
```json
{
  "status": "success",
  "message": "页面爬取完成",
  "url": "https://www.runoob.com/python3/python3-tutorial.html",
  "title": "Python3 教程",
  "parsed_questions": 5,
  "inserted_questions": 5,
  "word_count": 1234,
  "load_time": 1.23
}
```

**说明**: 
- 该接口用于快速爬取和分析单个技术页面
- 自动识别页面中的面试问题并存入向量数据库
- 适用于临时分析特定技术文章或文档

#### 4. 获取爬虫配置

```bash
curl http://localhost:8000/api/config
```

响应示例：
```json
{
  "status": "success",
  "config": {
    "sitemap_url": "javaguide.cn",
    "timeout": 30,
    "max_urls": null,
    "delay_between_requests": 0.5,
    "url_include_patterns": ["/docs/"],
    "url_exclude_patterns": []
  }
}
```

#### 5. 更新爬虫配置

```bash
curl -X PUT http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "sitemap_url": "example.com",
    "timeout": 60,
    "max_urls": 100,
    "url_include_patterns": ["/tutorial/"]
  }'
```

#### 6. 批量生成面试题

```bash
curl -X POST "http://localhost:8000/questions/generate-batch?count=10&difficulty=medium&tags=Python"
```

响应示例：
```json
{
  "status": "success",
  "count": 10,
  "questions": [
    {
      "id": "xxx",
      "title": "什么是Python装饰器？",
      "answer": "装饰器是一种特殊的函数...",
      "source_url": "https://example.com",
      "tags": ["Python", "基础"],
      "difficulty": "medium",
      "category": "编程语言",
      "importance_score": 0.8
    }
  ]
}
```

#### 4. 提交面试题（直接入库）

```bash
curl -X POST http://localhost:8000/questions/ingest \
  -H "Content-Type: application/json" \
  -d '[
    {
      "title": "什么是Python装饰器？",
      "answer": "装饰器是一种特殊的函数，可以用来修改其他函数的行为...",
      "source_url": "https://example.com/python-decorator",
      "tags": ["Python", "基础"],
      "importance_score": 0.9,
      "difficulty": "medium",
      "category": "编程语言"
    }
  ]'
```

#### 4. 语义搜索面试题

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何实现JWT认证",
    "top_k": 5
  }'
```

响应示例：
```json
{
  "query": "如何实现JWT认证",
  "results": [
    {
      "id": "xxx",
      "title": "JWT认证原理",
      "answer": "JWT由三部分组成...",
      "source_url": "https://javaguide.cn/system-design/security/jwt-intro.html",
      "tags": ["安全", "认证"],
      "score": 0.95
    }
  ],
  "total": 5
}
```

## 定时任务

系统支持每天定时执行爬虫任务，默认配置为 **22:00**。

可以通过修改 `.env` 文件调整执行时间：

```ini
SCHEDULER_HOUR=22    # 小时（0-23）
SCHEDULER_MINUTE=0   # 分钟（0-59）
```

定时任务会：
1. 读取配置的 Sitemap URL
2. 应用 URL 过滤规则
3. 流式爬取页面并实时 AI 识别
4. 将识别的面试题存入向量数据库

## 独立运行爬虫

如果只想运行爬虫而不需要启动API服务：

```bash
# 使用默认配置（app/config/crawler_config.json）
python -m app.main_crawler

# 指定站点地图URL
python -m app.main_crawler --sitemap-url javaguide.cn

# 指定自定义站点地图路径
python -m app.main_crawler --sitemap-url example.com --sitemap-path /custom-sitemap.xml

# 带选项
python -m app.main_crawler \
    --sitemap-url javaguide.cn \
    --max-urls 100 \
    --timeout 60 \
    --delay 1.0 \
    --output-dir ./results

# 使用配置文件
python -m app.main_crawler --config app/config/crawler_config.json

# 查看所有选项
python -m app.main_crawler --help
```

### 爬虫配置说明

#### 方式1: JSON配置文件

在 `app/config/crawler_config.json` 中配置：

```json
{
  "sitemap_url": "javaguide.cn",
  "sitemap_path": "/sitemap.xml",
  "timeout": 30,
  "max_urls": null,
  "delay_between_requests": 0.5,
  "output_dir": "./crawl_results",
  "verify_ssl": true,
  "follow_redirects": true,
  "check_robots_txt": true,
  "url_include_patterns": ["/docs/", "/api/"],
  "url_exclude_patterns": ["/admin/", "/private/"]
}
```

#### 方式2: 环境变量

在 `.env` 文件中配置（详见上文）。

#### 方式3: CLI参数

通过命令行参数直接指定（优先级最高）。

### URL过滤规则

URL过滤功能允许您通过定义 include/exclude 规则来灵活控制哪些页面需要爬取。

**Include Patterns（包含规则）**:
- 如果定义了 include_patterns，URL **必须匹配至少一个** include 模式才会被爬取
- 未定义时：如果没有定义 include_patterns，默认允许所有 URL（除非被 exclude 排除）
- 示例: `["/docs/"]` - 只爬取包含 `/docs/` 路径的 URL

**Exclude Patterns（排除规则）**:
- 如果 URL 匹配任何 exclude 模式，则**不会被爬取**
- 优先级: exclude 规则优先于 include 规则检查
- 示例: `["/admin/", "\\.pdf$"]` - 排除管理后台和PDF文件

**常用正则表达式示例**:
```json
{
  "url_include_patterns": [
    "/docs/",           // 包含 /docs/ 路径
    "/api/v[0-9]+/"     // 包含 /api/v1/, /api/v2/ 等路径
  ],
  "url_exclude_patterns": [
    "\\.pdf$",          // 排除 PDF 文件
    "\\.(jpg|png)$",    // 排除图片文件
    "/admin/",          // 排除管理后台
    "\\?page=[0-9]+$"   // 排除分页参数
  ]
}
```

详细使用说明请参考：[URL_FILTER_GUIDE.md](URL_FILTER_GUIDE.md)

## 测试

运行测试套件：

```bash
pytest tests/
```

运行特定测试：

```bash
# URL过滤测试
python -m tests.test_url_filter

# 页面分块测试
python -m tests.test_page_chunking

# 爬虫测试
pytest tests/test_sitemap_crawler.py

# 带覆盖率运行
pytest --cov=app tests/
```

## 开发说明

### 核心模块说明

#### 1. 爬虫模块
- **SitemapCrawler** (`app/services/sitemap_crawler.py`): 主爬虫类，协调站点地图解析和URL扫描
- **SitemapParser** (`app/services/sitemap_parser.py`): 解析XML站点地图，提取所有URL
- **URLScanner** (`app/services/url_scanner.py`): 扫描单个URL，获取页面内容
- **URLFilter** (`app/services/url_filter.py`): URL过滤器，支持 include/exclude 规则
- **CrawlerConfig** (`app/config/crawler_config.py`): 配置管理类，支持多种配置来源

#### 2. AI服务模块
- **LLMService** (`app/services/llm_service.py`): 大模型服务，负责面试题识别和提取
  - 支持多种大模型（OpenAI, Qwen, DeepSeek等）
  - 自动Token限制检测和分块处理
  - JSON输出修复机制
  - 支持回调函数实现即时入库
  
- **VectorService** (`app/services/vector_service.py`): 向量数据库服务
  - 基于 Redis Stack 的向量存储
  - 自动生成文本 Embedding
  - 支持语义搜索和相似度匹配
  - 索引管理和维护

#### 3. Web服务模块
- **main.py** (`app/main.py`): FastAPI 应用入口
  - RESTful API 接口
  - 定时任务调度
  - 流式爬取与实时处理

### 架构设计

#### 流式处理架构

```
┌─────────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│   Sitemap   │────▶│ URL过滤  │────▶│ 流式爬取  │────▶│ AI识别   │────▶│ 向量入库  │
└─────────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
                      (可选)          (边扫边解)      (实时处理)       (Redis)
```

**优势**:
- ✅ 扫描一个页面立即处理一个，无需等待所有页面扫描完成
- ✅ 内存占用低（只需处理当前页面）
- ✅ 即使中途失败，已处理的页面已经入库
- ✅ 用户可以实时看到处理进度和结果
- ✅ 更适合大规模爬取任务

详细技术说明请参考：[STREAMING_CRAWL.md](STREAMING_CRAWL.md)

### 数据处理流程

1. **Sitemap解析**: 从配置的站点地图中提取所有URL
2. **URL过滤**: 根据 include/exclude 规则过滤URL
3. **流式爬取**: 逐个扫描URL，获取页面内容
4. **AI识别**: 调用大模型识别面试问题
   - 自动检测Token限制
   - 智能分块处理长文档
   - JSON输出修复
5. **向量生成**: 为每个问题生成 Embedding
6. **向量入库**: 存入 Redis Stack
7. **语义搜索**: 支持基于向量的相似度搜索

### 配置管理

系统支持三种配置方式（优先级从高到低）：

1. **CLI参数**: 命令行直接指定
2. **JSON配置文件**: `app/config/crawler_config.json`
3. **环境变量**: `.env` 文件

### 扩展开发

#### 添加新的大模型支持

在 `app/services/llm_service.py` 中添加新的客户端初始化逻辑。

#### 自定义向量数据库

修改 `app/services/vector_service.py` 中的 `_init_clients()` 方法。

#### 添加新的URL过滤规则

在 `app/services/url_filter.py` 中扩展过滤逻辑。

### 待实现功能

- [ ] 用户认证与权限管理
- [ ] 日志系统完善
- [ ] 面试题去重优化
- [ ] 更多大模型支持

## 相关文档

- **[README_CRAWLER.md](README_CRAWLER.md)**: 爬虫详细使用说明
- **[STREAMING_CRAWL.md](STREAMING_CRAWL.md)**: 流式处理架构技术说明
- **[URL_FILTER_GUIDE.md](URL_FILTER_GUIDE.md)**: URL过滤规则使用指南
- **[SINGLE_PAGE_CRAWL.md](SINGLE_PAGE_CRAWL.md)**: 单页爬取接口使用说明
- **[frontend/README.md](frontend/README.md)**: 前端界面使用说明

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
│   │   ├── url_filter.py          # URL过滤器
│   │   ├── sitemap_crawler.py     # 主协调器
│   │   ├── llm_service.py         # 大模型服务
│   │   └── vector_service.py      # 向量数据库服务
│   ├── templates/
│   │   └── email_template.html    # 邮件模板
│   ├── main.py                    # FastAPI应用入口
│   └── main_crawler.py            # CLI爬虫入口
├── frontend/                      # Vue 3 前端项目
│   ├── src/
│   │   ├── views/                 # 页面视图
│   │   ├── services/              # API 服务
│   │   ├── router/                # 路由配置
│   │   ├── App.vue                # 根组件
│   │   └── main.js                # 入口文件
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── README.md                  # 前端文档
├── tests/
│   ├── test_sitemap_parser.py
│   ├── test_url_scanner.py
│   ├── test_sitemap_crawler.py
│   ├── test_url_filter.py         # URL过滤测试
│   ├── test_page_chunking.py      # 页面分块测试
│   ├── test_single_page_crawl.py  # 单页爬取测试/示例
│   └── test_email_service.py      # 邮件服务测试
├── crawl_results/                 # 爬取结果存储目录
├── requirements.txt               # Python依赖
├── .env.template                  # 环境变量模板
├── README.md                      # 主文档
├── docs/                          # 📚 项目文档中心
│   ├── PROJECT_OVERVIEW.md        # 项目概览
│   ├── ARCHITECTURE.md            # 架构设计
│   ├── README_CRAWLER.md          # 爬虫功能说明
│   ├── STREAMING_CRAWL.md         # 流式处理文档
│   ├── URL_FILTER_GUIDE.md        # URL过滤文档
│   └── SINGLE_PAGE_CRAWL.md       # 单页爬取文档
├── deploy/                        # 🚀 部署配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── README.md                  # 部署说明
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 常见问题

### Q: Redis连接失败怎么办？

A: 确保Redis服务已启动，并检查 `.env` 中的 `REDIS_URL` 配置是否正确。如果不需要向量存储功能，可以暂时忽略此错误，系统会使用备用方案。

### Q: 大模型API调用失败？

A: 检查以下几点：
1. `OPENAI_API_KEY` 是否正确配置
2. `OPENAI_API_BASE` 是否指向正确的API地址
3. 网络连接是否正常
4. API配额是否充足

### Q: 如何只爬取特定类型的页面？

A: 使用 URL 过滤规则，在 `.env` 或 `crawler_config.json` 中配置 `url_include_patterns` 和 `url_exclude_patterns`。详见 [docs/URL_FILTER_GUIDE.md](docs/URL_FILTER_GUIDE.md)。

### Q: 爬虫速度太慢怎么办？

A: 可以调整以下配置：
- 减小 `CRAWLER_DELAY`（但要注意不要对服务器造成压力）
- 增加 `CRAWLER_TIMEOUT`
- 使用 URL 过滤减少不必要的页面爬取

### Q: 如何查看爬取进度？

A: 启动服务后，日志会实时输出爬取进度。也可以访问 `/crawl/status` API 获取最近一次爬取的状态。
