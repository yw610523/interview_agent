# Interview AI Agent - 智能面试题管理系统

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

基于大模型的智能面试题管理系统，支持自动爬取技术文档、AI 识别面试题、向量存储和语义搜索。

```
Sitemap → URL过滤 → 流式爬取 → AI识别 → 向量入库 → 语义搜索
```

---

## 🚀 快速部署与使用

### Docker Compose 部署（推荐）

按照以下步骤进行部署：

```bash
# 1. 克隆项目
git clone https://github.com/your-username/interview_agent.git
cd interview_agent

# 2. 复制环境变量模板
cp .env.template .env

# 3. 修改 .env 文件，填入真实的环境变量配置
# 编辑 .env 文件，至少需要配置以下关键参数：
# - OPENAI_API_KEY: 你的 OpenAI API 密钥
# - SMTP_USER, SMTP_PASSWORD: 邮件服务配置（如需要）
# - SITEMAP_URL: 要爬取的网站域名或 sitemap 地址
# - APP_PORT, REDIS_PORT, REDIS_INSIGHT_PORT: 服务端口（可选，有默认值）

# 4. 启动服务
docker-compose -f deploy/docker-compose.yml up -d
```

服务启动后访问：
- **前端界面**: http://localhost
- **API 文档**: http://localhost/docs
- **Redis Insight**（数据管理）: http://localhost:8001

> **使用外置 Redis**：如果需要连接外部 Redis 服务器，请：
> 1. 在 `.env` 中设置 `REDIS_URL=redis://[:password@]host:port`
> 2. 在 `deploy/docker-compose.yml` 中注释掉 `redis` 服务块和 `depends_on` 配置
> 3. 重新启动：`docker-compose -f deploy/docker-compose.yml up -d`

### 手动部署（开发环境）

#### 环境要求
- Python 3.10+
- Redis Stack（用于向量存储，可选用 Docker 启动）

```bash
# 启动 Redis（如果本地没有）
docker run -d --name redis-stack -p 6379:6379 redis/redis-stack:latest

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.template .env
# 编辑 .env 文件，填入真实的环境变量配置

# 启动服务
python -m app.main
```

#### 启动前端（可选）

```bash
cd frontend
npm install
npm run dev
```

---

## ⚙️ 配置说明

项目使用 `.env` 文件管理环境变量。首次部署时,请复制模板并配置:

```bash
cp .env.template .env
```

编辑 `.env` 文件,至少需要配置以下关键参数:

| 配置项 | 必填 | 说明 |
|--------|------|------|
| `OPENAI_API_KEY` | **是** | 大模型 API 密钥 |
| `OPENAI_API_BASE` | 否 | API 地址(默认 `https://api.openai.com/v1`) |
| `OPENAI_MODEL` | 否 | 模型名(默认 `gpt-4o-mini`,也兼容 Qwen/DeepSeek 等) |
| `SITEMAP_URL` | 否 | 目标站点域名或 Sitemap URL(默认 `javaguide.cn`) |
| `REDIS_URL` | 否 | Redis 连接地址（内置 Redis: `redis://redis:6379`，外置 Redis: `redis://[:password@]host:port`） |
| `SMTP_USER`, `SMTP_PASSWORD` | 否 | 邮件服务配置(如需要发送邮件功能) |
| `APP_PORT` | 否 | 前端访问端口（默认 `80`） |
| `REDIS_PORT` | 否 | Redis 端口（默认 `6379`） |
| `REDIS_INSIGHT_PORT` | 否 | RedisInsight 管理界面端口（默认 `8001`） |

完整配置项见 `.env.template` 文件。

---

## 📡 API 快速参考

### 爬虫

```bash
# 手动触发爬取
curl http://localhost:8000/crawl/run

# 智能爬取单页
curl -X POST "http://localhost:8000/crawl/single-page?url=https://example.com/docs"

# 查看爬取状态
curl http://localhost:8000/crawl/status
```

### 面试题

```bash
# 搜索面试题
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "JWT 认证原理", "top_k": 5}'

# 批量生成随机面试题
curl -X POST "http://localhost:8000/questions/generate-batch?count=10&difficulty=medium"

# 直接入库
curl -X POST http://localhost:8000/questions/ingest \
  -H "Content-Type: application/json" \
  -d '[{"title": "什么是 Python 装饰器？", "answer": "...", "tags": ["Python"]}]'

# 获取所有面试题（分页）
curl http://localhost:8000/questions?page=1&page_size=20
```

### 系统配置

```bash
# 查看所有配置
curl http://localhost:8000/api/system-config

# 更新模型配置
curl -X PUT http://localhost:8000/api/llm-config \
  -H "Content-Type: application/json" \
  -d '{"openai_api_key": "sk-xxx", "openai_model": "gpt-4o-mini"}'

# 更新爬虫配置
curl -X PUT http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{"sitemap_url": "example.com", "max_urls": 100}'
```

---

## 🌐 前端界面

前端提供图形化管理界面，功能包括：
- **爬虫配置管理** — 批量爬取、单页爬取
- **面试题生成** — 指定类型、数量、难度
- **系统设置管理** — 模型、Redis、邮件、定时任务
- **系统状态监控**

---

## 📖 文档导航

| 文档 | 适用人群 | 内容 |
|------|----------|------|
| **docs/DEVELOPMENT.md** | 开发者 | 架构设计、核心模块、扩展指南、测试 |
| **docs/README_CRAWLER.md** | 所有人 | 爬虫详细使用说明 |
| **docs/URL_FILTER_GUIDE.md** | 所有人 | URL 过滤规则配置 |
| **docs/STREAMING_CRAWL.md** | 开发者 | 流式处理架构技术细节 |
| **docs/SINGLE_PAGE_CRAWL.md** | 所有人 | 单页爬取接口使用说明 |
| **docs/SYSTEM_SETTINGS.md** | 所有人 | 系统设置功能说明 |
| **deploy/** | 运维 | Docker、Nginx、CI/CD 配置 |

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# URL 过滤测试
python -m tests.test_url_filter

# 爬虫测试
pytest tests/test_sitemap_crawler.py -v
```

---

## 许可证

MIT License
