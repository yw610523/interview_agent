#!/bin/sh
set -e

echo "启动 Interview Agent 应用..."

# 在后台启动 FastAPI 后端服务
echo "启动后端 API 服务（端口 8000）..."
cd /app
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# 等待后端服务启动
echo "等待后端服务启动..."
sleep 3

# 检查后端服务是否正常运行
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "错误：后端服务启动失败"
    exit 1
fi

echo "后端服务已启动 (PID: $BACKEND_PID)"

# 启动 Nginx（前台运行）
echo "启动 Nginx（端口 80）..."
exec nginx -g 'daemon off;'
