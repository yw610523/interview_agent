# 配置测试文档

本目录包含所有配置模块的测试用例，用于验证配置的增删改查和同步功能。

## 测试文件结构

```
tests/config/
├── __init__.py                    # 包初始化文件
├── test_redis_config.py           # Redis 配置测试 (6 tests)
├── test_crawler_config.py         # 爬虫配置测试 (5 tests)
├── test_llm_config.py             # LLM 配置测试 (5 tests)
├── test_smtp_config.py            # SMTP 邮件配置测试 (4 tests)
├── test_firecrawl_config.py       # Firecrawl 配置测试 (4 tests)
├── test_rerank_config.py          # Rerank 配置测试 (4 tests)
├── test_content_service_config.py # Content & Service 配置测试 (4 tests)
├── test_prompts_config.py         # Prompts 提示词配置测试 (5 tests)
├── test_config_sync.py            # 配置同步功能测试 (6 tests)
└── README.md                      # 本文档
```

## 测试覆盖范围

**总计：43 个测试用例，100% 通过率**

### 1. Redis 配置测试 (`test_redis_config.py`) - 6 tests

- ✅ 读取 Redis 配置
- ✅ 构建 Redis URL（带密码/不带密码）
- ✅ 更新 Redis 配置（host/port/password）
- ✅ 配置持久化验证

**测试用例：**
- `test_01_read_redis_config` - 读取配置
- `test_02_build_redis_url` - 构建 URL
- `test_03_update_redis_config` - 更新配置
- `test_04_redis_url_with_password` - 带密码的 URL
- `test_05_redis_url_without_password` - 不带密码的 URL
- `test_06_config_persistence` - 持久化测试

### 2. 爬虫配置测试 (`test_crawler_config.py`)

- ✅ 读取爬虫配置
- ✅ 更新基础配置（sitemap_url、timeout 等）
- ✅ 更新 URL 过滤规则
- ✅ 更新定时任务配置
- ✅ 配置持久化验证

**测试用例：**
- `test_01_read_crawler_config` - 读取配置
- `test_02_update_crawler_basic_config` - 更新基础配置
- `test_03_update_url_filter_patterns` - 更新过滤规则
- `test_04_update_scheduler_config` - 更新定时任务
- `test_05_config_persistence` - 持久化测试

### 3. LLM 配置测试 (`test_llm_config.py`)

- ✅ 读取 LLM 配置
- ✅ 更新 API 密钥和端点
- ✅ 更新 Token 限制
- ✅ 更新 Embedding 维度
- ✅ 配置持久化验证

**测试用例：**
- `test_01_read_llm_config` - 读取配置
- `test_02_update_llm_basic_config` - 更新基础配置
- `test_03_update_token_limits` - 更新 Token 限制
- `test_04_update_embedding_dimension` - 更新 Embedding 维度
- `test_05_config_persistence` - 持久化测试

### 5. SMTP 邮件配置测试 (`test_smtp_config.py`) - 4 tests

- ✅ 读取 SMTP 配置
- ✅ 更新 SMTP 服务器/端口/用户
- ✅ 更新 SMTP 端口（SSL/TLS）
- ✅ 配置持久化验证

**测试用例：**
- `test_01_read_smtp_config` - 读取配置
- `test_02_update_smtp_config` - 更新配置
- `test_03_update_smtp_port` - 更新端口
- `test_04_config_persistence` - 持久化测试

### 6. Firecrawl 配置测试 (`test_firecrawl_config.py`) - 4 tests

- ✅ 读取 Firecrawl 配置
- ✅ 更新 API URL 和密钥
- ✅ 开关 Firecrawl 功能
- ✅ 配置持久化验证

**测试用例：**
- `test_01_read_firecrawl_config` - 读取配置
- `test_02_update_firecrawl_config` - 更新配置
- `test_03_toggle_firecrawl_enabled` - 开关功能
- `test_04_config_persistence` - 持久化测试

### 7. Rerank 配置测试 (`test_rerank_config.py`) - 4 tests

- ✅ 读取 Rerank 配置
- ✅ 更新 Rerank 模型和 API
- ✅ 开关 Rerank 功能
- ✅ 配置持久化验证

**测试用例：**
- `test_01_read_rerank_config` - 读取配置
- `test_02_update_rerank_config` - 更新配置
- `test_03_toggle_rerank_enabled` - 开关功能
- `test_04_config_persistence` - 持久化测试

### 8. Content & Service 配置测试 (`test_content_service_config.py`) - 4 tests

- ✅ 读取 Content 配置
- ✅ 更新内容长度限制
- ✅ 读取 Service 配置
- ✅ 更新服务端口

**测试用例：**
- `TestContentConfig::test_01_read_content_config` - 读取 Content 配置
- `TestContentConfig::test_02_update_content_config` - 更新 Content 配置
- `TestServiceConfig::test_01_read_service_config` - 读取 Service 配置
- `TestServiceConfig::test_02_update_service_config` - 更新 Service 配置

### 9. Prompts 提示词配置测试 (`test_prompts_config.py`) - 5 tests

- ✅ 读取提示词配置
- ✅ 更新问题提取提示词
- ✅ 更新答案生成提示词
- ✅ 同时更新两个提示词
- ✅ 配置持久化验证

**测试用例：**
- `test_01_read_prompts_config` - 读取配置
- `test_02_update_question_extraction_prompt` - 更新问题提取提示词
- `test_03_update_answer_generation_prompt` - 更新答案生成提示词
- `test_04_update_both_prompts` - 同时更新两个提示词
- `test_05_config_persistence` - 持久化测试

### 10. 配置同步测试 (`test_config_sync.py`) - 6 tests

- ✅ 单个配置重新加载
- ✅ 手动重新加载所有配置
- ✅ 多个配置连续更新
- ✅ 配置隔离性（修改一个不影响其他）
- ✅ 配置文件写入原子性
- ✅ 点号路径访问配置

**测试用例：**
- `test_01_reload_single_config` - 单配置重载
- `test_02_manual_reload` - 手动重载
- `test_03_multiple_config_updates` - 多配置更新
- `test_04_config_isolation` - 配置隔离性
- `test_05_config_file_atomicity` - 写入原子性
- `test_06_get_config_by_path` - 点号路径访问

## 运行测试

### 运行所有配置测试

```bash
cd D:\dev\interview_agent
python -m pytest tests/config/ -v -s
```

### 运行单个测试文件

```bash
# Redis 配置测试
python -m pytest tests/config/test_redis_config.py -v -s

# 爬虫配置测试
python -m pytest tests/config/test_crawler_config.py -v -s

# LLM 配置测试
python -m pytest tests/config/test_llm_config.py -v -s

# 配置同步测试
python -m pytest tests/config/test_config_sync.py -v -s
```

### 运行特定测试用例

```bash
python -m pytest tests/config/test_redis_config.py::TestRedisConfig::test_01_read_redis_config -v -s
```

## 测试特性

### 1. 自动恢复机制

所有测试用例都使用 `try-finally` 块确保测试后恢复原始配置，避免影响其他测试或生产环境。

### 2. 完整的验证流程

每个测试都包含：
- 前置条件检查
- 操作执行
- 结果验证（断言）
- 状态输出（print）
- 清理恢复

### 3. 真实文件操作

测试直接操作真实的配置文件（`config/*.yaml`），验证：
- 配置保存功能
- 文件持久化
- 重新加载机制
- 数据一致性

## 注意事项

⚠️ **重要提示：**

1. 测试会修改真实的配置文件，请确保：
   - 在测试环境中运行
   - 或在运行前备份配置文件

2. 测试需要后端服务停止运行，避免配置冲突

3. 如果测试失败，检查：
   - 配置文件权限
   - YAML 格式正确性
   - 配置管理器初始化

## 扩展测试

如需添加新的配置模块测试（如 SMTP、Firecrawl 等），请遵循以下模板：

```python
"""
XXX 配置测试
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.config_manager import config_manager


class TestXXXConfig:
    """XXX 配置测试类"""

    def test_01_read_xxx_config(self):
        """测试读取 XXX 配置"""
        print("\n=== 测试1: 读取 XXX 配置 ===")
        
        xxx_config = config_manager.get_xxx_config()
        
        assert xxx_config is not None
        assert isinstance(xxx_config, dict)
        
        print(f"✅ 配置读取成功")

    def test_02_update_xxx_config(self):
        """测试更新 XXX 配置"""
        print("\n=== 测试2: 更新 XXX 配置 ===")
        
        original_config = config_manager.get_xxx_config().copy()
        
        try:
            new_config = {
                # 测试数据
            }
            
            success = config_manager.save_config('xxx', new_config)
            assert success
            
            config_manager.reload()
            
            updated_config = config_manager.get_xxx_config()
            # 验证更新
            
            print(f"✅ 配置更新成功")
            
        finally:
            config_manager.save_config('xxx', original_config)
            config_manager.reload()
            print(f"✅ 已恢复原始配置")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
```

## 测试报告

运行测试后，pytest 会生成详细的测试报告，包括：
- 通过的测试用例
- 失败的测试用例（如有）
- 错误信息（如有）
- 执行时间

可以使用以下命令生成 HTML 报告：

```bash
python -m pytest tests/config/ -v --html=report.html --self-contained-html
```
