#!/usr/bin/env python3
"""
配置迁移脚本

将 .env 和 crawler_config.json 的配置合并到 config.yaml
"""

import os
from pathlib import Path
import json
import yaml
from dotenv import load_dotenv

def migrate_config():
    """执行配置迁移"""
    
    # 加载.env
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ 已加载 .env 文件")
    else:
        print("⚠️  .env 文件不存在")
        return
    
    # 加载 crawler_config.json
    crawler_json_path = Path(__file__).parent / "crawler_config.json"
    crawler_config = {}
    if crawler_json_path.exists():
        with open(crawler_json_path, 'r', encoding='utf-8') as f:
            crawler_config = json.load(f)
        print(f"✅ 已加载 crawler_config.json")
    else:
        print("⚠️  crawler_config.json 不存在")
    
    # 读取现有 config.yaml（如果有）
    config_yaml_path = Path(__file__).parent / "config.yaml"
    if config_yaml_path.exists():
        with open(config_yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        print(f"✅ 已加载现有 config.yaml")
    else:
        config = {}
        print("📝 创建新的 config.yaml")
    
    # 从环境变量填充配置
    config['llm'] = {
        'api_key': os.getenv('OPENAI_API_KEY', ''),
        'api_base': os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1'),
        'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        'embedding_model': os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small'),
        'embedding_dimension': int(os.getenv('EMBEDDING_DIMENSION', '1536')),
        'max_input_tokens': os.getenv('MODEL_MAX_INPUT_TOKENS', ''),
        'max_output_tokens': os.getenv('MODEL_MAX_OUTPUT_TOKENS', ''),
    }
    
    config['redis'] = {
        'url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    }
    
    config['email'] = {
        'smtp_server': os.getenv('SMTP_SERVER', ''),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'smtp_user': os.getenv('SMTP_USER', ''),
        'smtp_password': os.getenv('SMTP_PASSWORD', ''),
        'test_user': os.getenv('SMTP_TEST_USER', ''),
    }
    
    # 合并爬虫配置
    if 'crawler' not in config:
        config['crawler'] = {}
    
    config['crawler'].update({
        'sitemap_url': crawler_config.get('sitemap_url', os.getenv('SITEMAP_URL', '')),
        'sitemap_path': crawler_config.get('sitemap_path', '/sitemap.xml'),
        'timeout': crawler_config.get('timeout', int(os.getenv('CRAWLER_TIMEOUT', '30'))),
        'max_urls': crawler_config.get('max_urls', os.getenv('CRAWLER_MAX_URLS')),
        'delay_between_requests': crawler_config.get('delay_between_requests', float(os.getenv('CRAWLER_DELAY', '0.5'))),
        'output_dir': crawler_config.get('output_dir', os.getenv('CRAWLER_OUTPUT_DIR', './crawl_results')),
        'user_agent': crawler_config.get('user_agent', os.getenv('CRAWLER_USER_AGENT', '')),
        'verify_ssl': crawler_config.get('verify_ssl', True),
        'follow_redirects': crawler_config.get('follow_redirects', True),
        'max_content_length': crawler_config.get('max_content_length', 10485760),
        'check_robots_txt': crawler_config.get('check_robots_txt', True),
        'robots_path': crawler_config.get('robots_path', '/robots.txt'),
        'save_results': crawler_config.get('save_results', True),
        'verbose': crawler_config.get('verbose', True),
        'url_include_patterns': crawler_config.get('url_include_patterns', []),
        'url_exclude_patterns': crawler_config.get('url_exclude_patterns', []),
    })
    
    config['scheduler'] = {
        'hour': int(os.getenv('SCHEDULER_HOUR', '22')),
        'minute': int(os.getenv('SCHEDULER_MINUTE', '0')),
    }
    
    config['app'] = {
        'port': int(os.getenv('APP_PORT', '9023')),
        'host': '0.0.0.0',
        'debug': False,
    }
    
    # 保存配置
    with open(config_yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n✅ 配置已迁移到: {config_yaml_path}")
    print(f"📊 配置统计:")
    print(f"   - LLM配置: {len(config.get('llm', {}))} 项")
    print(f"   - Redis配置: {len(config.get('redis', {}))} 项")
    print(f"   - 邮件配置: {len(config.get('email', {}))} 项")
    print(f"   - 爬虫配置: {len(config.get('crawler', {}))} 项")
    print(f"   - 定时任务配置: {len(config.get('scheduler', {}))} 项")
    print(f"   - 应用配置: {len(config.get('app', {}))} 项")

if __name__ == "__main__":
    migrate_config()
