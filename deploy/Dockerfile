# 多阶段构建 - 前端构建阶段
FROM docker.m.daocloud.io/library/node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# 复制前端文件并安装依赖
COPY frontend/package*.json ./
RUN npm install --production=false

# 复制前端源代码并构建
COPY frontend/ ./
RUN npm run build

# 后端构建阶段 - 使用完整Python镜像（预装编译工具）
FROM docker.m.daocloud.io/library/python:3.10 AS backend-builder

# 设置工作目录和环境变量
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 先复制并安装 Python 依赖(利用 Docker 层缓存)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 再复制应用代码(代码变更不会导致依赖重新安装)
COPY app/ ./app/

# 最终运行阶段 - 使用完整 Python 镜像 + 安装 Nginx
FROM docker.m.daocloud.io/library/python:3.10-slim

# 安装 Nginx
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制后端代码、依赖和前端构建产物
COPY --from=backend-builder /app /app
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# 配置 Nginx 和启动脚本
RUN rm /etc/nginx/sites-enabled/default
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# 暴露端口（默认 9023）
EXPOSE 9023

# 健康检查（使用wget代替curl，nginx:alpine自带wget）
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:9023/ || exit 1

# 启动命令
ENTRYPOINT ["/docker-entrypoint.sh"]
