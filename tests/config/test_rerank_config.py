"""
Rerank 配置测试 (Redis 模式)

测试 Rerank 配置的增删改查功能（注意：rerank 现在嵌套在 llm.rerank 下）
"""
from app.config.config_manager import config_manager
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestRerankConfig:
    """Rerank 配置测试类（嵌套在 LLM 配置下）"""

    def test_01_read_rerank_config(self):
        """测试读取 Rerank 配置（优先 Redis）"""
        print("\n=== Test 1: Read Rerank Config ===")

        llm_config = config_manager.get_config('llm')
        rerank_config = llm_config.get('rerank', {})

        assert rerank_config is not None
        assert isinstance(rerank_config, dict)

        required_fields = ['enabled', 'model']
        for field in required_fields:
            assert field in rerank_config, f"Rerank config must contain {field} field"

        print(f"[OK] Enabled: {rerank_config.get('enabled')}")
        print(f"[OK] Model: {rerank_config.get('model')}")
        print(f"[OK] API Base: {rerank_config.get('api_base')}")

    def test_02_update_rerank_config(self):
        """测试更新 Rerank 配置（写入 Redis）"""
        print("\n=== Test 2: Update Rerank Config ===")

        original_llm_config = config_manager.get_config('llm').copy()

        try:
            new_llm_config = original_llm_config.copy()
            new_llm_config['rerank'] = {
                'enabled': True,
                'api_base': 'https://test.rerank.com/v1',
                'api_key': 'rk-test-key-456',
                'model': 'BAAI/bge-reranker-test'
            }

            success = config_manager.save_config('llm', new_llm_config)
            assert success

            updated_llm_config = config_manager.get_config('llm')
            updated_rerank = updated_llm_config.get('rerank', {})
            assert updated_rerank.get('enabled') is True
            assert updated_rerank.get('model') == 'BAAI/bge-reranker-test'

            print(f"[OK] Enabled: {updated_rerank.get('enabled')}")
            print(f"[OK] Model: {updated_rerank.get('model')}")

        finally:
            config_manager.save_config('llm', original_llm_config)
            print(f"[OK] Restored original config")

    def test_03_toggle_rerank_enabled(self):
        """测试开关 Rerank（写入 Redis）"""
        print("\n=== Test 3: Toggle Rerank Enabled ===")

        original_llm_config = config_manager.get_config('llm').copy()

        try:
            # 启用
            new_config = original_llm_config.copy()
            if 'rerank' not in new_config:
                new_config['rerank'] = {}
            new_config['rerank']['enabled'] = True
            config_manager.save_config('llm', new_config)

            assert config_manager.get_config('llm').get('rerank', {}).get('enabled') is True
            print(f"[OK] Rerank enabled")

            # 禁用
            new_config['rerank']['enabled'] = False
            config_manager.save_config('llm', new_config)

            assert config_manager.get_config('llm').get('rerank', {}).get('enabled') is False
            print(f"[OK] Rerank disabled")

        finally:
            config_manager.save_config('llm', original_llm_config)

    def test_04_config_redis_storage(self):
        """测试配置存储到 Redis"""
        print("\n=== Test 4: Config Storage to Redis ===")

        original_llm_config = config_manager.get_config('llm').copy()

        test_rerank = {
            'enabled': True,
            'api_base': 'https://persist.rerank.com/v1',
            'api_key': 'rk-persist-key',
            'model': 'BAAI/bge-reranker-persist'
        }

        new_llm_config = original_llm_config.copy()
        new_llm_config['rerank'] = test_rerank
        config_manager.save_config('llm', new_llm_config)

        # 验证配置在 Redis 中
        stored_llm_config = config_manager.get_config('llm')
        stored_rerank = stored_llm_config.get('rerank', {})
        assert stored_rerank.get('enabled') is True
        assert stored_rerank.get('model') == 'BAAI/bge-reranker-persist'

        print(f"[OK] Config saved to Redis")
        print(f"[OK] Redis content verified")
        print(f"[OK] Persistence test completed (Redis mode)")

        # 恢复
        config_manager.save_config('llm', original_llm_config)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
