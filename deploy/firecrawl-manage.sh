#!/bin/bash
# Firecrawl 源码构建管理脚本
# 使用 fork 版本: https://github.com/yw610523/firecrawl.git

set -e

# 直接使用 submodule 中的 docker-compose.yaml
SUBMODULE_DIR="submodules/firecrawl"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    echo "Firecrawl 源码构建管理脚本"
    echo "使用 fork 版本: https://github.com/yw610523/firecrawl.git"
    echo ""
    echo "用法: $0 <命令>"
    echo ""
    echo "命令:"
    echo "  init        初始化 firecrawl 子模块"
    echo "  build       构建 firecrawl 镜像"
    echo "  start       启动所有服务"
    echo "  stop        停止所有服务"
    echo "  restart     重启所有服务"
    echo "  logs        查看日志(实时)"
    echo "  status      查看服务状态"
    echo "  update      更新 firecrawl 代码并重新构建"
    echo "  sync-upstream 从官方仓库同步最新代码"
    echo "  clean       清理构建缓存和容器"
    echo "  help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 init      # 首次使用,初始化子模块"
    echo "  $0 build     # 构建 firecrawl 镜像"
    echo "  $0 start     # 启动服务"
    echo "  $0 update    # 更新到最新版本"
    echo "  $0 sync-upstream  # 同步官方仓库更新"
}

check_submodule() {
    if [ ! -f "${SUBMODULE_DIR}/docker-compose.yaml" ]; then
        log_error "Firecrawl 子模块未初始化!"
        log_info "请先运行: $0 init"
        exit 1
    fi
}

case "$1" in
    init)
        log_info "初始化 Firecrawl 子模块..."
        git submodule update --init --recursive
        log_info "✅ 子模块初始化完成"
        ;;
    
    build)
        check_submodule
        log_info "构建 Firecrawl 镜像(这可能需要几分钟)..."
        cd "$SUBMODULE_DIR"
        docker compose build api
        cd ..
        log_info "✅ 构建完成"
        ;;
    
    start)
        check_submodule
        log_info "启动 Firecrawl 服务..."
        cd "$SUBMODULE_DIR"
        docker compose up -d
        cd ..
        log_info "✅ 服务已启动"
        log_info "访问地址:"
        log_info "  - Firecrawl API: http://localhost:3002"
        ;;
    
    stop)
        log_info "停止 Firecrawl 服务..."
        cd "$SUBMODULE_DIR"
        docker compose down
        cd ..
        log_info "✅ 服务已停止"
        ;;
    
    restart)
        check_submodule
        log_info "重启 Firecrawl 服务..."
        cd "$SUBMODULE_DIR"
        docker compose restart
        cd ..
        log_info "✅ 服务已重启"
        ;;
    
    logs)
        check_submodule
        log_info "显示实时日志 (Ctrl+C 退出)..."
        cd "$SUBMODULE_DIR"
        docker compose logs -f
        ;;
    
    status)
        check_submodule
        log_info "服务状态:"
        cd "$SUBMODULE_DIR"
        docker compose ps
        ;;
    
    update)
        check_submodule
        log_info "更新 Firecrawl 代码(从 fork 仓库)..."
        cd "$SUBMODULE_DIR"
        git pull origin main
        log_info "重新构建镜像..."
        docker compose down
        docker compose up -d --build
        cd ..
        log_info "✅ 更新完成"
        ;;
    
    sync-upstream)
        check_submodule
        log_warn "这将从官方仓库同步最新代码并合并到当前分支"
        read -p "确认继续? (y/N): " confirm
        if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
            log_info "进入 submodule 目录..."
            cd "$SUBMODULE_DIR"
            
            log_info "拉取上游最新代码..."
            git fetch upstream
            
            log_info "合并上游更改..."
            git merge upstream/main || {
                log_error "合并冲突!请手动解决冲突后继续"
                log_info "解决冲突后运行: git commit && cd .."
                exit 1
            }
            
            log_info "推送到 fork 仓库..."
            git push origin main
            
            log_info "重新构建镜像..."
            docker compose down
            docker compose up -d --build
            cd ..
            
            log_info "✅ 同步完成"
        else
            log_info "取消同步"
        fi
        ;;
    
    clean)
        log_warn "这将删除所有 Firecrawl 容器和构建缓存"
        read -p "确认继续? (y/N): " confirm
        if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
            cd "$SUBMODULE_DIR"
            docker compose down -v --rmi all
            cd ..
            docker system prune -f
            log_info "✅ 清理完成"
        else
            log_info "取消清理"
        fi
        ;;
    
    help|--help|-h)
        show_help
        ;;
    
    *)
        log_error "未知命令: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
