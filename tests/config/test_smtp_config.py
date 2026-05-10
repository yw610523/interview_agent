"""
SMTP 配置测试 (Redis 模式)
"""
from app.config.config_manager import config_manager
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSmtpConfig:
    """SMTP 配置测试类"""

    def test_01_read_smtp_config(self):
        """测试读取 SMTP 配置（优先 Redis）"""
        print("\n=== Test 1: Read SMTP Config ===")

        smtp_config = config_manager.get_config('smtp')

        assert smtp_config is not None, "SMTP config cannot be empty"
        assert isinstance(smtp_config, dict), "SMTP config must be dict type"

        required_fields = ['server', 'port', 'user', 'password']
        for field in required_fields:
            assert field in smtp_config, f"SMTP config must contain {field} field"

        print(f"[OK] Server: {smtp_config.get('server')}")
        print(f"[OK] Port: {smtp_config.get('port')}")
        print(f"[OK] User: {smtp_config.get('user')}")
        print(f"[OK] Password: {'***' if smtp_config.get('password') else '(empty)'}")

    def test_02_update_smtp_config(self):
        """测试更新 SMTP 配置（写入 Redis）"""
        print("\n=== Test 2: Update SMTP Config ===")

        original_config = config_manager.get_config('smtp').copy()

        try:
            new_config = {
                'server': 'test.smtp.example.com',
                'port': 587,
                'user': 'test@example.com',
                'password': 'test_password'
            }

            success = config_manager.save_config('smtp', new_config)
            assert success, "Save SMTP config should succeed"

            print(f"[OK] Config saved to Redis")

            updated_config = config_manager.get_config('smtp')
            assert updated_config.get('server') == 'test.smtp.example.com'
            assert updated_config.get('port') == 587
            assert updated_config.get('user') == 'test@example.com'

            print(f"[OK] Server updated: {updated_config.get('server')}")
            print(f"[OK] Port updated: {updated_config.get('port')}")
            print(f"[OK] User updated: {updated_config.get('user')}")

        finally:
            config_manager.save_config('smtp', original_config)
            print(f"[OK] Restored original config")

    def test_03_update_smtp_port(self):
        """测试更新 SMTP 端口（写入 Redis）"""
        print("\n=== Test 3: Update SMTP Port ===")

        original_config = config_manager.get_config('smtp').copy()

        try:
            new_config = original_config.copy()
            new_config['port'] = 465

            config_manager.save_config('smtp', new_config)

            updated_config = config_manager.get_config('smtp')
            assert updated_config.get('port') == 465

            print(f"[OK] Port updated: {updated_config.get('port')}")

        finally:
            config_manager.save_config('smtp', original_config)
            print(f"[OK] Restored original config")

    def test_04_config_redis_storage(self):
        """测试配置存储到 Redis"""
        print("\n=== Test 4: Config Storage to Redis ===")

        test_config = {
            'server': 'persist.smtp.com',
            'port': 993,
            'user': 'persist@test.com',
            'password': 'persist_test'
        }

        config_manager.save_config('smtp', test_config)

        redis_config = config_manager.get_config('smtp')
        assert redis_config.get('server') == 'persist.smtp.com'
        assert redis_config.get('port') == 993
        assert redis_config.get('user') == 'persist@test.com'

        print(f"[OK] Config saved to Redis")
        print(f"[OK] Redis content verified")
        print(f"[OK] Persistence test completed (Redis mode)")


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '-s'])
