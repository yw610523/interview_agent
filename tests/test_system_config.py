#!/usr/bin/env python3
"""
系统配置API测试脚本

用于测试系统配置相关的API接口
"""

import requests

BASE_URL = "http://localhost:8000/api"


def test_get_system_config():
    """测试获取系统配置"""
    print("=" * 60)
    print("测试1: 获取系统配置")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/system-config")
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"响应状态: {data['status']}")
            print("\n配置类别:")
            for category in data['config'].keys():
                print(f"  - {category}")
            print("\n✅ 测试通过")
        else:
            print(f"❌ 测试失败: {response.text}")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

    print()


def test_update_llm_config():
    """测试更新模型配置"""
    print("=" * 60)
    print("测试2: 更新模型配置")
    print("=" * 60)

    config = {
        "openai_api_key": "test-key-123",
        "openai_api_base": "https://api.openai.com/v1",
        "openai_model": "gpt-4o-mini",
        "openai_embedding_model": "text-embedding-3-small",
        "embedding_dimension": 1536
    }

    try:
        response = requests.put(
            f"{BASE_URL}/llm-config",
            json=config,
            headers={"Content-Type": "application/json"}
        )
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"响应状态: {data['status']}")
            print(f"消息: {data['message']}")
            print("\n✅ 测试通过")
        else:
            print(f"❌ 测试失败: {response.text}")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

    print()


def test_update_redis_config():
    """测试更新Redis配置（已废弃，Redis配置现在使用 host/port/password）"""
    print("=" * 60)
    print("测试3: 更新Redis配置 (已废弃)")
    print("=" * 60)
    print("⚠️  此测试已废弃，Redis配置现在使用 host/port/password 字段")
    print()


def test_update_email_config():
    """测试更新邮件配置"""
    print("=" * 60)
    print("测试4: 更新邮件配置")
    print("=" * 60)

    config = {
        "smtp_server": "smtp.qq.com",
        "smtp_port": 587,
        "smtp_user": "test@example.com",
        "smtp_password": "test-password",
        "smtp_test_user": "test@example.com"
    }

    try:
        response = requests.put(
            f"{BASE_URL}/email-config",
            json=config,
            headers={"Content-Type": "application/json"}
        )
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"响应状态: {data['status']}")
            print(f"消息: {data['message']}")
            print("\n✅ 测试通过")
        else:
            print(f"❌ 测试失败: {response.text}")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("系统配置API测试")
    print("=" * 60 + "\n")

    print("注意: 请确保后端服务正在运行 (python -m app.main)\n")

    test_get_system_config()
    test_update_llm_config()
    test_update_redis_config()
    test_update_email_config()

    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
