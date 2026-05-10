#!/usr/bin/env python3
"""
配置迁移验证脚本

验证 config.yaml 是否正确加载所有配置
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config.config_manager import config_manager


def test_config_loading():
    """测试配置加载"""
    print("=" * 60)
    print("配置迁移验证测试")
    print("=" * 60)
    
    # 测试 SMTP 配置
    print("\n📧 SMTP 配置:")
    smtp_config = config_manager.get_config('smtp')
    print(f"  - Server: {smtp_config.get('server')}")
    print(f"  - Port: {smtp_config.get('port')}")
    print(f"  - User: {smtp_config.get('user', '***已配置***')}")
    print(f"  - Password: {'***已配置***' if smtp_config.get('password') else '❌ 未配置'}")
    
    # 测试 LLM 配置
    print("\n🤖 LLM 配置:")
    llm_config = config_manager.get_config('llm')
    print(f"  - API Key: {'***已配置***' if llm_config.get('openai_api_key') else '❌ 未配置'}")
    print(f"  - API Base: {llm_config.get('openai_api_base')}")
    print(f"  - Model: {llm_config.get('model')}")
    print(f"  - Embedding Model: {llm_config.get('embedding_model')}")
    print(f"  - Embedding Dimension: {llm_config.get('embedding_dimension')}")
    print(f"  - Max Input Tokens: {llm_config.get('max_input_tokens')}")
    print(f"  - Max Output Tokens: {llm_config.get('max_output_tokens')}")
    
    # 测试 Rerank 配置
    print("\n🔄 Rerank 配置:")
    rerank_config = config_manager.get_config('rerank')
    print(f"  - Enabled: {rerank_config.get('enabled')}")
    print(f"  - API URL: {rerank_config.get('api_url')}")
    print(f"  - API Key: {'***已配置***' if rerank_config.get('api_key') else '❌ 未配置'}")
    print(f"  - Model: {rerank_config.get('model')}")
    
    # 测试 Redis 配置
    print("\n💾 Redis 配置:")
    redis_config = config_manager.get_config('redis')
    print(f"  - Host: {redis_config.get('host')}")
    print(f"  - Port: {redis_config.get('port')}")
    print(f"  - Password: {'***' if redis_config.get('password') else '(未设置)'}")
    print(f"  - URL (构建): {config_manager.get_redis_url()}")
    
    # 测试爬虫配置
    print("\n🕷️ 爬虫配置:")
    crawler_config = config_manager.get_config('crawler')
    print(f"  - Sitemap URL: {crawler_config.get('sitemap_url') or '(未配置)'}")
    print(f"  - Timeout: {crawler_config.get('timeout')}")
    print(f"  - Max URLs: {crawler_config.get('max_urls')}")
    print(f"  - Delay: {crawler_config.get('delay_between_requests')}")
    print(f"  - Scheduler Hour: {crawler_config.get('scheduler', {}).get('hour')}")
    print(f"  - Scheduler Minute: {crawler_config.get('scheduler', {}).get('minute')}")
    
    # 测试 Firecrawl 配置
    print("\n🔥 Firecrawl 配置:")
    firecrawl_config = config_manager.get_config('firecrawl')
    print(f"  - Enabled: {firecrawl_config.get('enabled')}")
    print(f"  - API URL: {firecrawl_config.get('api_url')}")
    print(f"  - Timeout: {firecrawl_config.get('timeout')}")
    
    # 测试内容配置
    print("\n📄 内容处理配置:")
    content_config = config_manager.get_config('content')
    print(f"  - Max Content Length Per Page: {content_config.get('max_content_length_per_page')}")
    
    # 测试点号路径访问
    print("\n🔍 点号路径访问测试:")
    print(f"  - llm.model: {config_manager.get('llm.model')}")
    print(f"  - redis.host: {config_manager.get('redis.host')}")
    print(f"  - redis.port: {config_manager.get('redis.port')}")
    print(f"  - smtp.server: {config_manager.get('smtp.server')}")
    
    print("\n" + "=" * 60)
    print("✅ 配置加载测试完成!")
    print("=" * 60)
    
    # 检查关键配置是否缺失
    missing_configs = []
    if not llm_config.get('openai_api_key'):
        missing_configs.append('llm.openai_api_key')
    if not redis_config.get('host'):
        missing_configs.append('redis.host')
    if not redis_config.get('port'):
        missing_configs.append('redis.port')
    
    if missing_configs:
        print("\n⚠️  警告：以下关键配置未设置:")
        for config in missing_configs:
            print(f"  - {config}")
        return False
    else:
        print("\n✅ 所有关键配置均已设置!")
        return True


if __name__ == "__main__":
    success = test_config_loading()
    sys.exit(0 if success else 1)
