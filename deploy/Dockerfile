# 前端构建阶段
FROM docker.m.daocloud.io/library/node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# 复制前端文件并安装依赖
COPY frontend/package*.json ./
RUN npm install --production=false

# 复制前端源代码并构建
COPY frontend/ ./
RUN npm run build

# 最终运行阶段 - 使用 Python slim 镜像 + 安装 Nginx
FROM docker.m.daocloud.io/library/python:3.10-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 安装 Nginx
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 先复制 requirements.txt 并安装依赖
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制后端代码和前端构建产物
COPY app/ ./app/
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
