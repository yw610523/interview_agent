#!/usr/bin/env python3
"""
Rerank 模型配置检查脚本

用于验证 Rerank 模型的配置是否正确，包括 API URL、API Key 和模型名称。
"""
import os
from dotenv import load_dotenv


def check_rerank_config():
    """检查 Rerank 配置"""
    # 加载环境变量
    load_dotenv()

    print("=" * 60)
    print("Rerank 模型配置检查")
    print("=" * 60)

    # 读取配置
    rerank_enabled = os.getenv("RERANK_ENABLED", "false").lower() == "true"
    rerank_api_url = os.getenv("RERANK_API_URL", "")
    rerank_api_key = os.getenv("RERANK_API_KEY", "")
    rerank_model = os.getenv("RERANK_MODEL", "")

    print(f"\n✅ RERANK_ENABLED: {rerank_enabled}")
    print(f"📡 RERANK_API_URL: {rerank_api_url}")
    print(f"🔑 RERANK_API_KEY: {'已配置' if rerank_api_key else '❌ 未配置'}")
    print(f"🤖 RERANK_MODEL: {rerank_model}")

    print("\n" + "=" * 60)

    if not rerank_enabled:
        print("⚠️  Rerank 未启用")
        print("\n要启用 Rerank，请执行以下步骤：")
        print("1. 在 .env 文件中设置 RERANK_ENABLED=true")
        print("2. 填入你的 RERANK_API_KEY")
        print("3. 重启后端服务")
    elif not rerank_api_key:
        print("⚠️  Rerank API Key 未配置")
        print("\n如何获取 API Key：")
        print("1. 访问 https://cloud.siliconflow.cn/")
        print("2. 注册并登录")
        print("3. 在'API密钥'页面创建 API Key")
        print("4. 复制 API Key 到 .env 文件的 RERANK_API_KEY")
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
