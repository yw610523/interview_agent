"""
Rerank 配置测试

测试 Rerank 配置的增删改查和同步功能
"""
from app.config.config_manager import config_manager
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestRerankConfig:
    """Rerank 配置测试类"""

    def test_01_read_rerank_config(self):
        """测试读取 Rerank 配置"""
        print("\n=== Test 1: Read Rerank Config ===")

        rerank_config = config_manager.get_config('rerank')

        assert rerank_config is not None
        assert isinstance(rerank_config, dict)

        required_fields = ['enabled', 'model']
        for field in required_fields:
            assert field in rerank_config, f"Rerank config must contain {field} field"

        print(f"[OK] Enabled: {rerank_config.get('enabled')}")
        print(f"[OK] Model: {rerank_config.get('model')}")
        print(f"[OK] API URL: {rerank_config.get('api_url')}")

    def test_02_update_rerank_config(self):
        """测试更新 Rerank 配置"""
        print("\n=== Test 2: Update Rerank Config ===")

        original_config = config_manager.get_config('rerank').copy()

        try:
            new_config = {
                'enabled': True,
                'api_url': 'https://test.rerank.com/v1',
                'api_key': 'rk-test-key-456',
                'model': 'BAAI/bge-reranker-test'
            }

            success = config_manager.save_config('rerank', new_config)
            assert success

            config_manager.reload()

            updated_config = config_manager.get_config('rerank')
            assert updated_config.get('enabled') is True
            assert updated_config.get('model') == 'BAAI/bge-reranker-test'

            print(f"[OK] Enabled: {updated_config.get('enabled')}")
            print(f"[OK] Model: {updated_config.get('model')}")
            print(f"[OK] API URL: {updated_config.get('api_url')}")

        finally:
            config_manager.save_config('rerank', original_config)
            config_manager.reload()
            print(f"[OK] Restored original config")

    def test_03_toggle_rerank_enabled(self):
        """测试开关 Rerank"""
        print("\n=== Test 3: Toggle Rerank Enabled ===")

        original_config = config_manager.get_config('rerank').copy()

        try:
            # 启用
            new_config = original_config.copy()
            new_config['enabled'] = True
            config_manager.save_config('rerank', new_config)
            config_manager.reload()

            assert config_manager.get_config('rerank').get('enabled') is True
            print(f"[OK] Rerank enabled")

            # 禁用
            new_config['enabled'] = False
            config_manager.save_config('rerank', new_config)
            config_manager.reload()

            assert config_manager.get_config('rerank').get('enabled') is False
            print(f"[OK] Rerank disabled")

        finally:
            config_manager.save_config('rerank', original_config)
            config_manager.reload()

    def test_04_config_persistence(self):
        """测试配置持久化"""
        print("\n=== Test 4: Config Persistence ===")

        import yaml
        from pathlib import Path as PathLib

        test_config = {
            'enabled': True,
            'api_url': 'https://persist.rerank.com/v1',
            'api_key': 'rk-persist-key',
            'model': 'BAAI/bge-reranker-persist'
        }

        config_manager.save_config('rerank', test_config)

        config_file = PathLib(__file__).parent.parent.parent / 'config' / 'rerank.yaml'
        assert config_file.exists()

        with open(config_file, 'r', encoding='utf-8') as f:
            file_content = yaml.safe_load(f)

        assert file_content.get('enabled') is True
        assert file_content.get('model') == 'BAAI/bge-reranker-persist'

        print(f"[OK] Config persisted to file")

        original_config = config_manager.get_config('rerank').copy()
        config_manager.save_config('rerank', original_config)

        print(f"[OK] Persistence test completed")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
