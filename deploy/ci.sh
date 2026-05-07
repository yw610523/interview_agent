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
ENV_FILE="${PROJECT_DIR}/.env"
ENV_TEMPLATE="${PROJECT_DIR}/.env.template"

log_info "========================================="
log_info "开始部署 Interview Agent"
log_info "========================================="

# 步骤 1: 检查 .env 文件是否存在
log_info "步骤 1: 检查 .env 配置文件..."

if [ ! -f "$ENV_FILE" ]; then
    log_warn ".env 文件不存在，从 .env.template 复制..."
    
    if [ ! -f "$ENV_TEMPLATE" ]; then
        log_error ".env.template 模板文件也不存在！"
        exit 1
    fi
    
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    log_info "已创建 .env 文件，请编辑该文件并填写必要的配置项"
    
    # 检查必要的环境变量
    MISSING_VARS=()
    
    # 读取 .env 文件，检查必填项
    while IFS='=' read -r key value; do
        # 跳过注释和空行
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        
        # 去除空格
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        
        # 检查必填项（根据你的实际需求调整）
        case "$key" in
            "OPENAI_API_KEY")
                if [ -z "$value" ]; then
                    MISSING_VARS+=("$key")
                fi
                ;;
        esac
    done < "$ENV_FILE"
    
    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        log_error "以下必需的环境变量未配置："
        for var in "${MISSING_VARS[@]}"; do
            log_error "  - $var"
        done
        log_error ""
        log_error "请编辑 .env 文件并填写上述变量："
        log_error "  vim $ENV_FILE"
        log_error ""
        log_error "然后重新运行部署脚本或手动执行："
        log_error "  cd $SCRIPT_DIR && docker-compose up -d"
        exit 1
    fi
    
    log_info "✅ .env 文件已创建，所有必需变量已配置"
else
    log_info "✅ .env 文件已存在"
fi

# 步骤 2: 进入部署目录
log_info "步骤 2: 进入部署目录..."
cd "$SCRIPT_DIR"

if [ ! -f "docker-compose.yml" ]; then
    log_error "docker-compose.yml 文件不存在！"
    exit 1
fi

log_info "✅ 部署目录: $SCRIPT_DIR"

# 步骤 3: 拉取最新镜像（可选，如果需要从远程仓库拉取）
log_info "步骤 3: 拉取最新 Docker 镜像..."
if docker-compose pull app 2>/dev/null; then
    log_info "✅ 镜像拉取成功"
else
    log_warn "镜像拉取失败或不需要拉取，将继续使用本地镜像"
fi

# 步骤 4: 停止旧容器
log_info "步骤 4: 停止旧容器..."
docker-compose down --remove-orphans || true
log_info "✅ 旧容器已停止"

# 步骤 5: 启动新容器
log_info "步骤 5: 启动新容器..."
docker-compose up -d

if [ $? -eq 0 ]; then
    log_info "✅ 容器启动成功"
else
    log_error "❌ 容器启动失败！"
    exit 1
fi

# 步骤 6: 健康检查
log_info "步骤 6: 执行健康检查..."
sleep 10

MAX_RETRIES=5
RETRY_COUNT=0
IS_HEALTHY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$IS_HEALTHY" = false ]; do
    if curl -f http://localhost:80/ > /dev/null 2>&1; then
        IS_HEALTHY=true
        log_info "✅ 健康检查通过"
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            log_error "❌ 健康检查失败，服务可能未正常启动"
            log_error "请查看容器日志: docker-compose logs app"
            exit 1
        fi
        log_warn "⏳ 健康检查失败，重试 ${RETRY_COUNT}/${MAX_RETRIES}..."
        sleep 5
    fi
done

# 步骤 7: 清理旧镜像
log_info "步骤 7: 清理旧镜像..."
docker image prune -f > /dev/null 2>&1 || true
log_info "✅ 清理完成"

log_info "========================================="
log_info "🎉 部署成功完成！"
log_info "========================================="
log_info "访问地址:"
log_info "  - 前端界面: http://localhost:80"
log_info "  - API 文档: http://localhost:80/docs"
log_info ""
log_info "查看日志:"
log_info "  cd $SCRIPT_DIR && docker-compose logs -f app"
log_info "========================================="

exit 0
