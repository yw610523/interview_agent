"""
Redis 配置测试

测试 Redis 配置的增删改查和同步功能
"""
from app.config.config_manager import config_manager
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestRedisConfig:
    """Redis 配置测试类"""

    def test_01_read_redis_config(self):
        """测试读取 Redis 配置"""
        print("\n=== 测试1: 读取 Redis 配置 ===")

        redis_config = config_manager.get_config('redis')

        # 验证配置存在
        assert redis_config is not None, "Redis 配置不能为空"
        assert isinstance(redis_config, dict), "Redis 配置必须是字典类型"

        # 验证字段存在
        assert 'host' in redis_config, "Redis 配置必须包含 host 字段"
        assert 'port' in redis_config, "Redis 配置必须包含 port 字段"
        assert 'password' in redis_config, "Redis 配置必须包含 password 字段"

        print(f"[OK] Host: {redis_config.get('host')}")
        print(f"[OK] Port: {redis_config.get('port')}")
        print(f"[OK] Password: {'***' if redis_config.get('password') else '(empty)'}")

    def test_02_build_redis_url(self):
        """测试构建 Redis URL"""
        print("\n=== 测试2: 构建 Redis URL ===")

        redis_url = config_manager.build_redis_url()

        # 验证 URL 格式
        assert redis_url is not None, "Redis URL 不能为空"
        assert isinstance(redis_url, str), "Redis URL 必须是字符串"
        assert redis_url.startswith('redis://'), f"Redis URL 必须以 redis:// 开头，实际: {redis_url}"

        print(f"[OK] 构建的 URL: {redis_url}")

        # 验证 URL 包含必要信息
        redis_config = config_manager.get_config('redis')
        host = redis_config.get('host', 'localhost')
        port = redis_config.get('port', 6379)

        assert host in redis_url, f"URL 应包含 host: {host}"
        assert str(port) in redis_url, f"URL 应包含 port: {port}"

        print(f"[OK] URL 格式正确")

    def test_03_update_redis_config(self):
        """测试更新 Redis 配置"""
        print("\n=== 测试3: 更新 Redis 配置 ===")

        # 保存原始配置
        original_config = config_manager.get_config('redis').copy()

        try:
            # 创建新配置
            new_config = {
                'host': 'test.redis.example.com',
                'port': 6380,
                'password': 'test_password'
            }

            # 保存配置
            success = config_manager.save_config('redis', new_config)
            assert success, "保存 Redis 配置应该成功"

            print(f"[OK] 配置已保存")

            # 重新加载配置
            config_manager.reload()

            # 验证配置已更新
            updated_config = config_manager.get_config('redis')
            assert updated_config.get('host') == 'test.redis.example.com', "Host 应该已更新"
            assert updated_config.get('port') == 6380, "Port 应该已更新"
            assert updated_config.get('password') == 'test_password', "Password 应该已更新"

            print(f"[OK] Host 已更新: {updated_config.get('host')}")
            print(f"[OK] Port 已更新: {updated_config.get('port')}")
            print(f"[OK] Password 已更新: {'***'}")

            # 验证 URL 也更新了
            new_url = config_manager.build_redis_url()
            assert 'test.redis.example.com' in new_url, "URL 应该包含新的 host"
            assert '6380' in new_url, "URL 应该包含新的 port"

            print(f"[OK] URL 已更新: {new_url}")

        finally:
            # 恢复原始配置
            config_manager.save_config('redis', original_config)
            config_manager.reload()
            print(f"[OK] 已恢复原始配置")

    def test_04_redis_url_with_password(self):
        """测试带密码的 Redis URL 构建"""
        print("\n=== 测试4: 带密码的 Redis URL 构建 ===")

        # 保存原始配置
        original_config = config_manager.get_config('redis').copy()

        try:
            # 设置带密码的配置
            config_with_password = {
                'host': 'secure.redis.example.com',
                'port': 6381,
                'password': 'secret123'
            }

            config_manager.save_config('redis', config_with_password)
            config_manager.reload()

            # 验证 URL 格式
            url = config_manager.build_redis_url()
            print(f"[OK] 带密码的 URL: {url}")

            # 验证密码在 URL 中（格式: redis://:password@host:port）
            assert ':secret123@' in url, "URL 应该包含密码（格式: :password@）"
            assert 'secure.redis.example.com' in url, "URL 应该包含 host"
            assert '6381' in url, "URL 应该包含 port"

            print(f"[OK] 密码格式正确")

        finally:
            # 恢复原始配置
            config_manager.save_config('redis', original_config)
            config_manager.reload()
            print(f"[OK] 已恢复原始配置")

    def test_05_redis_url_without_password(self):
        """测试不带密码的 Redis URL 构建"""
        print("\n=== 测试5: 不带密码的 Redis URL 构建 ===")

        # 保存原始配置
        original_config = config_manager.get_config('redis').copy()

        try:
            # 设置不带密码的配置
            config_without_password = {
                'host': 'public.redis.example.com',
                'port': 6382,
                'password': ''
            }

            config_manager.save_config('redis', config_without_password)
            config_manager.reload()

            # 验证 URL 格式
            url = config_manager.build_redis_url()
            print(f"[OK] 不带密码的 URL: {url}")

            # 验证 URL 不包含密码分隔符
            assert '@' not in url, "不带密码的 URL 不应该包含 @"
            assert 'public.redis.example.com' in url, "URL 应该包含 host"
            assert '6382' in url, "URL 应该包含 port"

            # 验证格式为 redis://host:port
            expected_format = 'redis://public.redis.example.com:6382'
            assert url == expected_format, f"URL 格式应该是 {expected_format}，实际: {url}"

            print(f"[OK] 无密码格式正确")

        finally:
            # 恢复原始配置
            config_manager.save_config('redis', original_config)
            config_manager.reload()
            print(f"[OK] 已恢复原始配置")

    def test_06_config_persistence(self):
        """测试配置持久化"""
        print("\n=== 测试6: 配置持久化 ===")

        import yaml
        from pathlib import Path as PathLib
        from app.config.config_manager import ConfigManager

        # 保存测试配置
        test_config = {
            'host': 'persistence.test.com',
            'port': 6399,
            'password': 'persist_test'
        }

        config_manager.save_config('redis', test_config)

        # 从 ConfigManager 的覆盖目录读取文件（测试环境）
        config_dir = ConfigManager._config_dir_override
        if config_dir:
            # 测试环境：使用临时目录
            config_file = config_dir / 'redis.yaml'
        else:
            # 生产环境：使用项目根目录
            config_file = PathLib(__file__).parent.parent.parent / 'config' / 'redis.yaml'

        assert config_file.exists(), "配置文件应该存在"

        with open(config_file, 'r', encoding='utf-8') as f:
            file_content = yaml.safe_load(f)

        assert file_content.get('host') == 'persistence.test.com', "文件中的 host 应该匹配"
        assert file_content.get('port') == 6399, "文件中的 port 应该匹配"
        assert file_content.get('password') == 'persist_test', "文件中的 password 应该匹配"

        print(f"[OK] 配置已持久化到文件")
        print(f"[OK] 文件内容验证通过")

        # 恢复原始配置（由 conftest.py 统一处理）
        print(f"[OK] 持久化测试完成")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
