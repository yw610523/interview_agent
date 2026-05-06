# GitHub Actions 配置说明

## 📋 概述

本项目已配置完整的 GitHub Actions CI/CD 自动化流程，包括代码质量检查、单元测试、Docker 镜像构建和自动部署。

## 🗂️ 工作流文件

### 1. CI Pipeline (`.github/workflows/ci.yml`)

**触发条件：**
- 推送到 `main` 或 `develop` 分支
- 创建 Pull Request 到 `main` 分支

**执行任务：**
1. **代码质量检查**
   - flake8 代码风格检查
   - black 代码格式检查

2. **单元测试**
   - 运行 pytest 测试套件
   - 生成代码覆盖率报告
   - 最低覆盖率要求：60%
   - 使用 Redis 服务容器进行测试

3. **前端构建**
   - 安装 Node.js 依赖
   - 构建 Vue.js 前端应用
   - 上传构建产物

4. **Docker 镜像构建**
   - 构建 Docker 镜像（不推送）
   - 验证镜像可用性

---

### 2. Docker Publish (`.github/workflows/docker-publish.yml`)

**触发条件：**
- 推送到 `main` 分支
- 创建版本标签（如 `v1.0.0`）
- 发布 GitHub Release

**功能：**
- 构建多平台 Docker 镜像（linux/amd64, linux/arm64）
- 推送到 GitHub Container Registry (GHCR)
- 自动生成镜像标签：
  - `latest` - main 分支最新构建
  - `v1.0.0` - 语义化版本标签
  - `1.0` - 次要版本标签
  - `<commit-sha>` - Git commit SHA

**镜像地址：**
```
ghcr.io/<username>/interview_agent:latest
```

---

### 3. Deploy to Production (`.github/workflows/deploy.yml`)

**触发条件：**
- 手动触发（workflow_dispatch）
- 发布 GitHub Release

**功能：**
- 支持多环境部署（production/staging）
- 通过 SSH 自动部署到远程服务器
- 健康检查和部署验证
- 生成部署摘要报告

---

## 🔐 配置 Secrets 和 Variables

### GitHub Secrets 配置

在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中配置以下密钥：

#### 必需配置

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | `sk-...` |

#### 可选配置（如需自动部署）

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `DEPLOY_SSH_KEY` | SSH 私钥（用于连接部署服务器） | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `OPENAI_API_BASE` | OpenAI API 基础 URL | `https://api.openai.com/v1` |
| `SMTP_SERVER` | SMTP 服务器地址 | `smtp.qq.com` |
| `SMTP_PORT` | SMTP 端口 | `587` |
| `SMTP_USER` | SMTP 用户名 | `your-email@qq.com` |
| `SMTP_PASSWORD` | SMTP 密码 | `your-smtp-password` |
| `SITEMAP_URL` | Sitemap URL | `https://example.com/sitemap.xml` |

### GitHub Variables 配置

在 **Settings → Secrets and variables → Actions → Variables** 中配置：

| Variable 名称 | 说明 | 示例 |
|--------------|------|------|
| `DEPLOY_HOST` | 部署服务器主机地址 | `your-server.com` |
| `DEPLOY_USER` | 部署服务器用户名 | `ubuntu` |
| `DEPLOY_PORT` | SSH 端口（默认 22） | `22` |
| `DEPLOYMENT_URL` | 应用访问 URL（用于健康检查） | `https://your-app.com` |

---

## 🚀 使用指南

### 日常开发流程

1. **提交代码**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin feature-branch
   ```

2. **创建 Pull Request**
   - 自动触发 CI Pipeline
   - 所有检查通过后才能合并

3. **合并到 main 分支**
   - 自动触发 Docker 镜像构建
   - 镜像推送到 GHCR

### 发布新版本

1. **创建版本标签**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **或创建 GitHub Release**
   - 在 GitHub 上创建新的 Release
   - 自动触发 Docker 构建和部署

### 手动部署

1. 进入 GitHub 仓库的 **Actions** 标签
2. 选择 **Deploy to Production** 工作流
3. 点击 **Run workflow**
4. 选择部署环境和版本
5. 点击 **Run workflow** 开始部署

---

## 📊 查看构建状态

### GitHub Actions 页面
访问：`https://github.com/<username>/interview_agent/actions`

### 构建徽章

将以下代码添加到 README.md 中显示构建状态：

```markdown
![CI Pipeline](https://github.com/<username>/interview_agent/actions/workflows/ci.yml/badge.svg)
![Docker Publish](https://github.com/<username>/interview_agent/actions/workflows/docker-publish.yml/badge.svg)
```

---

## 🔧 自定义配置

### 修改 Python/Node 版本

编辑 `.github/workflows/ci.yml`：
```yaml
env:
  PYTHON_VERSION: '3.11'  # 修改 Python 版本
  NODE_VERSION: '18'      # 修改 Node.js 版本
```

### 调整测试覆盖率要求

编辑 `.github/workflows/ci.yml`：
```yaml
--cov-fail-under=60  # 修改最低覆盖率百分比
```

### 添加新的环境变量

在相应的工作流中添加：
```yaml
env:
  YOUR_VAR: your-value
```

或在步骤中使用：
```yaml
- name: Set environment variable
  run: echo "YOUR_VAR=value" >> $GITHUB_ENV
```

---

## 🐛 故障排查

### 1. 工作流失败

- 查看 Actions 标签页中的详细日志
- 检查是否缺少必需的 Secrets
- 验证依赖包版本兼容性

### 2. Docker 构建失败

- 检查 `deploy/Dockerfile` 是否正确
- 确认所有依赖都已包含在 `requirements.txt`
- 查看构建日志中的错误信息

### 3. 部署失败

- 验证 SSH 密钥配置正确
- 检查服务器防火墙设置
- 确认 Docker 和 docker-compose 已安装
- 查看部署日志：
  ```bash
  ssh user@server "docker-compose logs -f"
  ```

### 4. 测试失败

- 本地运行测试确认问题：
  ```bash
  python -m pytest tests/ -v
  ```
- 检查 Redis 服务是否正常运行
- 验证环境变量配置

---

## 💡 最佳实践

1. **保护敏感信息**
   - 永远不要在代码中硬编码密钥
   - 使用 GitHub Secrets 管理所有敏感数据
   - 定期轮换密钥

2. **分支策略**
   - `main` - 生产环境稳定版本
   - `develop` - 开发分支
   - `feature/*` - 功能分支

3. **版本管理**
   - 使用语义化版本（SemVer）
   - 每次发布创建 Git 标签
   - 编写清晰的 Release Notes

4. **监控和维护**
   - 定期检查构建成功率
   - 清理旧的 Docker 镜像
   - 更新 Actions 版本以获得最新功能

---

## 📚 相关资源

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [Docker Buildx 文档](https://docs.docker.com/buildx/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

---

## 🆘 获取帮助

如遇到问题：
1. 查看工作流运行日志
2. 检查 Secrets 和 Variables 配置
3. 参考项目文档：[CICD_README.md](../deploy/CICD_README.md)
4. 提交 Issue 并提供详细的错误信息
