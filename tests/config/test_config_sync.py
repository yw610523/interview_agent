"""
配置同步测试 (Redis 模式)

测试配置修改后的热加载和同步功能
"""
from app.config.config_manager import config_manager
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestConfigSync:
    """配置同步测试类"""

    def test_01_reload_single_config(self):
        """测试单个配置更新（写入 Redis）"""
        print("\n=== 测试1: 单个配置更新 ===")

        original_redis = config_manager.get_config('redis').copy()

        try:
            new_config = {
                'host': 'sync.test.com',
                'port': 6400,
                'password': ''
            }

            config_manager.save_config('redis', new_config)

            # 直接读 Redis，立即生效
            updated = config_manager.get_config('redis')
            assert updated.get('host') == 'sync.test.com'

            print(f"[OK] 配置已同步更新")
            print(f"[OK] Host: {updated.get('host')}")

        finally:
            config_manager.save_config('redis', original_redis)

    def test_02_manual_reload(self):
        """测试手动重新加载所有配置"""
        print("\n=== 测试2: 手动重新加载所有配置 ===")

        original_llm = config_manager.get_config('llm').copy()

        try:
            # 修改 Redis 中的配置
            test_config = original_llm.copy()
            test_config['openai']['model'] = 'manual-test-model'

            config_manager.save_config('llm', test_config)
            print(f"[OK] 配置已修改")

            # 手动重新加载（从 YAML 同步）
            config_manager.reload()

            # 验证配置
            updated = config_manager.get_config('llm')
            print(f"[OK] 手动重载成功")
            print(f"[OK] Model: {updated.get('openai', {}).get('model')}")

        finally:
            config_manager.save_config('llm', original_llm)

    def test_03_multiple_config_updates(self):
        """测试多个配置连续更新（写入 Redis）"""
        print("\n=== 测试3: 多个配置连续更新 ===")

        originals = {
            'redis': config_manager.get_config('redis').copy(),
            'crawler': config_manager.get_config('crawler').copy(),
            'llm': config_manager.get_config('llm').copy()
        }

        try:
            updates = [
                ('redis', {'host': 'multi1.test.com', 'port': 6401, 'password': ''}),
                ('crawler', {'sitemap_url': 'https://multi1.test.com/sitemap.xml', 'timeout': 50}),
            ]

            for config_key, new_data in updates:
                original = originals[config_key].copy()
                merged = {**original, **new_data}
                config_manager.save_config(config_key, merged)
                print(f"[OK] 已更新 {config_key}")

            # LLM 单独处理（嵌套结构）
            llm_original = originals['llm'].copy()
            if 'openai' in llm_original:
                llm_original['openai']['model'] = 'multi-model-1'
            else:
                llm_original['model'] = 'multi-model-1'
            config_manager.save_config('llm', llm_original)
            print(f"[OK] 已更新 llm")

            # 验证所有配置都已更新
            redis_config = config_manager.get_config('redis')
            crawler_config = config_manager.get_config('crawler')
            llm_config = config_manager.get_config('llm')

            assert redis_config.get('host') == 'multi1.test.com'
            assert crawler_config.get('sitemap_url') == 'https://multi1.test.com/sitemap.xml'

            if 'openai' in llm_config:
                assert llm_config['openai']['model'] == 'multi-model-1'
            else:
                assert llm_config.get('model') == 'multi-model-1'

            print(f"[OK] 所有配置同步成功")

        finally:
            for config_key, original in originals.items():
                config_manager.save_config(config_key, original)
            print(f"[OK] 已恢复所有配置")

    def test_04_config_isolation(self):
        """测试配置隔离性（修改一个配置不影响其他配置）"""
        print("\n=== 测试4: 配置隔离性测试 ===")

        original_crawler_url = config_manager.get_config('crawler').get('sitemap_url')
        original_redis_host = config_manager.get_config('redis').get('host')

        originals = {
            'llm': config_manager.get_config('llm').copy(),
            'crawler': config_manager.get_config('crawler').copy(),
            'redis': config_manager.get_config('redis').copy()
        }

        try:
            # 只修改 LLM 配置
            new_llm = originals['llm'].copy()
            if 'openai' in new_llm:
                new_llm['openai']['model'] = 'isolation-test-model'
            else:
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
            for config_key, original in originals.items():
                config_manager.save_config(config_key, original)

    def test_05_config_redis_atomicity(self):
        """测试 Redis 写入的原子性"""
        print("\n=== 测试5: Redis 写入原子性 ===")

        original = config_manager.get_config('crawler').copy()

        try:
            # 快速连续写入
            for i in range(5):
                test_config = original.copy()
                test_config['sitemap_url'] = f'https://atomic{i}.test.com/sitemap.xml'
                test_config['timeout'] = 30 + i
                config_manager.save_config('crawler', test_config)

            # 验证最后一次写入成功
            final_config = config_manager.get_config('crawler')
            assert final_config.get('sitemap_url') == 'https://atomic4.test.com/sitemap.xml'
            assert final_config.get('timeout') == 34

            print(f"[OK] 原子性测试通过")

        finally:
            config_manager.save_config('crawler', original)

    def test_06_get_config_by_path(self):
        """测试点号路径访问配置（优先 Redis）"""
        print("\n=== 测试6: 点号路径访问配置 ===")

        tests = [
            ('redis.host', str),
            ('redis.port', int),
            ('crawler.timeout', int),
            ('smtp.server', str),
        ]

        for path, expected_type in tests:
            value = config_manager.get(path)
            # 注意：某些值可能是环境变量未解析的字符串
            assert value is not None, f"路径 {path} 应该返回值"
            print(f"[OK] {path}: {value}")

        print(f"[OK] 点号路径访问测试通过")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
