"""
SMTP 邮件配置测试

测试 SMTP 配置的增删改查和同步功能
"""
from app.config.config_manager import config_manager
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSmtpConfig:
    """SMTP 配置测试类"""

    def test_01_read_smtp_config(self):
        """测试读取 SMTP 配置"""
        print("\n=== Test 1: Read SMTP Config ===")

        smtp_config = config_manager.get_config('smtp')

        # 验证配置存在
        assert smtp_config is not None, "SMTP config cannot be empty"
        assert isinstance(smtp_config, dict), "SMTP config must be a dict"

        # 验证关键字段
        required_fields = ['server', 'port', 'user', 'password']
        for field in required_fields:
            assert field in smtp_config, f"SMTP config must contain {field} field"

        print(f"[OK] Server: {smtp_config.get('server')}")
        print(f"[OK] Port: {smtp_config.get('port')}")
        print(f"[OK] User: {smtp_config.get('user')}")
        print(f"[OK] Password: {'***' if smtp_config.get('password') else '(empty)'}")

    def test_02_update_smtp_config(self):
        """测试更新 SMTP 配置"""
        print("\n=== Test 2: Update SMTP Config ===")

        # 保存原始配置
        original_config = config_manager.get_config('smtp').copy()

        try:
            # 创建新配置
            new_config = {
                'server': 'smtp.test.com',
                'port': 587,
                'user': 'test@test.com',
                'password': 'test_password',
                'test_user': 'recipient@test.com'
            }

            # 保存配置
            success = config_manager.save_config('smtp', new_config)
            assert success, "Save SMTP config should succeed"

            print(f"[OK] Config saved")

            # 重新加载配置
            config_manager.reload()

            # 验证配置已更新
            updated_config = config_manager.get_config('smtp')
            assert updated_config.get('server') == 'smtp.test.com'
            assert updated_config.get('port') == 587
            assert updated_config.get('user') == 'test@test.com'

            print(f"[OK] Server updated: {updated_config.get('server')}")
            print(f"[OK] Port updated: {updated_config.get('port')}")
            print(f"[OK] User updated: {updated_config.get('user')}")

        finally:
            # 恢复原始配置
            config_manager.save_config('smtp', original_config)
            config_manager.reload()
            print(f"[OK] Restored original config")

    def test_03_update_smtp_port(self):
        """测试更新 SMTP 端口"""
        print("\n=== Test 3: Update SMTP Port ===")

        # 保存原始配置
        original_config = config_manager.get_config('smtp').copy()

        try:
            # 设置不同端口
            new_config = original_config.copy()
            new_config['port'] = 465  # SSL 端口

            config_manager.save_config('smtp', new_config)
            config_manager.reload()

            # 验证配置
            updated_config = config_manager.get_config('smtp')
            assert updated_config.get('port') == 465

            print(f"[OK] Port: {updated_config.get('port')}")

        finally:
            # 恢复原始配置
            config_manager.save_config('smtp', original_config)
            config_manager.reload()
            print(f"[OK] Restored original config")

    def test_04_config_persistence(self):
        """测试配置持久化"""
        print("\n=== Test 4: Config Persistence ===")

        import yaml
        from pathlib import Path as PathLib

        # 保存测试配置
        test_config = {
            'server': 'persist.smtp.com',
            'port': 25,
            'user': 'persist@test.com',
            'password': 'persist_pass'
        }

        config_manager.save_config('smtp', test_config)

        # 直接从文件读取验证
        config_file = PathLib(__file__).parent.parent.parent / 'config' / 'smtp.yaml'
        assert config_file.exists(), "Config file should exist"

        with open(config_file, 'r', encoding='utf-8') as f:
            file_content = yaml.safe_load(f)

        assert file_content.get('server') == 'persist.smtp.com'
        assert file_content.get('port') == 25

        print(f"[OK] Config persisted to file")
        print(f"[OK] File content verified")

        # 恢复原始配置
        original_config = config_manager.get_config('smtp').copy()
        config_manager.save_config('smtp', original_config)

        print(f"[OK] Persistence test completed")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
