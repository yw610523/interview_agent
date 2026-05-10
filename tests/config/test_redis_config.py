"""
Redis 配置测试 (Redis 模式)

测试 Redis 配置的增删改查和同步功能
"""
from app.config.config_manager import config_manager
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestRedisConfig:
    """Redis 配置测试类"""

    def test_01_read_redis_config(self):
        """测试读取 Redis 配置（优先 Redis）"""
        print("\n=== 测试1: 读取 Redis 配置 ===")

        redis_config = config_manager.get_config('redis')

        assert redis_config is not None, "Redis 配置不能为空"
        assert isinstance(redis_config, dict), "Redis 配置必须是字典类型"

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

        assert redis_url is not None, "Redis URL 不能为空"
        assert isinstance(redis_url, str), "Redis URL 必须是字符串"
        assert redis_url.startswith('redis://'), f"Redis URL 必须以 redis:// 开头，实际: {redis_url}"

        print(f"[OK] 构建的 URL: {redis_url}")

        redis_config = config_manager.get_config('redis')
        host = redis_config.get('host', 'localhost')
        port = redis_config.get('port', 6379)

        assert host in redis_url, f"URL 应包含 host: {host}"
        assert str(port) in redis_url, f"URL 应包含 port: {port}"

        print(f"[OK] URL 格式正确")

    def test_03_update_redis_config(self):
        """测试更新 Redis 配置（写入 Redis）"""
        print("\n=== 测试3: 更新 Redis 配置 ===")

        original_config = config_manager.get_config('redis').copy()

        try:
            new_config = {
                'host': 'test.redis.example.com',
                'port': 6380,
                'password': 'test_password'
            }

            success = config_manager.save_config('redis', new_config)
            assert success, "保存 Redis 配置应该成功"

            print(f"[OK] 配置已保存到 Redis")

            # 直接读 Redis，无需 reload
            updated_config = config_manager.get_config('redis')
            assert updated_config.get('host') == 'test.redis.example.com', "Host 应该已更新"
            assert updated_config.get('port') == 6380, "Port 应该已更新"
            assert updated_config.get('password') == 'test_password', "Password 应该已更新"

            print(f"[OK] Host 已更新: {updated_config.get('host')}")
            print(f"[OK] Port 已更新: {updated_config.get('port')}")
            print(f"[OK] Password 已更新: {'***'}")

            new_url = config_manager.build_redis_url()
            assert 'test.redis.example.com' in new_url, "URL 应该包含新的 host"
            assert '6380' in new_url, "URL 应该包含新的 port"

            print(f"[OK] URL 已更新: {new_url}")

        finally:
            config_manager.save_config('redis', original_config)
            print(f"[OK] 已恢复原始配置")

    def test_04_redis_url_with_password(self):
        """测试带密码的 Redis URL 构建（写入 Redis）"""
        print("\n=== 测试4: 带密码的 Redis URL 构建 ===")

        original_config = config_manager.get_config('redis').copy()

        try:
            config_with_password = {
                'host': 'secure.redis.example.com',
                'port': 6381,
                'password': 'secret123'
            }

            config_manager.save_config('redis', config_with_password)

            url = config_manager.build_redis_url()
            print(f"[OK] 带密码的 URL: {url}")

            assert ':secret123@' in url, "URL 应该包含密码（格式: :password@）"
            assert 'secure.redis.example.com' in url, "URL 应该包含 host"
            assert '6381' in url, "URL 应该包含 port"

            print(f"[OK] 密码格式正确")

        finally:
            config_manager.save_config('redis', original_config)
            print(f"[OK] 已恢复原始配置")

    def test_05_redis_url_without_password(self):
        """测试不带密码的 Redis URL 构建（写入 Redis）"""
        print("\n=== 测试5: 不带密码的 Redis URL 构建 ===")

        original_config = config_manager.get_config('redis').copy()

        try:
            config_without_password = {
                'host': 'public.redis.example.com',
                'port': 6382,
                'password': ''
            }

            config_manager.save_config('redis', config_without_password)

            url = config_manager.build_redis_url()
            print(f"[OK] 不带密码的 URL: {url}")

            assert '@' not in url, "不带密码的 URL 不应该包含 @"
            assert 'public.redis.example.com' in url, "URL 应该包含 host"
            assert '6382' in url, "URL 应该包含 port"

            expected_format = 'redis://public.redis.example.com:6382'
            assert url == expected_format, f"URL 格式应该是 {expected_format}，实际: {url}"

            print(f"[OK] 无密码格式正确")

        finally:
            config_manager.save_config('redis', original_config)
            print(f"[OK] 已恢复原始配置")

    def test_06_config_redis_storage(self):
        """测试配置存储到 Redis"""
        print("\n=== 测试6: 配置存储到 Redis ===")

        test_config = {
            'host': 'persistence.test.com',
            'port': 6399,
            'password': 'persist_test'
        }

        config_manager.save_config('redis', test_config)

        # 验证配置在 Redis 中
        redis_config = config_manager.get_config('redis')
        assert redis_config.get('host') == 'persistence.test.com', "Redis 中的 host 应该匹配"
        assert redis_config.get('port') == 6399, "Redis 中的 port 应该匹配"
        assert redis_config.get('password') == 'persist_test', "Redis 中的 password 应该匹配"

        print(f"[OK] 配置已保存到 Redis")
        print(f"[OK] Redis 内容验证通过")
        print(f"[OK] 持久化测试完成（Redis 模式）")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
