# GitHub Actions 快速参考

## 📌 工作流概览

| 工作流 | 文件 | 触发条件 | 用途 |
|--------|------|---------|------|
| CI Pipeline | `ci.yml` | push/PR | 代码检查、测试、构建 |
| Docker Publish | `docker-publish.yml` | push main/tag/release | 构建并推送 Docker 镜像 |
| Deploy | `deploy.yml` | manual/release | 部署到服务器 |

---

## 🚀 常用操作

### 1. 触发 CI 检查

```bash
# 提交代码自动触发
git add .
git commit -m "feat: your changes"
git push origin feature-branch

# 创建 PR 到 main 分支也会自动触发
```

### 2. 发布新版本

```bash
# 方法一：创建版本标签
git tag v1.0.0
git push origin v1.0.0

# 方法二：在 GitHub 上创建 Release
# 访问: https://github.com/username/interview_agent/releases/new
```

### 3. 手动部署

1. 访问 **Actions** 标签页
2. 选择 **Deploy to Production**
3. 点击 **Run workflow**
4. 选择环境和版本
5. 点击运行

---

## 🔐 Secrets 配置清单

### 必需配置

```bash
# 在 GitHub Settings → Secrets and variables → Actions 中添加

OPENAI_API_KEY=sk-your-api-key
```

### 部署相关（可选）

```bash
DEPLOY_SSH_KEY=-----BEGIN OPENSSH PRIVATE KEY-----...
OPENAI_API_BASE=https://api.openai.com/v1
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your-email@qq.com
SMTP_PASSWORD=your-smtp-password
SITEMAP_URL=https://example.com/sitemap.xml
```

### Variables 配置

```bash
# 在 Variables 标签页添加

DEPLOY_HOST=your-server.com
DEPLOY_USER=ubuntu
DEPLOY_PORT=22
DEPLOYMENT_URL=https://your-app.com
```

---

## 📊 查看构建状态

### 网页查看
访问：`https://github.com/username/interview_agent/actions`

### 添加徽章到 README

```markdown
![CI](https://github.com/username/interview_agent/actions/workflows/ci.yml/badge.svg)
![Docker](https://github.com/username/interview_agent/actions/workflows/docker-publish.yml/badge.svg)
```

---

## 🐳 Docker 镜像使用

### 拉取镜像

```bash
# 最新版本
docker pull ghcr.io/username/interview_agent:latest

# 指定版本
docker pull ghcr.io/username/interview_agent:v1.0.0
```

### 运行容器

```bash
docker run -d \
  -p 80:80 \
  -e OPENAI_API_KEY=your-key \
  --name interview-agent \
  ghcr.io/username/interview_agent:latest
```

### 使用 docker-compose

```yaml
version: '3.8'
services:
  app:
    image: ghcr.io/username/interview_agent:latest
    ports:
      - "80:80"
    env_file:
      - .env
    depends_on:
      - redis
  
  redis:
    image: redis/redis-stack:latest
    ports:
      - "6379:6379"
```

---

## 🔧 故障排查

### CI 失败怎么办？

1. **查看日志**
   - 进入 Actions 页面
   - 点击失败的工作流
   - 展开失败的步骤查看详细错误

2. **常见问题**
   ```bash
   # 本地运行测试
   python -m pytest tests/ -v
   
   # 检查代码格式
   flake8 app/ tests/
   black --check app/ tests/
   
   # 前端构建测试
   cd frontend && npm run build
   ```

3. **重试工作流**
   - 在 Actions 页面点击 **Re-run jobs**

### Docker 构建失败？

```bash
# 本地构建测试
docker build -f deploy/Dockerfile -t test-image .

# 查看构建日志
docker build -f deploy/Dockerfile -t test-image . --progress=plain
```

### 部署失败？

```bash
# SSH 连接到服务器检查
ssh user@server

# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 重启服务
docker-compose restart
```

---

## 💡 最佳实践

### 1. 分支策略

```
main          - 生产环境（稳定版本）
develop       - 开发分支
feature/*     - 功能分支
hotfix/*      - 紧急修复
```

### 2. 版本命名

遵循语义化版本（SemVer）：
- `v1.0.0` - 主版本.次版本.修订版本
- 主版本：不兼容的 API 修改
- 次版本：向下兼容的功能新增
- 修订版本：向下兼容的问题修正

### 3. Commit 规范

```bash
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式
refactor: 重构
test: 测试相关
chore: 构建过程或辅助工具变动
```

### 4. 安全建议

- ✅ 使用 GitHub Secrets 管理敏感信息
- ✅ 定期轮换 API 密钥
- ✅ 启用双因素认证（2FA）
- ✅ 审查 PR 后再合并
- ❌ 不要在代码中硬编码密钥
- ❌ 不要提交 `.env` 文件

---

## 📚 相关文档

- [详细配置指南](WORKFLOWS_GUIDE.md)
- [部署说明](../deploy/CICD_README.md)
- [GitHub Actions 官方文档](https://docs.github.com/en/actions)

---

## 🆘 获取帮助

遇到问题？

1. 查看工作流运行日志
2. 检查 Secrets 配置是否正确
3. 参考详细配置指南
4. 提交 Issue 并提供：
   - 错误截图
   - 相关日志
   - 复现步骤
