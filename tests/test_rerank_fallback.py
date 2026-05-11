#!/usr/bin/env python3
"""
Rerank 配置复用逻辑测试

用于验证 Rerank 配置是否正确复用了 OpenAI 的配置。
当未配置独立的 rerank.api_url 和 rerank.api_key 时，
系统将自动复用 llm.openai_api_base 和 llm.openai_api_key。
"""
import yaml
from pathlib import Path


def test_rerank_fallback():
    """测试 Rerank 配置复用逻辑"""
    # 从 config.yaml 读取配置
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        print("❌ 未找到 config.yaml 文件")
        return

    print("=" * 60)
    print("Rerank 配置复用测试")
    print("=" * 60)

    # 读取配置
    rerank_config = config.get('rerank', {})
    rerank_enabled = rerank_config.get('enabled', False)
    if isinstance(rerank_enabled, str):
        rerank_enabled = rerank_enabled.lower() in ('true', '1', 'yes')
    rerank_api_base = rerank_config.get('api_base', '').strip()
    rerank_api_key = rerank_config.get('api_key', '').strip()
    
    llm_config = config.get('llm', {})
    openai_api_base = llm_config.get('openai_api_base', '')
    openai_api_key = llm_config.get('openai_api_key', '')

    print(f"\n✅ RERANK_ENABLED: {rerank_enabled}")
    print(f"📡 RERANK_API_BASE: '{rerank_api_base}' {'(为空，将复用 OPENAI_API_BASE)' if not rerank_api_base else ''}")
    print(f"🔑 RERANK_API_KEY: '{'已配置' if rerank_api_key else '(为空，将复用 OPENAI_API_KEY)'}'")
    print(f"\n📡 OPENAI_API_BASE: {openai_api_base}")
    print(f"🔑 OPENAI_API_KEY: {'已配置' if openai_api_key else '未配置'}")

    print("\n" + "=" * 60)

    if rerank_enabled:
        if not rerank_api_key and openai_api_key:
            print("✅ Rerank 将复用 OPENAI_API_KEY")
        elif rerank_api_key:
            print("✅ Rerank 使用独立的 API Key")
        else:
            print("❌ Rerank 已启用但无 API Key")
        
        if not rerank_api_base and openai_api_base:
            print("✅ Rerank 将复用 OPENAI_API_BASE")
        elif rerank_api_base:
            print("✅ Rerank 使用独立的 API URL")
        else:
            print("⚠️  Rerank 无 API URL，将使用 OpenAI 默认地址")
    else:
        print("⚠️  Rerank 未启用")

    print("=" * 60)


if __name__ == "__main__":
    test_rerank_fallback()
