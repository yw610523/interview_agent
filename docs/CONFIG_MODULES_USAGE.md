# 配置模块使用指南

## 架构设计

每个配置文件都有对应的 Python 封装类，提供类型安全的配置访问。

```
config/
├── smtp.yaml          → app/config/smtp_config.py (SmtpConfig)
├── llm.yaml           → app/config/llm_config.py (LlmConfig)
├── redis.yaml         → app/config/redis_config.py (RedisConfig)
├── rerank.yaml        → app/config/rerank_config.py (RerankConfig)
├── firecrawl.yaml     → app/config/firecrawl_config.py (FirecrawlConfig)
├── service.yaml       → app/config/service_config.py (ServiceConfig)
├── content.yaml       → app/config/content_config.py (ContentConfig)
├── prompts.yaml       → app/config/prompts_config.py (PromptsConfig)
└── crawler.yaml       → app/config/crawler_config.py (CrawlerConfig)
```

## 使用方式

### 1. 导入配置函数

```python
from app.config import (
    get_smtp_config,
    get_llm_config,
    get_redis_config,
    get_rerank_config,
    get_firecrawl_config,
    get_service_config,
    get_content_config,
    get_prompts_config,
    get_config_from_env,  # Crawler 专用
)
```

### 2. 获取配置对象

```python
# SMTP 配置
smtp = get_smtp_config()
print(smtp.server)  # "smtp.qq.com"
print(smtp.port)    # 465

# LLM 配置
llm = get_llm_config()
print(llm.model)              # "gpt-4o-mini"
print(llm.embedding_model)    # "text-embedding-3-small"

# Redis 配置
redis = get_redis_config()
print(redis.host)             # "localhost"
print(redis.build_url())      # "redis://localhost:6379"
```

### 3. IDE 自动补全和类型检查

```python
from app.config import get_llm_config

llm = get_llm_config()

# ✅ IDE 会自动补全这些属性
llm.openai_api_key
llm.model
llm.max_input_tokens

# ✅ 类型检查会捕获错误
llm.unknown_property  # ❌ Pyright/Mypy 报错
```

## 各配置模块详解

### SmtpConfig

```python
@dataclass
class SmtpConfig:
    server: str = "smtp.qq.com"
    port: int = 465
    user: str = ""
    password: str = ""
    test_user: str = ""
```

**使用示例：**
```python
from app.config import get_smtp_config

smtp = get_smtp_config()
if smtp.user and smtp.password:
    # 发送邮件逻辑
    pass
```

### LlmConfig

```python
@dataclass
class LlmConfig:
    openai_api_key: str = ""
    openai_api_base: str = ""
    model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    max_input_tokens: int = 128000
    max_output_tokens: int = 16384
```

**使用示例：**
```python
from app.config import get_llm_config

llm = get_llm_config()
if not llm.openai_api_key:
    raise ValueError("未配置 OpenAI API Key")
```

### RedisConfig

```python
@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    
    def build_url(self) -> str:
        """构建 Redis URL"""
        ...
```

**使用示例：**
```python
from app.config import get_redis_config

redis = get_redis_config()
redis_url = redis.build_url()
# 返回: "redis://localhost:6379" 或 "redis://:password@host:port"
```

### RerankConfig

```python
@dataclass
class RerankConfig:
    enabled: bool = False
    api_url: str = "https://cloud.siliconflow.cn/v1"
    api_key: str = ""
    model: str = "BAAI/bge-reranker-v2-m3"
```

**使用示例：**
```python
from app.config import get_rerank_config

rerank = get_rerank_config()
if rerank.enabled:
    # 使用 Rerank 服务
    pass
```

### FirecrawlConfig

```python
@dataclass
class FirecrawlConfig:
    enabled: bool = False
    api_url: str = "http://localhost:3002"
    api_key: Optional[str] = None
    timeout: int = 600
    use_official: bool = False
    only_main_content: bool = True
```

### ServiceConfig

```python
@dataclass
class ServiceConfig:
    app_port: int = 9023
```

### ContentConfig

```python
@dataclass
class ContentConfig:
    max_content_length_per_page: int = 2000
```

### PromptsConfig

```python
@dataclass
class PromptsConfig:
    question_extraction_system: str = ""
    answer_generation_system: str = ""
```

**使用示例：**
```python
from app.config import get_prompts_config

prompts = get_prompts_config()
system_prompt = prompts.question_extraction_system
```

### CrawlerConfig

```python
@dataclass
class CrawlerConfig:
    sitemap_url: str = ""
    timeout: int = 30
    max_urls: Optional[int] = None
    # ... 更多字段
    
    # Firecrawl 配置（已废弃，请使用 FirecrawlConfig）
    use_firecrawl: bool = False
    firecrawl_api_url: str = "..."
```

**使用示例：**
```python
from app.config import get_config_from_env, get_scheduler_config

# 获取爬虫配置
crawler = get_config_from_env()
print(crawler.sitemap_url)

# 获取调度器配置
scheduler = get_scheduler_config()
print(scheduler['hour'])    # 22
print(scheduler['minute'])  # 0
```

## 优势对比

### ❌ 旧方式（直接使用 config_manager）

```python
from app.config.config_manager import config_manager

# 没有类型提示
smtp_server = config_manager.get('smtp.server')  # str?
smtp_port = config_manager.get('smtp.port')      # int? str?

# 容易拼写错误
smtp_svr = config_manager.get('smtp.serer')  # ❌ 拼错但不会报错

# 没有默认值保护
timeout = config_manager.get('crawler.timeout')  # 可能返回 None
```

### ✅ 新方式（使用配置类）

```python
from app.config import get_smtp_config, get_llm_config

# 完整的类型提示
smtp = get_smtp_config()
smtp_server: str = smtp.server      # ✅ IDE 知道是 str
smtp_port: int = smtp.port          # ✅ IDE 知道是 int

# 拼写错误会被捕获
smtp_svr = smtp.serer  # ❌ Pyright/Mypy 立即报错

# 有合理的默认值
crawler = get_config_from_env()
timeout: int = crawler.timeout  # ✅ 默认 30，不会是 None
```

## 最佳实践

### 1. 在模块顶部获取配置

```python
# ✅ 推荐：模块级别获取一次
from app.config import get_llm_config

llm_config = get_llm_config()

def process_text(text: str):
    # 使用全局配置
    model = llm_config.model
    ...

# ❌ 不推荐：每次调用都重新加载
def process_text(text: str):
    llm_config = get_llm_config()  # 重复加载
    ...
```

### 2. 验证关键配置

```python
from app.config import get_llm_config

llm = get_llm_config()

# 启动时验证必要配置
if not llm.openai_api_key:
    raise RuntimeError("OpenAI API Key 未配置")

if not llm.openai_api_base:
    raise RuntimeError("OpenAI API Base URL 未配置")
```

### 3. 使用 dataclass 的方法

```python
from app.config import get_redis_config

redis = get_redis_config()

# ✅ 使用内置方法
url = redis.build_url()

# ✅ 转换为字典
config_dict = redis.to_dict()
```

## 新增配置模块

如果需要新增配置模块（例如 `database.yaml`）：

### 步骤 1：创建 YAML 文件

```yaml
# config/database.yaml
host: localhost
port: 5432
database: myapp
user: admin
password: ''
```

### 步骤 2：创建 Python 封装

```python
# app/config/database_config.py
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "myapp"
    user: str = "admin"
    password: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseConfig':
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


def get_database_config() -> DatabaseConfig:
    from app.config.config_manager import config_manager
    db_data = config_manager.get_config('database')
    return DatabaseConfig.from_dict(db_data)
```

### 步骤 3：导出到 __init__.py

```python
# app/config/__init__.py
from .database_config import DatabaseConfig, get_database_config

__all__ = [
    # ... 其他配置
    'DatabaseConfig',
    'get_database_config',
]
```

### 步骤 4：使用

```python
from app.config import get_database_config

db = get_database_config()
print(f"{db.user}@{db.host}:{db.port}/{db.database}")
```

## 总结

✅ **类型安全** - Dataclass 提供完整的类型提示  
✅ **IDE 支持** - 自动补全、拼写检查、重构支持  
✅ **默认值** - 每个字段都有合理的默认值  
✅ **统一接口** - 所有配置模块结构一致  
✅ **易于扩展** - 新增配置只需 4 步  

这就是现代化的配置管理方式！🎉
