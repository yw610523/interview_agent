# Firecrawl 源码构建部署指南

## 概述

本文档说明如何使用 git submodule 方式从源码构建和部署 Firecrawl 服务。

**重要**: 本项目使用自定义 fork 版本: https://github.com/yw610523/firecrawl.git

### Fork 版本优势

- ⚡ **快速响应** - 遇到问题立即修复,无需等待官方
- 🔧 **定制灵活** - 根据项目需求添加特定功能
- 🛡️ **稳定可控** - 锁定稳定版本,避免上游破坏性更新
- 📖 **学习价值** - 深入了解 Firecrawl 内部实现

## 网络配置说明

**重要**: Firecrawl 运行在独立的 Docker Compose 中,与 App 不在同一个网络。

### 访问方式

Firecrawl 的 API 服务会映射到宿主机端口 (默认 `3002`),App 需要通过宿主机地址访问:

#### Windows/Mac (Docker Desktop)
```env
FIRECRAWL_API_URL=http://host.docker.internal:3002
```

#### Linux
```env
FIRECRAWL_API_URL=http://localhost:3002
# 或
FIRECRAWL_API_URL=http://127.0.0.1:3002
```

### 修改 Firecrawl 端口

如果需要修改 Firecrawl 的端口,请编辑 `submodules/firecrawl/.env`:

```bash
# 创建或编辑 Firecrawl 的环境变量文件
cd submodules/firecrawl
cp .env.example .env  # 如果不存在
vim .env

# 修改以下配置:
PORT=3002              # 宿主机映射端口
INTERNAL_PORT=3002     # 容器内端口(不建议修改)
```

然后重启 Firecrawl:
```bash
docker compose down
docker compose up -d
```

### 验证连接

```bash
# 从宿主机测试
curl http://localhost:3002/health

# 从 App 容器内测试 (Windows/Mac)
docker exec -it interview-agent curl http://host.docker.internal:3002/health

# 从 App 容器内测试 (Linux)
docker exec -it interview-agent curl http://host.docker.internal:3002/health
# 如果失败,使用:
docker exec -it interview-agent curl http://172.17.0.1:3002/health  # Docker 默认网桥 IP
```

## 快速开始

### 1. 初始化子模块

```bash
git submodule update --init --recursive
```

### 2. 启动 Firecrawl

**方法 1: 直接进入 submodule 目录(推荐)**

```bash
cd submodules/firecrawl
docker compose up -d
```

**方法 2: 从项目根目录**

```bash
docker compose -f submodules/firecrawl/docker-compose.yaml up -d
```

**方法 3: 使用 CI/CD 脚本(全自动部署)**

```bash
bash deploy/ci.sh
```

CI/CD 脚本会自动:
1. ✅ 检查并克隆 Firecrawl submodule
2. ✅ 拉取最新代码 (git pull)
3. ✅ 构建 Firecrawl 镜像
4. ✅ 启动 Firecrawl 服务
5. ✅ 拉取 App 镜像
6. ✅ 启动 App 服务
7. ✅ 执行健康检查

### 3. 验证服务

```bash
# 查看 Firecrawl 状态
cd submodules/firecrawl
docker compose ps

# 查看日志
docker compose logs -f api

# 测试 API
curl http://localhost:3002/v0/test/health
```

## 常用命令

### 启动/停止

```bash
cd submodules/firecrawl

# 启动
docker compose up -d

# 停止
docker compose down

# 重启
docker compose restart

# 查看日志
docker compose logs -f

# 重新构建
docker compose up -d --build
```

### 更新代码

```bash
cd submodules/firecrawl

# 拉取最新代码
git pull origin main

# 重新构建并启动
docker compose down
docker compose up -d --build

cd ../..
```

## Git 远程仓库配置

当前 submodule 配置了双远程仓库:

```bash
cd submodules/firecrawl
git remote -v

# 输出:
# origin    https://github.com/yw610523/firecrawl.git      (你的 fork)
# upstream  https://github.com/mendableai/firecrawl.git    (官方)
```

### 同步上游更新

```bash
cd submodules/firecrawl

# 拉取上游最新代码
git fetch upstream
git merge upstream/main

# 推送到 fork
git push origin main

# 重新构建
docker compose down
docker compose up -d --build

cd ../..
```

## 自定义修改

在 fork 版本中进行修改:

```bash
# 1. 进入 submodule
cd submodules/firecrawl

# 2. 创建分支
git checkout -b my-feature

# 3. 修改代码
# ... 进行你的修改 ...

# 4. 提交并推送
git add .
git commit -m "描述修改"
git push origin my-feature

# 5. 更新主项目引用
cd ../..
git add submodules/firecrawl
git commit -m "更新 firecrawl 到自定义版本"

# 6. 重新构建
cd submodules/firecrawl
docker compose up -d --build
```

## 故障排查

### 问题 1: Submodule 未初始化

**症状:** `submodules/firecrawl` 目录为空

**解决:**
```bash
git submodule update --init --recursive
```

### 问题 2: 端口冲突

**症状:** `port is already allocated`

**解决:** 修改 `submodules/firecrawl/.env` 中的端口配置

### 问题 3: 构建失败 - 内存不足

**症状:** 构建过程中出现 "Killed"

**解决:**
- 增加 Docker 内存限制(Docker Desktop 设置)
- 或减少工作进程数: 修改 `.env` 中 `NUM_WORKERS_PER_QUEUE=4`

### 问题 4: 网络超时

**症状:** npm/pnpm 下载依赖超时

**解决:** 在 `submodules/firecrawl/apps/api` 目录下创建 `.npmrc`:
```
registry=https://registry.npmmirror.com
```

## 相关文档

- [Firecrawl 官方文档](https://docs.firecrawl.dev/)
- [主项目 README](../README.md)

---

**维护者**: yw610523  
**Fork 仓库**: https://github.com/yw610523/firecrawl.git  
**官方仓库**: https://github.com/mendableai/firecrawl.git
