# 多阶段构建 - 前端构建阶段
FROM docker.m.daocloud.io/library/node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# 复制前端文件并安装依赖
COPY frontend/package*.json ./
RUN npm install --production=false

# 复制前端源代码并构建
COPY frontend/ ./
RUN npm run build

# 后端构建阶段
FROM python:3.10-slim AS backend-builder

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制 Python 依赖文件并安装
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 最终运行阶段 - 使用 Nginx 提供前端和反向代理
FROM docker.m.daocloud.io/library/nginx:alpine

# 安装必要的工具
RUN apk add --no-cache python3 py3-pip curl

# 复制后端代码和依赖
COPY --from=backend-builder /app /app
COPY --from=backend-builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# 复制前端构建产物到 Nginx
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# 配置 Nginx
RUN rm /etc/nginx/conf.d/default.conf
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf

# 创建启动脚本
COPY deploy/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# 暴露端口（Nginx 默认 80）
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# 启动命令
ENTRYPOINT ["/docker-entrypoint.sh"]
