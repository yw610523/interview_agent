
## 快速开始

### 环境要求

- Python 3.10+
- pip

### 安装依赖

```bash
# 安装所有依赖
pip install -r requirements.txt
```

### 配置环境变量

复制 `.env.template` 到 `.env` 并配置：

```bash
cp .env.template .env
```

编辑 `.env` 文件：

```ini
# SMTP 配置（可选）
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_password

# 爬虫配置
SITEMAP_URL=https://example.com/sitemap.xml  # 设置要爬取的站点地图URL
CRAWLER_TIMEOUT=30
CRAWLER_MAX_URLS=
CRAWLER_DELAY=0.5
CRAWLER_OUTPUT_DIR=./crawl_results

# 定时任务配置
SCHEDULER_HOUR=22
SCHEDULER_MINUTE=0
```

### 启动服务

```bash
python -m app.main
```

服务启动后访问：
- API文档：http://localhost:8000/docs
- 备用文档：http://localhost:8000/redoc

## API 接口

### 面试题管理

| 接口 | 方法 | 描述 |
|------|------|------|
| `/questions/ingest` | POST | 接收并存储面试题 |

### 爬虫管理

| 接口 | 方法 | 描述 |
|------|------|------|
| `/crawl/run` | GET | 手动触发爬虫任务 |
| `/crawl/status` | GET | 获取最近一次爬取状态 |

### 接口示例

#### 手动触发爬虫

```bash
curl http://localhost:8000/crawl/run
```

#### 获取爬取状态

```bash
curl http://localhost:8000/crawl/status
```

#### 提交面试题

```bash
curl -X POST http://localhost:8000/questions/ingest \
  -H "Content-Type: application/json" \
  -d '[
    {
      "title": "什么是Python装饰器？",
      "answer": "装饰器是一种特殊的函数，可以用来修改其他函数的行为...",
      "source_url": "https://example.com/python-decorator",
      "tags": ["Python", "基础"],
      "importance_score": 0.9
    }
  ]'
```

## 定时任务

系统支持每天定时执行爬虫任务，默认配置为 **22:00**。

可以通过修改 `.env` 文件调整执行时间：

```ini
SCHEDULER_HOUR=22    # 小时（0-23）
SCHEDULER_MINUTE=0   # 分钟（0-59）
```

## 独立运行爬虫

如果只想运行爬虫而不需要启动API服务：

```bash
# 使用默认配置
python -m app.main_crawler

# 指定站点地图URL
python -m app.main_crawler --sitemap-url https://example.com/sitemap.xml

# 使用配置文件
python -m app.main_crawler --config app/config/crawler_config.json

# 查看所有选项
python -m app.main_crawler --help
```

## 测试

运行测试套件：

```bash
pytest tests/
```

## 开发说明

### 核心模块说明

1. **SitemapCrawler**：主爬虫类，协调站点地图解析和URL扫描
2. **SitemapParser**：解析XML站点地图，提取所有URL
3. **URLScanner**：扫描单个URL，获取页面内容
4. **CrawlerConfig**：配置管理类，支持多种配置来源

### 待实现功能

- [ ] 向量数据库集成（Redis Stack）
- [ ] 面试题去重与相似度检测
- [ ] 大模型分析面试题
- [ ] 用户认证与权限管理
- [ ] 日志系统完善

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
