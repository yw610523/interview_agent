#!/bin/bash

# CI/CD 部署脚本
# 用于 Jenkins webhook 触发后的自动部署

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Firecrawl 服务检查函数
check_firecrawl_service() {
    local firecrawl_compose="${SCRIPT_DIR}/docker-compose-firecrawl.yaml"
    
    # 检查是否启用 Firecrawl
    if [ "$FIRECRAWL_ENABLED" != "true" ]; then
        log_info "⏭️  Firecrawl 未启用，跳过检查"
        return 0
    fi
    
    log_info "🔍 Firecrawl 已启用，开始检查..."
    
    if [ ! -f "$firecrawl_compose" ]; then
        log_error "docker-compose-firecrawl.yaml 不存在!"
        exit 1
    fi
    
    # 检查是否使用官方云服务
    if [ "$USE_OFFICIAL_FIRECRAWL" = "true" ]; then
        log_info "🌐 使用官方 Firecrawl 云服务，检查连通性..."
        
        # 检查官方 API 地址连通性
        if curl -f -s --max-time 10 "https://api.firecrawl.dev/health" > /dev/null 2>&1; then
            log_info "✅ 官方 Firecrawl 云服务连通性正常"
        else
            log_error "❌ 官方 Firecrawl 云服务连通性检查失败！"
            log_error "请检查："
            log_error "  1. 网络连接是否正常"
            log_error "  2. 是否配置了正确的 FIRECRAWL_API_KEY"
            log_error "  3. 官方服务是否可用"
            exit 1
        fi
    else
        # 使用自托管 Firecrawl
        log_info "🏠 使用自托管 Firecrawl，检查配置..."
        
        # 检查 FIRECRAWL_API_URL 是否配置
        if [ -z "$FIRECRAWL_API_URL" ]; then
            log_error "❌ FIRECRAWL_API_URL 未配置！"
            log_error "请设置 FIRECRAWL_API_URL 环境变量（例如：http://localhost:3002）"
            exit 1
        fi
        
        log_info "📡 检查自托管 Firecrawl 连通性: $FIRECRAWL_API_URL"
        
        # 检查连通性
        if curl -f -s --max-time 10 "$FIRECRAWL_API_URL/health" > /dev/null 2>&1; then
            log_info "✅ 自托管 Firecrawl 连通性正常"
        else
            log_warn "⚠️  自托管 Firecrawl 无法访问，尝试启动..."
            
            # 启动 Firecrawl 容器
            log_info "🚀 启动 Firecrawl 服务..."
            cd "$SCRIPT_DIR"
            
            if docker compose -f "$firecrawl_compose" up -d; then
                log_info "✅ Firecrawl 容器启动成功"
                
                # 等待服务启动
                log_info "⏳ 等待 Firecrawl 服务就绪..."
                sleep 5
                
                # 再次检查连通性
                if curl -f -s --max-time 10 "$FIRECRAWL_API_URL/health" > /dev/null 2>&1; then
                    log_info "✅ Firecrawl 服务已就绪"
                else
                    log_error "❌ Firecrawl 服务启动后仍无法访问！"
                    log_error "请查看容器日志: docker compose -f $firecrawl_compose logs"
                    exit 1
                fi
            else
                log_error "❌ Firecrawl 容器启动失败！"
                log_error "请检查："
                log_error "  1. Docker 是否正常运行"
                log_error "  2. docker-compose-firecrawl.yaml 配置是否正确"
                log_error "  3. 端口是否被占用"
                exit 1
            fi
        fi
    fi
    
    log_info "✅ Firecrawl 配置检查完成"
}

# 步骤 1: 检查配置目录
check_config_directory() {
    log_info "步骤 1: 检查配置目录..."
    
    # 检查 config 目录是否存在
    if [ ! -d "$CONFIG_DIR" ]; then
        log_error "config/ 目录不存在！"
        exit 1
    else
        log_info "✅ config/ 目录已存在"
        
        # 统计配置文件数量
        CONFIG_COUNT=$(find "$CONFIG_DIR" -name "*.yaml" | wc -l)
        log_info "   找到 ${CONFIG_COUNT} 个 YAML 配置文件"
    fi
}

# 步骤 3: 拉取最新 App 镜像
pull_app_image() {
    log_info "步骤 3: 拉取最新 App 镜像..."
    
    # 检查是否配置了 GHCR_TOKEN（可选，公开仓库不需要）
    if [ -n "$GHCR_TOKEN" ]; then
        log_info "使用 GHCR_TOKEN 登录..."
        echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin 2>/dev/null || true
    fi
    
    # 拉取最新镜像
    if docker compose -f "${SCRIPT_DIR}/$COMPOSE_FILE" pull app; then
        log_info "✅ App 镜像拉取成功"
    else
        log_warn "⚠️  App 镜像拉取失败，将使用本地构建或已有镜像"
        log_warn "如果是首次部署，请确保已构建 App 镜像"
    fi
}

# 步骤 4: 停止旧容器
stop_old_containers() {
    log_info "步骤 4: 停止旧容器..."
    docker compose -f "${SCRIPT_DIR}/$COMPOSE_FILE" down --remove-orphans || true
    log_info "✅ 旧容器已停止"
}

# 步骤 5: 启动新容器
start_new_containers() {
    log_info "步骤 5: 启动新容器..."
    
    # 生成临时 .env 文件，将 Jenkins 环境变量传递给 Docker Compose
    local env_file="${SCRIPT_DIR}/.env.tmp"
    cat > "$env_file" <<EOF
# 自动生成的环境变量（Jenkins 传入）
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}
REDIS_PASSWORD=${REDIS_PASSWORD:-}
APP_PORT=${APP_PORT:-9023}

# Firecrawl 配置
FIRECRAWL_ENABLED=${FIRECRAWL_ENABLED:-false}
FIRECRAWL_API_URL=${FIRECRAWL_API_URL:-}
FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY:-}
FIRECRAWL_TIMEOUT=${FIRECRAWL_TIMEOUT:-60}
USE_OFFICIAL_FIRECRAWL=${USE_OFFICIAL_FIRECRAWL:-false}
FIRECRAWL_ONLY_MAIN_CONTENT=${FIRECRAWL_ONLY_MAIN_CONTENT:-true}

# LLM 配置
OPENAI_API_KEY=${OPENAI_API_KEY:-}
OPENAI_API_BASE=${OPENAI_API_BASE:-}
OPENAI_MODEL=${OPENAI_MODEL:-}
EMBEDDING_API_BASE=${EMBEDDING_API_BASE:-}
EMBEDDING_API_KEY=${EMBEDDING_API_KEY:-}
EMBEDDING_MODEL=${EMBEDDING_MODEL:-}
EMBEDDING_DIMENSION=${EMBEDDING_DIMENSION:-1024}
RERANK_ENABLED=${RERANK_ENABLED:-true}
RERANK_API_BASE=${RERANK_API_BASE:-}
RERANK_API_KEY=${RERANK_API_KEY:-}
RERANK_MODEL=${RERANK_MODEL:-}

# SMTP 配置
SMTP_SERVER=${SMTP_SERVER:-}
SMTP_PORT=${SMTP_PORT:-587}
SMTP_USER=${SMTP_USER:-}
SMTP_PASSWORD=${SMTP_PASSWORD:-}
EOF
    
    log_info "✅ 已生成临时环境变量文件: $env_file"
    
    # 使用 --env-file 传递环境变量
    docker compose -f "${SCRIPT_DIR}/$COMPOSE_FILE" --env-file "$env_file" up -d
    
    # 清理临时文件
    rm -f "$env_file"
    
    if [ $? -eq 0 ]; then
        log_info "✅ 容器启动成功"
    else
        log_error "❌ 容器启动失败！"
        exit 1
    fi
}

# 步骤 6: 健康检查
health_check() {
    log_info "步骤 6: 执行健康检查..."
    sleep 10
    
    MAX_RETRIES=5
    RETRY_COUNT=0
    IS_HEALTHY=false
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$IS_HEALTHY" = false ]; do
        if curl -f http://localhost:${APP_PORT:-9023}/ > /dev/null 2>&1; then
            IS_HEALTHY=true
            log_info "✅ 健康检查通过"
        else
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
                log_error "❌ 健康检查失败，服务可能未正常启动"
                log_error "请查看容器日志: docker compose logs app"
                exit 1
            fi
            log_warn "⏳ 健康检查失败，重试 ${RETRY_COUNT}/${MAX_RETRIES}..."
            sleep 5
        fi
    done
}

# 步骤 7: 清理旧镜像
cleanup_old_images() {
    log_info "步骤 7: 清理旧镜像..."
    docker image prune -f > /dev/null 2>&1 || true
    log_info "✅ 清理完成"
}

# 获取脚本所在目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 配置文件路径（使用 config/ 目录下的多个 YAML 文件）
CONFIG_DIR="${PROJECT_DIR}/config"

# 确定使用的 docker-compose 文件（可通过 COMPOSE_FILE 环境变量指定）
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
COMPOSE_FILE_PATH="${SCRIPT_DIR}/${COMPOSE_FILE}"

log_info "========================================="
log_info "开始部署 Interview Agent"
log_info "========================================="

# 执行部署步骤
check_config_directory
check_firecrawl_service
pull_app_image
stop_old_containers
start_new_containers
health_check
cleanup_old_images

log_info "========================================="
log_info "🎉 部署成功完成！"
log_info "========================================="
log_info "访问地址:"
log_info "  - 前端界面: http://localhost:9023"
log_info "  - API 文档: http://localhost:9023/docs"
log_info ""
log_info "查看日志:"
log_info "  cd $SCRIPT_DIR && docker compose -f $COMPOSE_FILE logs -f app"
log_info "========================================="

exit 0
