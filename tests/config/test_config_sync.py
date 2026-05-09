"""
配置同步测试

测试配置修改后的热加载和同步功能
"""
from app.config.config_manager import config_manager
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestConfigSync:
    """配置同步测试类"""

    def test_01_reload_single_config(self):
        """测试单个配置重新加载"""
        print("\n=== 测试1: 单个配置重新加载 ===")

        # 保存原始配置
        original_redis = config_manager.get_config('redis').copy()

        try:
            # 修改配置
            new_config = {
                'host': 'sync.test.com',
                'port': 6400,
                'password': ''
            }

            config_manager.save_config('redis', new_config)

            # 验证配置已更新（save_config 会自动 reload）
            updated = config_manager.get_config('redis')
            assert updated.get('host') == 'sync.test.com'

            print(f"[OK] 配置已同步更新")
            print(f"[OK] Host: {updated.get('host')}")

        finally:
            # 恢复
            config_manager.save_config('redis', original_redis)

    def test_02_manual_reload(self):
        """测试手动重新加载所有配置"""
        print("\n=== 测试2: 手动重新加载所有配置 ===")

        # 保存原始配置
        original_llm = config_manager.get_config('llm').copy()

        try:
            # 直接修改配置文件（绕过 save_config）
            import yaml
            from pathlib import Path as PathLib

            config_file = PathLib(__file__).parent.parent.parent / 'config' / 'llm.yaml'
            test_config = {
                'openai_api_key': 'manual-test-key',
                'openai_api_base': 'https://manual.test.com/v1',
                'model': 'manual-model',
                'embedding_model': 'manual-embed',
                'embedding_dimension': 512
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(test_config, f, allow_unicode=True)

            print(f"[OK] 配置文件已直接修改")

            # 手动重新加载
            config_manager.reload()

            # 验证配置已更新
            updated = config_manager.get_config('llm')
            assert updated.get('openai_api_key') == 'manual-test-key'
            assert updated.get('model') == 'manual-model'

            print(f"[OK] 手动重载成功")
            print(f"[OK] Model: {updated.get('model')}")

        finally:
            # 恢复
            config_manager.save_config('llm', original_llm)

    def test_03_multiple_config_updates(self):
        """测试多个配置连续更新"""
        print("\n=== 测试3: 多个配置连续更新 ===")

        # 保存原始配置
        originals = {
            'redis': config_manager.get_config('redis').copy(),
            'crawler': config_manager.get_config('crawler').copy(),
            'llm': config_manager.get_config('llm').copy()
        }

        try:
            # 连续更新多个配置
            updates = [
                ('redis', {'host': 'multi1.test.com', 'port': 6401, 'password': ''}),
                ('crawler', {'sitemap_url': 'https://multi1.test.com/sitemap.xml', 'timeout': 50}),
                ('llm', {'model': 'multi-model-1', 'embedding_model': 'multi-embed-1'})
            ]

            for config_key, new_data in updates:
                original = originals[config_key].copy()
                merged = {**original, **new_data}
                config_manager.save_config(config_key, merged)
                print(f"[OK] 已更新 {config_key}")

            # 验证所有配置都已更新
            redis_config = config_manager.get_config('redis')
            crawler_config = config_manager.get_config('crawler')
            llm_config = config_manager.get_config('llm')

            assert redis_config.get('host') == 'multi1.test.com'
            assert crawler_config.get('sitemap_url') == 'https://multi1.test.com/sitemap.xml'
            assert llm_config.get('model') == 'multi-model-1'

            print(f"[OK] 所有配置同步成功")

        finally:
            # 恢复所有配置
            for config_key, original in originals.items():
                config_manager.save_config(config_key, original)
            print(f"[OK] 已恢复所有配置")

    def test_04_config_isolation(self):
        """测试配置隔离性（修改一个配置不影响其他配置）"""
        print("\n=== 测试4: 配置隔离性测试 ===")

        # 记录原始值
        original_crawler_url = config_manager.get_config('crawler').get('sitemap_url')
        original_redis_host = config_manager.get_config('redis').get('host')

        # 保存原始配置
        originals = {
            'llm': config_manager.get_config('llm').copy(),
            'crawler': config_manager.get_config('crawler').copy(),
            'redis': config_manager.get_config('redis').copy()
        }

        try:
            # 只修改 LLM 配置
            new_llm = originals['llm'].copy()
            new_llm['model'] = 'isolation-test-model'
            config_manager.save_config('llm', new_llm)

            # 验证其他配置未受影响
            current_crawler_url = config_manager.get_config('crawler').get('sitemap_url')
            current_redis_host = config_manager.get_config('redis').get('host')

            assert current_crawler_url == original_crawler_url, "Crawler 配置不应被影响"
            assert current_redis_host == original_redis_host, "Redis 配置不应被影响"

            print(f"[OK] 配置隔离性验证通过")
            print(f"[OK] Crawler URL 保持不变: {current_crawler_url}")
            print(f"[OK] Redis Host 保持不变: {current_redis_host}")

        finally:
            # 恢复
            for config_key, original in originals.items():
                config_manager.save_config(config_key, original)

    def test_05_config_file_atomicity(self):
        """测试配置文件写入的原子性"""
        print("\n=== 测试5: 配置文件写入原子性 ===")

        import yaml
        from pathlib import Path as PathLib

        # 保存原始配置
        original = config_manager.get_config('crawler').copy()

        try:
            # 快速连续写入
            for i in range(5):
                test_config = {
                    'sitemap_url': f'https://atomic{i}.test.com/sitemap.xml',
                    'timeout': 30 + i,
                    'max_urls': None,
                    'delay_between_requests': 0.5
                }
                config_manager.save_config('crawler', test_config)

            # 验证最后一次写入成功
            final_config = config_manager.get_config('crawler')
            assert final_config.get('sitemap_url') == 'https://atomic4.test.com/sitemap.xml'
            assert final_config.get('timeout') == 34

            # 验证文件完整性
            config_file = PathLib(__file__).parent.parent.parent / 'config' / 'crawler.yaml'
            with open(config_file, 'r', encoding='utf-8') as f:
                file_content = yaml.safe_load(f)

            assert file_content is not None, "配置文件应该是有效的 YAML"
            assert isinstance(file_content, dict), "配置文件应该是字典类型"

            print(f"[OK] 原子性测试通过")
            print(f"[OK] 文件完整性验证通过")

        finally:
            # 恢复
            config_manager.save_config('crawler', original)

    def test_06_get_config_by_path(self):
        """测试点号路径访问配置"""
        print("\n=== 测试6: 点号路径访问配置 ===")

        # 测试各种路径访问
        tests = [
            ('redis.host', str),
            ('redis.port', int),
            ('llm.model', str),
            ('crawler.timeout', int),
            ('smtp.server', str),
        ]

        for path, expected_type in tests:
            value = config_manager.get(path)
            assert value is not None, f"路径 {path} 应该返回值"
            assert isinstance(value, expected_type), f"路径 {path} 应该返回 {expected_type.__name__} 类型"
            print(f"[OK] {path}: {value} ({expected_type.__name__})")

        print(f"[OK] 点号路径访问测试通过")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
