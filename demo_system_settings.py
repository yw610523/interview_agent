#!/usr/bin/env python3
"""
系统设置功能演示脚本

展示如何使用系统配置API进行配置管理
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

def print_section(title):
    """打印分隔线和标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def demo_get_system_config():
    """演示：获取系统配置"""
    print_section("演示1: 获取系统配置")
    
    print("\n📋 请求: GET /api/system-config")
    
    try:
        response = requests.get(f"{BASE_URL}/system-config")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ 成功获取配置")
            print(f"\n配置类别:")
            for category in data['config'].keys():
                print(f"  • {category}")
            
            # 显示部分配置示例
            llm_config = data['config'].get('llm', {})
            print(f"\n模型配置示例:")
            print(f"  - 模型名称: {llm_config.get('openai_model', 'N/A')}")
            print(f"  - Embedding模型: {llm_config.get('openai_embedding_model', 'N/A')}")
            print(f"  - API Key: {llm_config.get('openai_api_key', 'N/A')[:10]}... (已脱敏)")
        else:
            print(f"\n❌ 请求失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")

def demo_update_llm_config():
    """演示：更新模型配置"""
    print_section("演示2: 更新模型配置")
    
    config = {
        "openai_api_key": "sk-test-key-12345",
        "openai_api_base": "https://api.openai.com/v1",
        "openai_model": "gpt-4o-mini",
        "openai_embedding_model": "text-embedding-3-small",
        "embedding_dimension": 1536,
        "model_max_input_tokens": "",
        "model_max_output_tokens": ""
    }
    
    print(f"\n📝 请求: PUT /api/llm-config")
    print(f"\n配置内容:")
    for key, value in config.items():
        if 'key' in key.lower() or 'password' in key.lower():
            print(f"  - {key}: {'*' * 10} (隐藏)")
        else:
            print(f"  - {key}: {value}")
    
    try:
        response = requests.put(
            f"{BASE_URL}/llm-config",
            json=config,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ {data['message']}")
            print(f"\n⚠️  注意: 需要重启服务才能使新配置生效")
        else:
            print(f"\n❌ 请求失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")

def demo_update_redis_config():
    """演示：更新Redis配置"""
    print_section("演示3: 更新Redis配置")
    
    redis_url = "redis://localhost:6379"
    
    print(f"\n📝 请求: PUT /api/redis-config")
    print(f"\n配置内容:")
    print(f"  - Redis URL: {redis_url}")
    
    try:
        response = requests.put(
            f"{BASE_URL}/redis-config",
            json={"redis_url": redis_url},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ {data['message']}")
            print(f"\n⚠️  注意: 需要重启服务才能使新配置生效")
        else:
            print(f"\n❌ 请求失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")

def demo_update_email_config():
    """演示：更新邮件配置"""
    print_section("演示4: 更新邮件配置")
    
    config = {
        "smtp_server": "smtp.qq.com",
        "smtp_port": 587,
        "smtp_user": "your-email@qq.com",
        "smtp_password": "your-auth-code",
        "smtp_test_user": "test-email@qq.com"
    }
    
    print(f"\n📝 请求: PUT /api/email-config")
    print(f"\n配置内容:")
    for key, value in config.items():
        if 'password' in key.lower():
            print(f"  - {key}: {'*' * 10} (隐藏)")
        else:
            print(f"  - {key}: {value}")
    
    try:
        response = requests.put(
            f"{BASE_URL}/email-config",
            json=config,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ {data['message']}")
            print(f"\n💡 提示: 可以使用测试邮件功能验证配置")
            print(f"⚠️  注意: 需要重启服务才能使新配置生效")
        else:
            print(f"\n❌ 请求失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")

def demo_test_email():
    """演示：测试邮件发送"""
    print_section("演示5: 测试邮件发送")
    
    print(f"\n📝 请求: POST /api/test-email")
    print(f"\n说明: 发送测试邮件到配置的测试邮箱")
    
    try:
        response = requests.post(f"{BASE_URL}/test-email")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ {data['message']}")
            print(f"\n💡 请检查测试邮箱是否收到邮件")
        else:
            data = response.json()
            print(f"\n❌ 测试失败: {data.get('detail', '未知错误')}")
            print(f"\n可能的原因:")
            print(f"  1. 邮件配置不正确")
            print(f"  2. SMTP服务器连接失败")
            print(f"  3. 未配置测试邮箱")
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")

def demo_workflow():
    """演示：完整配置流程"""
    print_section("演示6: 完整配置工作流程")
    
    print("\n📋 推荐的配置流程:\n")
    print("  1️⃣  配置爬虫设置")
    print("      • 设置 Sitemap URL")
    print("      • 调整爬取参数")
    print("      • ✅ 立即生效，无需重启\n")
    
    print("  2️⃣  配置模型设置")
    print("      • 设置 API Key")
    print("      • 配置模型名称")
    print("      • ⚠️  需要重启服务\n")
    
    print("  3️⃣  配置Redis设置")
    print("      • 设置 Redis URL")
    print("      • ⚠️  需要重启服务\n")
    
    print("  4️⃣  配置邮件设置")
    print("      • 设置 SMTP 信息")
    print("      • 测试邮件发送")
    print("      • ⚠️  需要重启服务\n")
    
    print("  5️⃣  配置定时任务")
    print("      • 设置执行时间")
    print("      • ⚠️  需要重启服务\n")
    
    print("  🔄 重启服务使所有配置生效")
    print("      $ python -m app.main\n")

def main():
    """主函数：运行所有演示"""
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  系统设置功能演示".center(56) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    
    print("\n⚠️  注意: 请确保后端服务正在运行")
    print("   启动命令: python -m app.main\n")
    
    input("按 Enter 键开始演示...")
    
    demo_get_system_config()
    time.sleep(1)
    
    demo_update_llm_config()
    time.sleep(1)
    
    demo_update_redis_config()
    time.sleep(1)
    
    demo_update_email_config()
    time.sleep(1)
    
    demo_test_email()
    time.sleep(1)
    
    demo_workflow()
    
    print("\n" + "=" * 70)
    print("  演示完成")
    print("=" * 70)
    print("\n📖 更多信息请参考:")
    print("  • docs/SYSTEM_SETTINGS.md - 功能详细说明")
    print("  • docs/SYSTEM_SETTINGS_UI_GUIDE.md - 界面使用指南")
    print("  • README.md - 项目主文档\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n演示已取消")
