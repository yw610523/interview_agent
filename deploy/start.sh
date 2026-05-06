#!/bin/bash
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  Interview Agent 快速启动脚本${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    echo "请先安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# 检查 .env 文件是否存在
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}警告: .env 文件不存在${NC}"
    if [ -f ".env.template" ]; then
        echo "从 .env.template 创建 .env 文件..."
        cp .env.template .env
        echo -e "${YELLOW}请编辑 .env 文件并配置必要的环境变量（特别是 OPENAI_API_KEY）${NC}"
        echo ""
        read -p "按回车键继续..." 
    else
        echo -e "${RED}错误: 找不到 .env.template 文件${NC}"
        exit 1
    fi
fi

# 确定使用的 docker-compose 命令
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo -e "${GREEN}步骤 1/3: 构建 Docker 镜像...${NC}"
$DOCKER_COMPOSE build

echo ""
echo -e "${GREEN}步骤 2/3: 启动服务...${NC}"
$DOCKER_COMPOSE up -d

echo ""
echo -e "${GREEN}步骤 3/3: 检查服务状态...${NC}"
sleep 5

# 检查服务状态
if $DOCKER_COMPOSE ps | grep -q "Up"; then
    echo -e "${GREEN}✓ 服务启动成功！${NC}"
    echo ""
    echo -e "${BLUE}访问地址:${NC}"
    echo "  - 前端界面: http://localhost"
    echo "  - API 文档: http://localhost/docs"
    echo "  - RedisInsight: http://localhost:8001"
    echo ""
    echo -e "${BLUE}常用命令:${NC}"
    echo "  查看日志:     $DOCKER_COMPOSE logs -f"
    echo "  停止服务:     $DOCKER_COMPOSE down"
    echo "  重启服务:     $DOCKER_COMPOSE restart"
    echo "  查看状态:     $DOCKER_COMPOSE ps"
    echo ""
else
    echo -e "${RED}✗ 服务启动失败，请检查日志${NC}"
    echo ""
    echo "查看日志: $DOCKER_COMPOSE logs"
    exit 1
fi
