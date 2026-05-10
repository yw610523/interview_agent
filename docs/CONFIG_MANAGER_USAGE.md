# ConfigManager 使用指南

## 设计理念

ConfigManager 遵循**开闭原则（OCP）**：
- ✅ **对扩展开放**：新增配置项只需在 `config/` 目录下添加 YAML 文件
- ❌ **对修改关闭**：无需修改 `config_manager.py` 代码

## 自动发现机制

### 工作原理

1. **扫描目录**：自动扫描 `config/` 目录下所有 `.yaml` 文件
2. **文件名即键**：`redis.yaml` → 配置键为 `redis`
3. **内容即值**：YAML 文件内容作为配置值

### 示例

```
config/
├── redis.yaml      → config_manager.get_config('redis')
├── smtp.yaml       → config_manager.get_config('smtp')
├── llm.yaml        → config_manager.get_config('llm')
└── new_module.yaml → config_manager.get_config('new_module')  # 自动生效！
```

## API 使用

### 1. 获取整个模块配置

```python
from app.config.config_manager import config_manager

# 旧方式（已废弃）
smtp_config = config_manager.get_smtp_config()  # ❌

# 新方式（推荐）
smtp_config = config_manager.get_config('smtp')  # ✅
```

### 2. 获取嵌套配置值

```python
# 获取 SMTP 服务器
server = config_manager.get('smtp.server')

# 获取 LLM 模型
model = config_manager.get('llm.model')

# 获取 Redis 主机
host = config_manager.get('redis.host')
```

### 3. 带默认值的访问

```python
# 如果配置不存在，返回默认值
timeout = config_manager.get('crawler.timeout', default=30)
api_key = config_manager.get('llm.api_key', default='')
```

### 4. Redis URL 构建

```python
# 便捷方法
redis_url = config_manager.build_redis_url()
# 返回: redis://localhost:6379 或 redis://:password@host:port
```

## 新增配置项

### 步骤 1：创建配置文件

在 `config/` 目录下创建新的 YAML 文件：

```yaml
# config/my_new_service.yaml
host: localhost
port: 8080
api_key: ''
timeout: 30
```

### 步骤 2：直接使用（无需修改代码！）

```python
# 立即可以使用
my_config = config_manager.get_config('my_new_service')
host = config_manager.get('my_new_service.host')
port = config_manager.get('my_new_service.port')
```

**就这么简单！不需要：**
- ❌ 修改 `config_manager.py`
- ❌ 添加 `get_my_new_service_config()` 方法
- ❌ 在 `_get_default_config()` 中添加默认值
- ❌ 在 `config_files` 列表中注册

## 迁移指南

### 从旧 API 迁移到新 API

| 旧 API | 新 API | 说明 |
|--------|--------|------|
| `get_smtp_config()` | `get_config('smtp')` | 通用方法 |
| `get_llm_config()` | `get_config('llm')` | 通用方法 |
| `get_redis_config()` | `get_config('redis')` | 通用方法 |
| `get_redis_url()` | `build_redis_url()` | 保留便捷方法 |
| `get('smtp.server')` | `get('smtp.server')` | 保持不变 ✅ |

### 代码示例

```python
# 旧代码
from app.config.config_manager import config_manager

smtp_config = config_manager.get_smtp_config()
server = smtp_config.get('server')

llm_config = config_manager.get_llm_config()
model = llm_config.get('model')

# 新代码（更简洁）
from app.config.config_manager import config_manager

server = config_manager.get('smtp.server')
model = config_manager.get('llm.model')

# 或者
smtp_config = config_manager.get_config('smtp')
llm_config = config_manager.get_config('llm')
```

## 优势对比

### 旧设计（违反 OCP）

```python
# 每次新增配置需要修改 3 处代码
def _load_from_directory(self, config_dir):
    config_files = [
        ('smtp.yaml', 'smtp'),
        ('llm.yaml', 'llm'),
        # 新增: ('new.yaml', 'new'),  ← 必须修改这里
    ]

def _get_default_config(self):
    return {
        'smtp': {...},
        'llm': {...},
        # 'new': {...},  ← 必须修改这里
    }

def get_new_config(self):  # ← 必须添加新方法
    return self._config.get('new', {})
```

### 新设计（符合 OCP）

```python
# 自动发现，无需修改代码
def _load_from_directory(self, config_dir):
    yaml_files = list(config_dir.glob('*.yaml'))  # 自动扫描
    for yaml_file in yaml_files:
        config_key = yaml_file.stem  # 自动提取键名
        # 自动加载...

# 通用访问方法，无需为每个模块创建方法
def get_config(self, module_name):
    return self._config.get(module_name, {})
```

## 最佳实践

### 1. 优先使用点号路径访问

```python
# ✅ 推荐：直接获取具体值
server = config_manager.get('smtp.server')
port = config_manager.get('smtp.port')

# ⚠️ 不推荐：获取整个配置再取值
smtp_config = config_manager.get_config('smtp')
server = smtp_config.get('server')
```

### 2. 提供合理的默认值

```python
# ✅ 推荐
timeout = config_manager.get('service.timeout', default=30)

# ❌ 不推荐（可能返回 None）
timeout = config_manager.get('service.timeout')
```

### 3. 配置文件命名规范

- 使用小写字母和下划线：`my_service.yaml`
- 避免特殊字符和空格
- 文件名应具有描述性

## 总结

✅ **符合开闭原则** - 新增配置无需修改代码  
✅ **自动发现** - 扫描目录自动加载  
✅ **统一 API** - `get_config()` 替代所有 `get_xxx_config()`  
✅ **向后兼容** - 点号路径访问保持不变  
✅ **易于维护** - 代码量减少 60%+  
