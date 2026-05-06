# Interview AI Agent - 项目总览

## 📖 项目简介

Interview AI Agent 是一个基于大模型的智能面试题管理系统，支持自动爬取技术文档、AI识别面试题、向量存储和语义搜索。

本项目现已包含完整的**前端界面**和**后端API**，提供图形化的用户操作界面。

## 🎯 核心功能

### 1. 智能爬虫
- **批量爬取**: 基于Sitemap的大规模页面爬取
- **单页爬取**: 快速分析单个技术页面
- **URL过滤**: 灵活的include/exclude规则
- **流式处理**: 边扫描边解析，实时入库
- **配置管理**: 前端界面直接配置所有参数

### 2. AI面试题识别
- 使用大模型自动从技术文档中识别面试问题
- 智能分块处理长文档
- JSON输出修复机制
- 自动提取难度、分类、标签等元数据

### 3. 向量存储与搜索
- 基于Redis Stack的向量数据库
- 自动生成文本Embedding
- 支持语义搜索和相似度匹配
- 多维度筛选（难度、分类、标签）

### 4. 面试题生成
- 随机生成指定数量的面试题
- 按条件筛选（难度、分类、标签）
- 折叠面板展示问题和答案
- 显示题目来源和重要性评分

## 🏗️ 技术架构

### 后端技术栈
- **Python 3.10+**
- **FastAPI** - Web框架
- **OpenAI API** - 大模型服务
- **Redis Stack** - 向量数据库
- **BeautifulSoup4** - HTML解析
- **APScheduler** - 定时任务

### 前端技术栈
- **Vue 3** - 渐进式JavaScript框架
- **Vite 5** - 前端构建工具
- **Ant Design Vue 4** - UI组件库
- **Vue Router 4** - 路由管理
- **Pinia** - 状态管理
- **Axios** - HTTP客户端

## 📁 项目结构

```
interview_agent/
├── app/                          # 后端代码
│   ├── config/                   # 配置管理
│   ├── services/                 # 核心服务
│   │   ├── sitemap_crawler.py    # 爬虫服务
│   │   ├── llm_service.py        # 大模型服务
│   │   ├── vector_service.py     # 向量数据库服务
│   │   └── ...
│   ├── main.py                   # FastAPI入口
│   └── main_crawler.py           # CLI爬虫入口
├── frontend/                     # 前端代码
│   ├── src/
│   │   ├── views/                # 页面视图
│   │   │   ├── HomeView.vue      # 首页
│   │   │   ├── CrawlerView.vue   # 爬虫管理
│   │   │   └── QuestionsView.vue # 面试题生成
│   │   ├── services/             # API服务
│   │   ├── router/               # 路由配置
│   │   └── App.vue               # 根组件
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── tests/                        # 测试代码
├── crawl_results/                # 爬取结果
├── requirements.txt              # Python依赖
├── .env.template                 # 环境变量模板
├── README.md                     # 主文档
├── QUICKSTART.md                 # 快速启动指南
└── FRONTEND_SUMMARY.md           # 前端开发总结
```

## 🚀 快速开始

### 方式一：完整启动（推荐）

#### 1. 启动后端
```bash
# 安装Python依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.template .env
# 编辑 .env 文件，配置API密钥等

# 启动后端服务
python -m app.main
```

访问 http://localhost:8000/docs 查看API文档

#### 2. 启动前端
```bash
# 打开新终端
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:3000 使用图形界面

### 方式二：仅使用后端API

```bash
python -m app.main

# 使用curl或Postman调用API
curl http://localhost:8000/crawl/run
curl http://localhost:8000/questions/generate-batch?count=10
```

## 📊 使用流程

### 典型工作流程

1. **配置爬虫** → 在"爬虫管理"页面设置Sitemap URL和过滤规则
2. **执行爬取** → 点击"立即执行批量爬取"或"单页爬取"
3. **等待处理** → AI自动识别面试题并存入向量数据库
4. **生成题目** → 在"面试题生成"页面选择条件并生成
5. **查看结果** → 点击问题展开查看答案

### 示例场景

#### 场景1: 学习新技术
1. 找到该技术的学习网站（如Python官方文档）
2. 使用单页爬取分析关键章节
3. 生成相关面试题进行自测

#### 场景2: 准备面试
1. 配置目标公司的技术博客Sitemap
2. 执行批量爬取收集相关问题
3. 按难度筛选生成模拟面试题
4. 反复练习直到掌握

#### 场景3: 构建题库
1. 配置多个技术网站的Sitemap
2. 设置定时任务每天自动爬取
3. 积累大量高质量面试题
4. 按需生成不同主题的试卷

## 🔌 API接口

### 爬虫管理
- `GET /crawl/run` - 手动触发批量爬取
- `GET /crawl/status` - 获取爬取状态
- `POST /crawl/single-page` - 单页爬取
- `GET /api/config` - 获取爬虫配置
- `PUT /api/config` - 更新爬虫配置

### 面试题管理
- `POST /questions/generate-batch` - 批量生成面试题
- `GET /questions/search` - 搜索面试题
- `GET /questions` - 获取所有面试题
- `GET /questions/count` - 获取总数
- `DELETE /questions/{id}` - 删除面试题

完整API文档：http://localhost:8000/docs

## 📝 配置文件

### 后端配置 (.env)
```ini
# 大模型配置
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Redis配置
REDIS_URL=redis://localhost:6379

# 爬虫配置
SITEMAP_URL=javaguide.cn
CRAWLER_MAX_URLS=
CRAWLER_DELAY=0.5

# 定时任务
SCHEDULER_HOUR=22
SCHEDULER_MINUTE=0
```

### 前端配置 (vite.config.js)
```javascript
server: {
  port: 3000,
  proxy: {
    '/api': { target: 'http://localhost:8000' },
    '/questions': { target: 'http://localhost:8000' },
    '/crawl': { target: 'http://localhost:8000' }
  }
}
```

## 🧪 测试

### 后端测试
```bash
pytest tests/
```

### 前端测试
```bash
cd frontend
npm run dev  # 手动测试
```

## 📚 相关文档

- **[README.md](README.md)** - 完整的项目说明文档
- **[QUICKSTART.md](QUICKSTART.md)** - 快速启动指南
- **[frontend/README.md](frontend/README.md)** - 前端详细说明
- **[frontend/INSTALL.md](frontend/INSTALL.md)** - 前端安装指南
- **[FRONTEND_SUMMARY.md](FRONTEND_SUMMARY.md)** - 前端开发总结
- **[README_CRAWLER.md](README_CRAWLER.md)** - 爬虫使用说明
- **[STREAMING_CRAWL.md](STREAMING_CRAWL.md)** - 流式处理架构
- **[URL_FILTER_GUIDE.md](URL_FILTER_GUIDE.md)** - URL过滤规则
- **[SINGLE_PAGE_CRAWL.md](SINGLE_PAGE_CRAWL.md)** - 单页爬取接口

## 🎨 界面预览

### 首页
- 系统介绍和功能说明
- 快速导航按钮
- 实时统计信息

### 爬虫管理
- 配置表单（Sitemap URL、超时、过滤规则等）
- 定时任务设置
- 批量爬取和单页爬取两个标签页
- 爬取状态和统计数据

### 面试题生成
- 筛选条件（数量、难度、分类、标签）
- 折叠面板展示题目列表
- 点击展开查看答案
- 显示来源链接和评分

## 💡 特色功能

1. **配置即改即用** - 前端修改配置立即生效，无需重启
2. **双模式爬取** - 批量和单页两种模式满足不同需求
3. **智能筛选** - 多维度筛选生成个性化面试题
4. **优雅展示** - 折叠面板设计，问题和答案清晰分离
5. **实时反馈** - 加载状态、成功/失败提示完善
6. **响应式设计** - 支持桌面端和移动端

## 🔧 开发扩展

### 添加新页面
1. 在 `frontend/src/views/` 创建Vue组件
2. 在 `frontend/src/router/index.js` 添加路由
3. 在 `App.vue` 菜单中添加导航项

### 添加新API
1. 在 `app/main.py` 添加FastAPI路由
2. 在 `frontend/src/services/index.js` 封装API调用
3. 在页面组件中调用新API

### 自定义样式
- 修改Ant Design主题
- 在组件中使用scoped样式
- 创建全局样式文件

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

感谢以下开源项目：
- FastAPI
- Vue.js
- Ant Design
- OpenAI
- Redis

---

**开始使用**: 参考 [QUICKSTART.md](QUICKSTART.md)

**遇到问题**: 查看各模块的详细文档或提交Issue
