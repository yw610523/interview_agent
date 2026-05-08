#!/usr/bin/env python3
"""
Rerank 配置复用逻辑测试

用于验证 Rerank 配置是否正确复用了 OpenAI 的配置。
当未配置独立的 RERANK_API_URL 和 RERANK_API_KEY 时，
系统将自动复用 OPENAI_API_BASE 和 OPENAI_API_KEY。
"""
import os
from dotenv import load_dotenv


def test_rerank_fallback():
    """测试 Rerank 配置复用逻辑"""
    load_dotenv()

    print("=" * 60)
    print("Rerank 配置复用测试")
    print("=" * 60)

    # 读取配置
    rerank_enabled = os.getenv("RERANK_ENABLED", "false").lower() == "true"
    rerank_api_url = os.getenv("RERANK_API_URL", "").strip()
    rerank_api_key = os.getenv("RERANK_API_KEY", "").strip()
    openai_api_base = os.getenv("OPENAI_API_BASE")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    print(f"\n✅ RERANK_ENABLED: {rerank_enabled}")
    print(f"📡 RERANK_API_URL: '{rerank_api_url}' {'(为空，将复用 OPENAI_API_BASE)' if not rerank_api_url else ''}")
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
        
        if not rerank_api_url and openai_api_base:
            print("✅ Rerank 将复用 OPENAI_API_BASE")
        elif rerank_api_url:
            print("✅ Rerank 使用独立的 API URL")
        else:
            print("⚠️  Rerank 无 API URL，将使用 OpenAI 默认地址")
    else:
        print("⚠️  Rerank 未启用")

    print("=" * 60)


if __name__ == "__main__":
    test_rerank_fallback()
