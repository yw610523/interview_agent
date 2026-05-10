"""
Content 和 Service 配置测试 (Redis 模式)

测试内容处理和服务配置的增删改查功能
"""
from app.config.config_manager import config_manager
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestContentConfig:
    """Content 配置测试类"""

    def test_01_read_content_config(self):
        """测试读取 Content 配置（优先 Redis）"""
        print("\n=== Test 1: Read Content Config ===")

        content_config = config_manager.get_config('content')

        assert content_config is not None
        assert isinstance(content_config, dict)
        # chunk_size 是核心配置项
        assert 'chunk_size' in content_config

        print(f"[OK] Chunk Size: {content_config.get('chunk_size')}")
        print(f"[OK] Chunk Overlap: {content_config.get('chunk_overlap')}")
        print(f"[OK] Chunking Mode: {content_config.get('chunking_mode')}")

    def test_02_update_content_config(self):
        """测试更新 Content 配置（写入 Redis）"""
        print("\n=== Test 2: Update Content Config ===")

        original_config = config_manager.get_config('content').copy()

        try:
            new_config = original_config.copy()
            new_config['chunk_size'] = 1024

            success = config_manager.save_config('content', new_config)
            assert success

            # 直接读 Redis，无需 reload
            updated_config = config_manager.get_config('content')
            assert updated_config.get('chunk_size') == 1024

            print(f"[OK] Chunk Size updated: {updated_config.get('chunk_size')}")

        finally:
            config_manager.save_config('content', original_config)
            print(f"[OK] Restored original config")


class TestServiceConfig:
    """Service 配置测试类"""

    def test_01_read_service_config(self):
        """测试读取 Service 配置（优先 Redis）"""
        print("\n=== Test 1: Read Service Config ===")

        service_config = config_manager.get_config('service')

        assert service_config is not None
        assert isinstance(service_config, dict)

        required_fields = ['app_port']
        for field in required_fields:
            assert field in service_config, f"Service config must contain {field} field"

        print(f"[OK] App Port: {service_config.get('app_port')}")

    def test_02_update_service_config(self):
        """测试更新 Service 配置（写入 Redis）"""
        print("\n=== Test 2: Update Service Config ===")

        original_config = config_manager.get_config('service').copy()

        try:
            new_config = original_config.copy()
            new_config['app_port'] = 9999

            success = config_manager.save_config('service', new_config)
            assert success

            # 直接读 Redis，无需 reload
            updated_config = config_manager.get_config('service')
            assert updated_config.get('app_port') == 9999

            print(f"[OK] App Port updated: {updated_config.get('app_port')}")

        finally:
            config_manager.save_config('service', original_config)
            print(f"[OK] Restored original config")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
