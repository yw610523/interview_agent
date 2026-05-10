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

# 获取脚本所在目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_DIR}/config.yaml"
CONFIG_TEMPLATE="${PROJECT_DIR}/config.yaml.template"

# 确定使用的 docker-compose 文件（可通过 COMPOSE_FILE 环境变量指定）
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
COMPOSE_FILE_PATH="${SCRIPT_DIR}/${COMPOSE_FILE}"

log_info "========================================="
log_info "开始部署 Interview Agent"
log_info "========================================="

# 步骤 1: 检查配置文件
log_info "步骤 1: 检查配置文件..."

# 检查 config.yaml
if [ ! -f "$CONFIG_FILE" ]; then
    log_warn "config.yaml 文件不存在"
    
    if [ -f "$CONFIG_TEMPLATE" ]; then
        log_info "从 config.yaml.template 复制创建 config.yaml..."
        cp "$CONFIG_TEMPLATE" "$CONFIG_FILE"
        log_info "✅ 已创建 config.yaml 文件"
        log_warn "⚠️  请编辑 $CONFIG_FILE 并填写必要的配置项（如 API Keys）"
        
        # 提示用户编辑配置文件
        log_warn ""
        log_warn "重要提示："
        log_warn "  1. 编辑 config.yaml 文件"
        log_warn "  2. 至少配置以下关键项："
        log_warn "     - llm.openai_api_key (OpenAI API 密钥)"
        log_warn "     - redis.url (Redis 连接地址)"
        log_warn "     - smtp.user 和 smtp.password (邮件配置，如需使用)"
        log_warn "  3. 保存后重新运行部署脚本"
        log_warn ""
        
        # 不再自动退出，允许继续部署（用户可以稍后编辑）
        log_warn "⚠️  如果现在不编辑，应用可能无法正常运行"
    else
        log_error "config.yaml.template 模板文件也不存在！"
        exit 1
    fi
else
    log_info "✅ config.yaml 文件已存在"
fi

# 步骤 2: 启动 Firecrawl 服务（使用 Docker Compose）
log_info "步骤 2: 检查并启动 Firecrawl..."

# Firecrawl 配置文件路径
FIRECRAWL_COMPOSE="${SCRIPT_DIR}/docker-compose-firecrawl.yaml"
FIRECRAWL_ENV_FILE="${PROJECT_DIR}/.env.firecrawl"

if [ ! -f "$FIRECRAWL_COMPOSE" ]; then
    log_error "docker-compose-firecrawl.yaml 不存在!"
    exit 1
fi

# 检查环境变量文件
if [ ! -f "$FIRECRAWL_ENV_FILE" ]; then
    log_warn ".env.firecrawl 文件不存在，使用默认配置"
    log_warn "如需自定义私有仓库地址，请复制 deploy/.env.firecrawl.template 为 .env.firecrawl"
else
    log_info "✅ 检测到 .env.firecrawl 配置文件"
fi

# 智能检测：检查 Firecrawl 是否需要重启
NEED_RESTART=false

# 检查容器是否运行
if docker compose -f "$FIRECRAWL_COMPOSE" ps api 2>/dev/null | grep -q "Up"; then
    log_info "✅ Firecrawl 容器正在运行"
else
    log_warn "⚠️  Firecrawl 容器未运行，需要启动"
    NEED_RESTART=true
fi

# 根据检测结果决定是否启动
if [ "$NEED_RESTART" = true ]; then
    log_info "启动 Firecrawl 服务..."
    cd "$SCRIPT_DIR"
    
    # 使用 --env-file 加载环境变量
    if [ -f "$FIRECRAWL_ENV_FILE" ]; then
        docker compose -f "$FIRECRAWL_COMPOSE" --env-file "$FIRECRAWL_ENV_FILE" up -d
    else
        docker compose -f "$FIRECRAWL_COMPOSE" up -d
    fi
    
    log_info "✅ Firecrawl 启动完成"
else
    log_info "⏭️  跳过 Firecrawl 启动（容器已在运行）"
fi

log_info "✅ Firecrawl 部署完成"

# 步骤 3: 拉取最新 App 镜像
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

# 步骤 4: 停止旧容器
log_info "步骤 4: 停止旧容器..."
docker compose -f "${SCRIPT_DIR}/$COMPOSE_FILE" down --remove-orphans || true
log_info "✅ 旧容器已停止"

# 步骤 5: 启动新容器
log_info "步骤 5: 启动新容器..."
docker compose -f "${SCRIPT_DIR}/$COMPOSE_FILE" up -d

if [ $? -eq 0 ]; then
    log_info "✅ 容器启动成功"
else
    log_error "❌ 容器启动失败！"
    exit 1
fi

# 步骤 6: 验证 config.yaml 挂载
log_info "步骤 6: 验证配置文件挂载..."
sleep 3

# 检查容器内是否存在 config.yaml
if docker exec interview-agent test -f /app/config.yaml 2>/dev/null; then
    log_info "✅ config.yaml 已成功挂载到容器"
    
    # 显示配置文件大小，确认内容已加载
    CONFIG_SIZE=$(docker exec interview-agent wc -c < /app/config.yaml 2>/dev/null || echo "unknown")
    log_info "   配置文件大小: ${CONFIG_SIZE} bytes"
else
    log_warn "⚠️  config.yaml 未挂载到容器"
    log_warn "   请确保:"
    log_warn "   1. config.yaml 文件存在于项目根目录"
    log_warn "   2. docker-compose.yml 中包含 volume 映射"
fi

# 步骤 7: 健康检查
log_info "步骤 7: 执行健康检查..."
sleep 10

MAX_RETRIES=5
RETRY_COUNT=0
IS_HEALTHY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$IS_HEALTHY" = false ]; do
    if curl -f http://localhost:9023/ > /dev/null 2>&1; then
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

# 步骤 8: 清理旧镜像
log_info "步骤 8: 清理旧镜像..."
docker image prune -f > /dev/null 2>&1 || true
log_info "✅ 清理完成"

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
