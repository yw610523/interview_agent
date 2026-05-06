# Interview Agent Frontend

Interview AI Agent 的前端界面，基于 Vue 3 + Vite + Ant Design Vue 构建。

## 功能特性

### 1. 爬虫配置管理
- ✅ 在前端界面直接配置爬虫参数
- ✅ 支持批量爬取和单页爬取
- ✅ 配置URL包含/排除规则
- ✅ 定时任务配置

### 2. 面试题生成
- ✅ 随机生成指定数量的面试题
- ✅ 按难度、分类、标签筛选
- ✅ 问题直接展示，答案点击展开/收起
- ✅ 显示题目来源和元数据

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **Ant Design Vue** - 企业级 UI 组件库
- **Vue Router** - 官方路由管理器
- **Pinia** - Vue 状态管理库
- **Axios** - HTTP 客户端

## 快速开始

### 前置要求

- Node.js >= 16.0.0
- npm >= 8.0.0

### 安装依赖

```bash
cd frontend
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 生产构建

```bash
npm run build
```

构建产物将输出到 `dist` 目录。

### 预览生产构建

```bash
npm run preview
```

## 项目结构

```
frontend/
├── src/
│   ├── components/     # 可复用组件
│   ├── views/          # 页面视图
│   │   ├── HomeView.vue        # 首页
│   │   ├── CrawlerView.vue     # 爬虫管理页
│   │   └── QuestionsView.vue   # 面试题生成页
│   ├── services/       # API 服务
│   │   ├── api.js              # Axios 实例
│   │   └── index.js            # API 接口定义
│   ├── router/         # 路由配置
│   │   └── index.js
│   ├── App.vue         # 根组件
│   └── main.js         # 入口文件
├── index.html          # HTML 模板
├── vite.config.js      # Vite 配置
└── package.json        # 项目依赖
```

## API 代理配置

开发模式下，Vite 配置了代理，将请求转发到后端服务器：

- `/api/*` → `http://localhost:8000`
- `/questions/*` → `http://localhost:8000`
- `/crawl/*` → `http://localhost:8000`

确保后端服务在 8000 端口运行。

## 主要页面说明

### 1. 首页 (/)
- 系统介绍和功能说明
- 快速导航按钮
- 系统状态统计（面试题总数、上次爬取信息）

### 2. 爬虫管理 (/crawler)
包含两个标签页：

#### 批量爬取
- 爬虫配置表单（Sitemap URL、超时时间、URL过滤规则等）
- 定时任务配置
- 立即执行批量爬取按钮
- 查看爬取状态和统计信息

#### 单页爬取
- 输入单个页面URL进行智能爬取
- 实时显示爬取结果和问题识别数量

### 3. 面试题生成 (/questions)
- 生成配置（数量、难度、分类、标签）
- 面试题列表展示
- 折叠面板形式展示问题和答案
- 支持展开/收起全部答案
- 显示题目来源链接和重要性评分

## 开发指南

### 添加新页面

1. 在 `src/views/` 创建新的 Vue 组件
2. 在 `src/router/index.js` 中添加路由配置
3. 在 `App.vue` 的菜单中添加导航项

### 调用 API

使用已封装的 API 服务：

```javascript
import { crawlerApi, questionApi } from '../services'

// 获取爬虫配置
const config = await crawlerApi.getConfig()

// 生成面试题
const result = await questionApi.generateBatch(10, 'medium', null, ['Python'])
```

### 样式定制

项目使用 Ant Design Vue 的默认主题，可以通过修改 `vite.config.js` 或创建自定义主题文件来定制样式。

## 注意事项

1. **后端依赖**: 前端需要后端服务运行在 `http://localhost:8000`
2. **CORS**: 开发模式下通过 Vite 代理解决跨域问题
3. **环境变量**: 如需更改后端地址，修改 `vite.config.js` 中的 proxy 配置

## 浏览器支持

- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## License

MIT
