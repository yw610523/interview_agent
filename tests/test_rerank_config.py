#!/usr/bin/env python3
"""
Rerank 模型配置检查脚本

用于验证 Rerank 模型的配置是否正确，包括 API Base URL、API Key 和模型名称。
"""
import os
import yaml
from pathlib import Path


def get_config_value(config, key_path, default=None):
    """从嵌套字典中获取值"""
    keys = key_path.split('.')
    value = config
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
            if value is None:
                return default
        else:
            return default
    return value if value is not None else default


def check_rerank_config():
    """检查 Rerank 配置"""
    # 从 llm.yaml 读取配置
    config_path = Path(__file__).parent.parent / "config" / "llm.yaml"
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        print("❌ 未找到 config/llm.yaml 文件")
        return

    print("=" * 60)
    print("Rerank 模型配置检查")
    print("=" * 60)

    # 读取配置（从 llm.rerank 嵌套结构）
    rerank_config = config.get('rerank', {})
    rerank_enabled = rerank_config.get('enabled', False)
    if isinstance(rerank_enabled, str):
        rerank_enabled = rerank_enabled.lower() in ('true', '1', 'yes')
    rerank_api_base = rerank_config.get('api_base', '')
    rerank_api_key = rerank_config.get('api_key', '')
    rerank_model = rerank_config.get('model', '')
    
    # 如果 rerank 配置为空，检查是否复用 openai 配置
    if not rerank_api_key:
        openai_config = config.get('openai', {})
        rerank_api_key = openai_config.get('api_key', '')
    if not rerank_api_base:
        openai_config = config.get('openai', {})
        rerank_api_base = openai_config.get('api_base', '')

    print(f"\n✅ RERANK_ENABLED: {rerank_enabled}")
    print(f"📡 RERANK_API_BASE: {rerank_api_base}")
    print(f"🔑 RERANK_API_KEY: {'已配置' if rerank_api_key else '❌ 未配置'}")
    print(f"🤖 RERANK_MODEL: {rerank_model}")

    print("\n" + "=" * 60)

    if not rerank_enabled:
        print("⚠️  Rerank 未启用")
        print("\n要启用 Rerank，请执行以下步骤：")
        print("1. 在 config/llm.yaml 文件中设置 rerank.enabled: true")
        print("2. 填入你的 rerank.api_key")
        print("3. 重启后端服务")
    elif not rerank_api_key:
        print("⚠️  Rerank API Key 未配置")
        print("\n如何获取 API Key：")
        print("1. 访问 https://siliconflow.cn/")
        print("2. 注册并登录")
        print("3. 在'API密钥'页面创建 API Key")
        print("4. 复制 API Key 到 config/llm.yaml 文件的 rerank.api_key")
    else:
        print("✅ Rerank 配置完整！")
        print("\n现在可以测试 Rerank 功能：")
        print("1. 访问 http://localhost:3000/questions")
        print("2. 勾选'启用 Rerank'开关")
        print("3. 点击'🎯 获取推荐'按钮")
        print("4. 查看后端日志确认 Rerank 是否正常工作")

    print("=" * 60)


if __name__ == "__main__":
    check_rerank_config()
