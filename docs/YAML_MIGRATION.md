# YAML配置迁移指南

## 📋 概述

本次重构将系统配置统一为YAML格式，替代原来的`.env` + `crawler_config.json`分散配置方式。

## ✅ 已完成的修改

### 1. 新增文件

- `app/config/config.yaml` - 主配置文件（从现有配置迁移）
- `app/config/config.example.yaml` - 配置模板（提交到Git）
- `app/config/config_manager.py` - 统一配置管理器

### 2. 依赖更新

- `requirements.txt` - 添加 `pyyaml` 依赖

### 3. 配置文件结构

```yaml
app:           # 应用配置
llm:           # LLM配置
redis:         # Redis配置
email:         # 邮件配置
crawler:       # 爬虫配置
scheduler:     # 定时任务配置
```

## 🔧 需要手动修改的代码文件

### 后端文件（Python）

#### 1. app/main.py

**需要修改的部分：**

```python
# 导入配置管理器
from app.config.config_manager import get_config

# 替换所有环境变量读取
# 之前：
import os
api_key = os.getenv("OPENAI_API_KEY")

# 之后：
config = get_config()
api_key = config.get("llm.api_key")

# 替换CrawlerConfig加载
# 之前：
from app.config.crawler_config import CrawlerConfig
config = CrawlerConfig.from_json(str(DEFAULT_CONFIG_PATH))

# 之后：
config = get_config()
crawler_config_dict = config.get_crawler_config()
# 如果需要CrawlerConfig对象：
from app.config.crawler_config import CrawlerConfig
crawler_config = CrawlerConfig.from_dict(crawler_config_dict)
```

**具体修改位置：**
- Line ~50: 初始化LLM服务时读取配置
- Line ~121: run_crawler()函数中加载爬虫配置
- Line ~1066-1110: get_crawler_config()和update_crawler_config() API
- Line ~1152-1193: update_llm_config() API
- Line ~1196-1230: update_redis_config() API
- Line ~1233-1272: update_email_config() API
- Line ~1312-1369: get_system_config() API

#### 2. app/services/llm_service.py

```python
# 导入配置管理器
from app.config.config_manager import get_config

# 在 _init_clients() 方法中
def _init_clients(self):
    config = get_config()
    llm_config = config.get_llm_config()
    
    self.api_key = llm_config.get("api_key", "")
    self.api_base = llm_config.get("api_base", "")
    self.model = llm_config.get("model", "gpt-4o-mini")
    # ... 其他配置
```

#### 3. app/services/vector_service.py

```python
# 导入配置管理器
from app.config.config_manager import get_config

# 在 __init__ 或连接Redis时
config = get_config()
redis_config = config.get_redis_config()
redis_url = redis_config.get("url", "redis://localhost:6379/0")
```

#### 4. app/services/email_service.py

```python
# 导入配置管理器
from app.config.config_manager import get_config

# 在发送邮件时读取配置
config = get_config()
email_config = config.get_email_config()
smtp_server = email_config.get("smtp_server")
# ... 其他配置
```

#### 5. app/services/sitemap_crawler.py

```python
# 导入配置管理器
from app.config.config_manager import get_config

# 在需要使用配置的地方
config = get_config()
crawler_config = config.get_crawler_config()
timeout = crawler_config.get("timeout", 30)
```

#### 6. app/services/url_filter.py

```python
# 导入配置管理器
from app.config.config_manager import get_config

# 在初始化时
config = get_config()
crawler_config = config.get_crawler_config()
include_patterns = crawler_config.get("url_include_patterns", [])
exclude_patterns = crawler_config.get("url_exclude_patterns", [])
```

#### 7. app/services/config_hot_reload.py

```python
# 简化热加载逻辑
from app.config.config_manager import get_config

def reload_llm_config(self) -> bool:
    try:
        logger.info("开始热加载模型配置...")
        # 重新加载配置
        config = get_config()
        config.reload()
        
        # 重新初始化LLM服务
        if self.llm_service:
            self.llm_service._init_clients()
            logger.info("✅ LLM服务配置已更新")
            return True
    except Exception as e:
        logger.error(f"热加载模型配置失败: {str(e)}")
        return False
```

### 前端文件（Vue）

前端API调用**不需要修改**，因为后端API接口保持不变。

## 🚀 部署步骤

### 1. 安装新依赖

```bash
pip install pyyaml
```

### 2. 测试配置加载

```python
# 测试脚本
python -c "from app.config.config_manager import get_config; c = get_config(); print(c.to_dict())"
```

### 3. 重启服务

```bash
# Docker环境
cd deploy
docker compose down
docker compose up -d

# 本地开发环境
python -m app.main
```

### 4. 验证功能

- ✅ 访问系统设置页面
- ✅ 修改爬虫配置并保存
- ✅ 检查 `app/config/config.yaml` 是否更新
- ✅ 触发爬虫任务，验证配置生效
- ✅ 测试LLM、Redis、邮件配置修改

## 📝 注意事项

### 1. 敏感信息处理

**推荐做法：**
- 在 `config.yaml` 中使用占位符
- 通过 `.env` 文件覆盖敏感信息
- `.env` 不提交到Git

**示例：**
```yaml
# config.yaml
llm:
  api_key: "your-api-key-here"  # 占位符

# .env
OPENAI_API_KEY=sk-real-key-here  # 实际值
```

### 2. 向后兼容

配置管理器支持环境变量覆盖，所以现有的 `.env` 文件仍然有效，只是作为补充而非主要配置源。

### 3. 配置优先级

```
环境变量 (.env) > YAML配置文件 (config.yaml) > 默认值
```

## 🔄 回滚方案

如果遇到问题，可以回滚到旧配置方式：

1. 恢复 `requirements.txt`（移除pyyaml）
2. 删除 `app/config/config_manager.py`
3. 恢复原来的配置读取代码
4. 继续使用 `.env` + `crawler_config.json`

## ✨ 优势

1. ✅ **统一管理** - 所有配置在一个文件中
2. ✅ **支持注释** - 方便理解配置含义
3. ✅ **易于编辑** - YAML比JSON更适合人工修改
4. ✅ **分层结构** - 清晰的配置分类
5. ✅ **热加载支持** - 修改后立即生效
6. ✅ **环境变量覆盖** - 敏感信息安全处理
