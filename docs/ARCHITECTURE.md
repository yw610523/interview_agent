# Docker 架构说明

## 您之前的问题

> "这个Dockerfile不对吧, 为什么暴露8000, 这不是后端地址吗, 我需要的是前端访问"

您的观察非常正确！最初的 Dockerfile 确实有问题。

---

## 问题分析

### ❌ 原始方案的问题

```
┌─────────────────────┐
│   Docker 容器        │
│                     │
│  FastAPI (8000)     │ ← 只暴露了后端 API
│                     │
└─────────────────────┘
       ↑
   用户无法直接访问前端
```

**问题**：
- 只暴露了 8000 端口（后端 API）
- 前端静态文件没有被 Web 服务器托管
- 用户无法通过浏览器访问前端界面

---

## ✅ 改进后的方案

### 方案对比

#### 方案一：Nginx + FastAPI 单容器（已实现）⭐

```
┌──────────────────────────────────┐
│    interview-agent 容器           │
│                                  │
│  ┌──────────┐                   │
│  │  Nginx   │  Port 80          │ ← 用户访问入口
│  │          │                   │
│  │ - 前端   │                   │
│  │ - 反向代理│                  │
│  └────┬─────┘                   │
│       │                          │
│       ↓                          │
│  ┌──────────┐                   │
│  │ FastAPI  │  Internal 8000    │ ← 内部 API
│  └────┬─────┘                   │
│       │                          │
└───────┼──────────────────────────┘
        │
        ↓
┌──────────────────────────────────┐
│    interview-redis 容器           │
│    Redis Stack (6379)            │
└──────────────────────────────────┘
```

**优点**：
- ✅ 单一入口（80 端口），简化部署
- ✅ 前后端统一部署，易于管理
- ✅ Nginx 提供高性能静态文件服务
- ✅ 自动处理 CORS 问题
- ✅ 适合中小规模应用

**访问方式**：
- 前端: `http://localhost`
- API: `http://localhost/api/*`（自动反向代理）
- Docs: `http://localhost/docs`

---

#### 方案二：前后端分离部署（备选）

```
┌─────────────────┐      ┌─────────────────┐
│  Frontend       │      │  Backend        │
│  Nginx (80)     │─────▶│  FastAPI (8000) │
│                 │ HTTP │                 │
└─────────────────┘      └────────┬────────┘
                                  │
                                  ↓
                         ┌─────────────────┐
                         │  Redis (6379)   │
                         └─────────────────┘
```

**优点**：
- ✅ 前后端独立扩展
- ✅ 可以独立更新前端或后端
- ✅ 适合大规模应用

**缺点**：
- ❌ 需要管理多个容器
- ❌ 需要配置 CORS
- ❌ 部署复杂度增加

---

## 当前实现的详细说明

### 1. Dockerfile 多阶段构建

```dockerfile
# 阶段 1: 前端构建
FROM node:18-alpine AS frontend-builder
# 构建 Vue3 前端 → dist/

# 阶段 2: 后端构建
FROM python:3.11-slim AS backend-builder
# 安装 Python 依赖和 FastAPI 应用

# 阶段 3: 最终镜像
FROM nginx:alpine
# - 复制前端 dist → /usr/share/nginx/html
# - 复制后端代码和依赖
# - 配置 Nginx 反向代理
# - 启动脚本同时运行 Nginx + FastAPI
```

### 2. Nginx 路由配置

```nginx
server {
    listen 80;
    
    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
    
    # API 反向代理到 FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }
    
    # FastAPI 文档
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }
}
```

### 3. 启动流程

```bash
#!/bin/sh
# docker-entrypoint.sh

# 1. 启动 FastAPI 后端（后台运行）
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# 2. 等待后端启动
sleep 3

# 3. 启动 Nginx（前台运行）
exec nginx -g 'daemon off;'
```

---

## 请求流程示例

### 场景 1: 用户访问首页

```
浏览器 → http://localhost/
    ↓
Nginx 接收请求
    ↓
返回 /usr/share/nginx/html/index.html
    ↓
浏览器渲染 Vue3 应用
```

### 场景 2: 前端调用 API

```
Vue App → fetch('/api/questions')
    ↓
Nginx 接收请求 /api/questions
    ↓
反向代理到 http://127.0.0.1:8000/questions
    ↓
FastAPI 处理请求
    ↓
返回 JSON 数据
    ↓
Nginx 转发响应给前端
    ↓
Vue App 接收并展示数据
```

### 场景 3: 访问 API 文档

```
浏览器 → http://localhost/docs
    ↓
Nginx 接收请求 /docs
    ↓
反向代理到 http://127.0.0.1:8000/docs
    ↓
FastAPI 返回 Swagger UI
    ↓
浏览器显示 API 文档
```

---

## 端口映射说明

### Docker Compose 配置

```yaml
services:
  app:
    ports:
      - "80:80"  # 主机端口:容器端口
    
  redis:
    ports:
      - "6379:6379"    # Redis
      - "8001:8001"    # RedisInsight
```

### 端口用途

| 端口 | 服务 | 说明 |
|------|------|------|
| 80 | Nginx | 前端 + API 反向代理（主要访问入口） |
| 8000 | FastAPI | 内部 API 服务（不对外暴露） |
| 6379 | Redis | 向量数据库 |
| 8001 | RedisInsight | Redis 可视化管理工具 |

---

## 为什么这样设计？

### 1. 用户体验优先

- 用户只需记住一个地址：`http://localhost`
- 无需关心前后端分离的细节
- API 调用透明，无 CORS 问题

### 2. 部署简化

- 单个容器包含所有组件
- 一键启动：`docker-compose up -d`
- 减少网络配置复杂度

### 3. 性能优化

- Nginx 高效处理静态文件
- 反向代理减少跨域开销
- 内部通信使用 localhost，速度快

### 4. 易于维护

- 统一的日志管理
- 简化的监控和告警
- 方便的备份和恢复

---

## 对比传统方案

| 特性 | 传统方案 | 当前方案 |
|------|----------|----------|
| 容器数量 | 3个（前端+后端+Redis） | 2个（应用+Redis） |
| 端口暴露 | 2个（80+8000） | 1个（80） |
| CORS 配置 | 需要配置 | 自动处理 |
| 部署复杂度 | 中 | 低 |
| 扩展性 | 高 | 中 |
| 适用场景 | 大型应用 | 中小型应用 |

---

## 如果需要前后端独立扩展

如果未来需要独立扩展前端或后端，可以轻松改造：

### 步骤 1: 拆分 Dockerfile

创建 `deploy/Dockerfile.frontend` 和 `deploy/Dockerfile.backend`

### 步骤 2: 修改 docker-compose.yml

```yaml
services:
  frontend:
    build:
      context: .
      dockerfile: deploy/Dockerfile.frontend
    ports:
      - "80:80"
  
  backend:
    build:
      context: .
      dockerfile: deploy/Dockerfile.backend
    expose:
      - "8000"  # 不对外暴露，只供前端访问
  
  redis:
    # ... 保持不变
```

### 步骤 3: 配置前端代理

在 Nginx 中配置后端地址：

```nginx
location /api/ {
    proxy_pass http://backend:8000;  # 使用 Docker 网络
}
```

---

## 总结

✅ **当前方案的核心优势**：
1. 用户通过 80 端口访问前端
2. Nginx 自动将 API 请求转发到后端
3. 简化的部署和维护
4. 良好的性能和用户体验

✅ **解决了您提出的问题**：
- ~~暴露 8000 端口~~ → 现在暴露 80 端口
- ~~无法访问前端~~ → 前端由 Nginx 托管
- ~~前后端分离混乱~~ → 统一入口，清晰的路由

📚 **相关文档**：
- [deploy/DEPLOYMENT.md](deploy/DEPLOYMENT.md) - 详细部署指南
- [deploy/CICD_README.md](deploy/CICD_README.md) - CI/CD 配置说明
- [deploy/docker-compose.yml](deploy/docker-compose.yml) - 服务编排配置
