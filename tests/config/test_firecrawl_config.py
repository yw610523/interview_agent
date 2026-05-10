"""
Firecrawl 配置测试

测试 Firecrawl 配置的增删改查和同步功能
"""
from app.config.config_manager import config_manager
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestFirecrawlConfig:
    """Firecrawl 配置测试类"""

    def test_01_read_firecrawl_config(self):
        """测试读取 Firecrawl 配置"""
        print("\n=== Test 1: Read Firecrawl Config ===")

        firecrawl_config = config_manager.get_config('firecrawl')

        assert firecrawl_config is not None
        assert isinstance(firecrawl_config, dict)

        required_fields = ['enabled', 'api_url', 'timeout']
        for field in required_fields:
            assert field in firecrawl_config, f"Firecrawl config must contain {field} field"

        print(f"[OK] Enabled: {firecrawl_config.get('enabled')}")
        print(f"[OK] API URL: {firecrawl_config.get('api_url')}")
        print(f"[OK] Timeout: {firecrawl_config.get('timeout')}")

    def test_02_update_firecrawl_config(self):
        """测试更新 Firecrawl 配置"""
        print("\n=== Test 2: Update Firecrawl Config ===")

        original_config = config_manager.get_config('firecrawl').copy()

        try:
            new_config = {
                'enabled': True,
                'api_url': 'http://test.firecrawl.com:3002',
                'api_key': 'fc-test-key-123',
                'timeout': 300,
                'use_official': False,
                'only_main_content': True
            }

            success = config_manager.save_config('firecrawl', new_config)
            assert success

            # 直接读取 Redis，无需 reload
            updated_config = config_manager.get_config('firecrawl')
            assert updated_config.get('enabled') is True
            assert updated_config.get('api_url') == 'http://test.firecrawl.com:3002'
            assert updated_config.get('timeout') == 300

            print(f"[OK] Enabled: {updated_config.get('enabled')}")
            print(f"[OK] API URL: {updated_config.get('api_url')}")
            print(f"[OK] Timeout: {updated_config.get('timeout')}")

        finally:
            config_manager.save_config('firecrawl', original_config)
            print(f"[OK] Restored original config")

    def test_03_toggle_firecrawl_enabled(self):
        """测试开关 Firecrawl"""
        print("\n=== Test 3: Toggle Firecrawl Enabled ===")

        original_config = config_manager.get_config('firecrawl').copy()

        try:
            # 启用
            new_config = original_config.copy()
            new_config['enabled'] = True
            config_manager.save_config('firecrawl', new_config)

            assert config_manager.get_config('firecrawl').get('enabled') is True
            print(f"[OK] Firecrawl enabled")

            # 禁用
            new_config['enabled'] = False
            config_manager.save_config('firecrawl', new_config)

            assert config_manager.get_config('firecrawl').get('enabled') is False
            print(f"[OK] Firecrawl disabled")

        finally:
            config_manager.save_config('firecrawl', original_config)

    def test_04_config_persistence(self):
        """测试配置持久化到 Redis"""
        print("\n=== Test 4: Config Persistence ===")

        test_config = {
            'enabled': True,
            'api_url': 'http://persist.firecrawl.com:3002',
            'api_key': 'fc-persist-key',
            'timeout': 500
        }

        config_manager.save_config('firecrawl', test_config)

        # 验证配置已保存到 Redis
        redis_config = config_manager.get_config('firecrawl')
        assert redis_config.get('enabled') is True
        assert redis_config.get('api_url') == 'http://persist.firecrawl.com:3002'
        assert redis_config.get('timeout') == 500

        print(f"[OK] Config persisted to Redis")

        original_config = config_manager.get_config('firecrawl').copy()
        config_manager.save_config('firecrawl', original_config)

        print(f"[OK] Persistence test completed")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
