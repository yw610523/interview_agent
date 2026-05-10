# Development Guide — 开发者指南

> 本文档面向希望理解、修改或扩展 Interview AI Agent 的开发者。

---

## 目录

- [系统架构](#系统架构)
- [项目结构](#项目结构)
- [核心模块](#核心模块)
- [配置管理](#配置管理)
- [扩展开发](#扩展开发)
- [测试](#测试)
- [API 接口全览](#api-接口全览)

---

## 系统架构

### 流式处理管线

```
┌─────────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│   Sitemap   │────▶│ URL过滤  │────▶│ 流式爬取  │────▶│ AI识别   │────▶│ 向量入库  │
└─────────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
                      (可选)          (边扫边解)      (实时处理)       (Redis)
```

核心设计原则：**扫描一个页面立即处理一个**，无需等待所有页面完成。

- 内存占用低（只需处理当前页面）
- 即使中途失败，已处理的页面已经入库
- 用户可以实时看到处理进度

### 部署架构

```
┌──────────────────────────────────┐
│  Nginx (80)                      │ ← 用户访问入口
│  - 前端静态文件                    │
│  - 反向代理 → FastAPI            │
│         │                        │
│         ↓                        │
│  FastAPI (internal :8000)        │
└─────────┬────────────────────────┘
          │
          ↓
┌──────────────────────────────────┐
│  Redis Stack (6379)              │
│  - 向量存储                      │
│  - 爬取缓存                      │
└──────────────────────────────────┘
```

---

## 项目结构

```
interview_agent/
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI 应用入口 + 路由定义
│   ├── main_crawler.py                # CLI 独立爬虫入口
│   ├── config/
│   │   ├── crawler_config.py          # 配置管理类（多来源合并）
│   │   └── crawler_config.json        # 默认爬虫配置
│   ├── services/
│   │   ├── sitemap_parser.py          # XML 站点地图解析器
│   │   ├── url_scanner.py             # 单页内容扫描器
│   │   ├── url_filter.py              # URL 正则过滤引擎
│   │   ├── sitemap_crawler.py         # 爬虫主协调器
│   │   ├── llm_service.py             # 大模型服务（识别 + 分块 + JSON 修复）
│   │   ├── vector_service.py          # Redis 向量数据库服务
│   │   ├── config_hot_reload.py       # 配置热加载管理器
│   │   └── email_service.py           # 邮件发送服务
│   └── templates/
│       └── email_template.html        # 邮件 HTML 模板
├── frontend/                          # Vue 3 前端项目
├── tests/                             # 单元测试
├── crawl_results/                     # 爬取结果输出目录
├── deploy/                            # Docker / Nginx / CI-CD 配置
└── docs/                              # 文档
```

---

## 核心模块

### 1. 爬虫模块

所有爬虫服务在 `app/services/` 下，职责分明：

| 类 | 文件 | 职责 |
|----|------|------|
| `SitemapParser` | `sitemap_parser.py` | 从 XML Sitemap 中提取所有 URL |
| `URLScanner` | `url_scanner.py` | 扫描单个 URL 的 HTML 内容 |
| `URLFilter` | `url_filter.py` | 基于正则 include/exclude 规则过滤 URL |
| `SitemapCrawler` | `sitemap_crawler.py` | 主协调器：解析→过滤→扫描→回调 |
| `CrawlerConfig` | `config/crawler_config.py` | 多来源配置合并（环境变量 / JSON / CLI） |

**爬虫调用链**：

```
SitemapCrawler.crawl()
  → SitemapParser.parse()          # 提取 URL 列表
  → URLFilter.filter()             # 过滤 URL
  → 遍历 URL, 对每个:
      → URLScanner.scan(url)       # 获取页面内容
      → page_processed_callback()  # 回调传入 main.py，触发 AI 识别 + 入库
```

**关键设计 — 回调机制**：`SitemapCrawler.crawl()` 接受 `page_processed_callback` 参数。每扫描完一个页面就回调一次，让调用方决定如何处理页面内容（如调用 LLM 识别面试题并入库），而非等待全部爬取完毕。

### 2. AI 服务模块

#### LLMService (`app/services/llm_service.py`)

大模型服务，负责面试题识别和提取。

**核心方法**：

| 方法 | 用途 |
|------|------|
| `parse_crawl_results(pages, on_question_found)` | 从爬取的页面内容中识别面试题 |
| `generate_answer(question)` | 为指定问题生成答案 |
| `repair_json(text)` | 自动修复 LLM 输出的非标准 JSON |

**特性**：

- **多模型兼容** — 使用 OpenAI 兼容 API，可接入 OpenAI、Qwen、DeepSeek 等
- **Token 感知分块** — 自动检测模型 Token 上限，超长文档自动分块处理
- **回调即时入库** — `on_question_found` 回调让每识别一批问题立即入库
- **JSON 修复** — `json-repair` 库自动修复 LLM 偶尔输出的非标准 JSON

**支持的模型**（通过 `OPENAI_API_BASE` 和 `OPENAI_MODEL` 切换）：

```
gpt-4o-mini / gpt-4o          → OpenAI
qwen-plus / qwen-max           → 通义千问
deepseek-chat / deepseek-reasoner → DeepSeek
```

#### VectorService (`app/services/vector_service.py`)

基于 Redis Stack 的向量数据库服务。

**核心方法**：

| 方法 | 用途 |
|------|------|
| `insert_questions(records)` | 批量插入面试题并生成 Embedding |
| `search(query, top_k, filters)` | 语义搜索 |
| `get_by_id(id)` | 按 ID 查询 |
| `delete_by_id(id)` | 按 ID 删除 |
| `get_all()` | 获取全部（用于分页 / 批量生成） |
| `count()` | 统计总数 |

**向量存储结构** — Redis Hash 键格式：

```
question:{uuid}
  ├── title              (string)
  ├── answer             (string)
  ├── source_url         (string)
  ├── tags               (JSON array string)
  ├── importance_score   (float)
  ├── difficulty         (string)
  ├── category           (string)
  └── embedding          (binary vector)
```

Redis Stack 通过 `FT.CREATE` 创建向量索引支持 `KNN` 搜索。

### 3. Web 服务模块

`app/main.py` — FastAPI 应用入口，包含：

- **API 路由定义** — 面试题管理、爬虫控制、系统配置（400+ 行路由）
- **定时任务调度** — 基于 APScheduler 的 Cron 触发，默认每天 22:00
- **流式爬取** — `run_crawler()` + 回调机制实现边爬边解析
- **SSE 实时日志** — `/crawl/single-page/stream` 端点支持 EventSource 实时推送进度

**热加载机制** — `ConfigHotReloadManager` 允许在运行时更新 LLM、Redis、Email 配置并立即生效，无需重启进程。

---

## 配置管理

系统支持两种配置来源，**优先级从高到低**：

```
CLI 参数  >  YAML 配置文件 (config.yaml)
```

### CrawlerConfig 类

`app/config/crawler_config.py` 中的 `CrawlerConfig` 类统一管理所有爬虫配置：

```python
# 从 YAML 文件加载（推荐）
config = CrawlerConfig.from_yaml("config.yaml")

# 从统一配置管理器加载
from app.config.config_manager import config_manager
config = config_manager.get_crawler_config()

# 从字典加载（用于 API 更新）
config = CrawlerConfig.from_dict({"sitemap_url": "example.com", ...})
```

### YAML 配置项说明

所有配置项都在 `config.yaml` 中管理，主要包含以下部分：

| 配置节 | 描述 | 示例 |
|----------|-----------|--------|
| `crawler.sitemap_url` | Sitemap URL | `https://example.com/sitemap.xml` |
| `crawler.timeout` | 请求超时时间 | `30` |
| `crawler.max_urls` | 最大爬取URL数 | `null` |
| `crawler.delay_between_requests` | 请求间隔 | `0.5` |
| `crawler.url_include_patterns` | URL包含模式 | `["/docs/"]` |
| `crawler.url_exclude_patterns` | URL排除模式 | `["/admin/"]` |
| `llm.openai_api_key` | LLM API Key | `sk-xxx` |
| `redis.url` | Redis连接地址 | `redis://localhost:6379` |

---

## 扩展开发

### 添加新的大模型支持

`LLMService` 使用 OpenAI 兼容 API 协议，接入新模型只需修改环境变量：

```ini
OPENAI_API_BASE=https://api.new-provider.com/v1
OPENAI_MODEL=new-model-name
OPENAI_API_KEY=your_key
```

如果新模型有特殊的 Token 限制，在 `config.yaml` 中配置：

```yaml
llm:
  max_input_tokens: 128000
  max_output_tokens: 16384
```

如果需要深度定制（如不同的请求格式），修改 `llm_service.py` 中的 `_call_llm()` 方法。

### 自定义向量数据库

当前实现基于 Redis Stack。如需替换为其他向量数据库（如 Pinecone、Milvus、Qdrant）：

1. 修改 `vector_service.py` 中的 `_init_clients()` 方法
2. 实现 `insert_questions()`、`search()`、`get_by_id()`、`delete_by_id()`、`get_all()`、`count()` 六个核心方法
3. 保持 `VectorRecord` 数据类的接口不变

### 自定义 URL 过滤规则

`url_filter.py` 中的 `URLFilter` 类提供了 `include_patterns` 和 `exclude_patterns` 支持。

如需添加自定义过滤逻辑（如按页面大小、域名、内容类型过滤），在 `URLFilter.filter()` 方法中扩展：

```python
class URLFilter:
    def filter(self, urls: List[str]) -> List[str]:
        # 现有正则过滤
        urls = self._apply_include_patterns(urls)
        urls = self._apply_exclude_patterns(urls)
        
        # 自定义：按域名白名单过滤
        urls = [u for u in urls if self._is_allowed_domain(u)]
        
        return urls
```

### 添加新的 API 端点

在 `app/main.py` 中添加路由，使用 FastAPI 装饰器：

```python
@app.get("/api/my-custom-endpoint")
async def my_custom_endpoint():
    # 可以访问 llm_service 和 vector_service 全局实例
    return {"status": "ok"}
```

---

## API 接口全览

### 面试题管理

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/questions/ingest` | POST | 批量入库面试题 |
| `/api/questions/search` | GET | 关键词搜索（支持标签/难度过滤） |
| `/api/questions/{id}` | GET | 获取单题详情 |
| `/api/questions/{id}` | DELETE | 删除单题 |
| `/api/questions` | GET | 分页获取全部 |
| `/api/questions/count` | GET | 统计总数 |
| `/api/questions/generate` | POST | 用 LLM 生成答案 |
| `/api/questions/generate-batch` | POST | 随机批量获取 |

### 爬虫管理

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/crawl/run` | GET | 手动触发爬取 |
| `/api/crawl/status` | GET | 查看爬取状态 |
| `/api/crawl/single-page` | POST | 单页爬取+AI识别 |
| `/api/crawl/single-page/stream` | GET | SSE 实时日志流 |
| `/api/config` | GET/PUT | 爬虫配置读写 |
| `/api/scheduler-config` | GET/PUT | 定时任务配置读写 |

### 系统配置

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/system-config` | GET | 获取全部配置 |
| `/api/llm-config` | PUT | 更新 LLM 配置 |
| `/api/redis-config` | PUT | 更新 Redis 配置 |
| `/api/email-config` | PUT | 更新邮件配置 |
| `/api/test-email` | POST | 测试邮件发送 |

### 搜索

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/search` | POST | 语义搜索 |

### 调试

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/debug/vector-status` | GET | 向量数据库状态和样本数据 |
| `/api/debug/reset-index` | POST | 重置索引和数据 |
| `/api/debug/merge-duplicates` | POST | 检测并合并相似问题 |

---

## 测试

```bash
# 运行全部测试
pytest tests/

# 带覆盖率
pytest --cov=app tests/

# 特定测试
pytest tests/test_sitemap_crawler.py -v
python -m tests.test_url_filter
python -m tests.test_page_chunking
python -m tests.test_single_page_crawl
python -m tests.test_email_service
```

测试文件位于 `tests/` 目录，使用 pytest 框架。

---

## 待实现功能

- [ ] 用户认证与权限管理
- [ ] 日志系统完善
- [ ] 面试题去重优化
- [ ] 更多大模型原生 SDK 支持（非 OpenAI 兼容协议）
- [x] 系统设置界面（已完成）
