"""
爬虫配置测试

测试爬虫配置的增删改查和同步功能
"""
from app.config.config_manager import config_manager
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestCrawlerConfig:
    """爬虫配置测试类"""

    def test_01_read_crawler_config(self):
        """测试读取爬虫配置"""
        print("\n=== 测试1: 读取爬虫配置 ===")

        crawler_config = config_manager.get_config('crawler')

        # 验证配置存在
        assert crawler_config is not None, "爬虫配置不能为空"
        assert isinstance(crawler_config, dict), "爬虫配置必须是字典类型"

        # 验证关键字段
        required_fields = ['sitemap_url', 'timeout', 'max_urls', 'delay_between_requests']
        for field in required_fields:
            assert field in crawler_config, f"爬虫配置必须包含 {field} 字段"

        print(f"[OK] Sitemap URL: {crawler_config.get('sitemap_url')}")
        print(f"[OK] Timeout: {crawler_config.get('timeout')}")
        print(f"[OK] Max URLs: {crawler_config.get('max_urls')}")
        print(f"[OK] Delay: {crawler_config.get('delay_between_requests')}")

    def test_02_update_crawler_basic_config(self):
        """测试更新爬虫基础配置"""
        print("\n=== 测试2: 更新爬虫基础配置 ===")

        # 保存原始配置
        original_config = config_manager.get_config('crawler').copy()

        try:
            # 创建新配置
            new_config = {
                'sitemap_url': 'https://test.example.com/sitemap.xml',
                'timeout': 60,
                'max_urls': 100,
                'delay_between_requests': 1.0,
                'output_dir': './test_results',
                'user_agent': 'TestBot/1.0'
            }

            # 保存配置
            success = config_manager.save_config('crawler', new_config)
            assert success, "保存爬虫配置应该成功"

            print(f"[OK] 配置已保存")

            # 重新加载配置
            config_manager.reload()

            # 验证配置已更新
            updated_config = config_manager.get_config('crawler')
            assert updated_config.get('sitemap_url') == 'https://test.example.com/sitemap.xml'
            assert updated_config.get('timeout') == 60
            assert updated_config.get('max_urls') == 100
            assert updated_config.get('delay_between_requests') == 1.0

            print(f"[OK] Sitemap URL 已更新: {updated_config.get('sitemap_url')}")
            print(f"[OK] Timeout 已更新: {updated_config.get('timeout')}")
            print(f"[OK] Max URLs 已更新: {updated_config.get('max_urls')}")
            print(f"[OK] Delay 已更新: {updated_config.get('delay_between_requests')}")

        finally:
            # 恢复原始配置
            config_manager.save_config('crawler', original_config)
            config_manager.reload()
            print(f"[OK] 已恢复原始配置")

    def test_03_update_url_filter_patterns(self):
        """测试更新 URL 过滤规则"""
        print("\n=== 测试3: 更新 URL 过滤规则 ===")

        # 保存原始配置
        original_config = config_manager.get_config('crawler').copy()

        try:
            # 设置 URL 过滤规则
            new_config = original_config.copy()
            new_config['url_include_patterns'] = ['/docs/*', '/api/*']
            new_config['url_exclude_patterns'] = ['/admin/*', '/private/*']

            config_manager.save_config('crawler', new_config)
            config_manager.reload()

            # 验证配置
            updated_config = config_manager.get_config('crawler')
            assert updated_config.get('url_include_patterns') == ['/docs/*', '/api/*']
            assert updated_config.get('url_exclude_patterns') == ['/admin/*', '/private/*']

            print(f"[OK] Include Patterns: {updated_config.get('url_include_patterns')}")
            print(f"[OK] Exclude Patterns: {updated_config.get('url_exclude_patterns')}")

        finally:
            # 恢复原始配置
            config_manager.save_config('crawler', original_config)
            config_manager.reload()
            print(f"[OK] 已恢复原始配置")

    def test_04_update_scheduler_config(self):
        """测试更新定时任务配置"""
        print("\n=== 测试4: 更新定时任务配置 ===")

        # 保存原始配置
        original_config = config_manager.get_config('crawler').copy()

        try:
            # 设置定时任务
            new_config = original_config.copy()
            if 'scheduler' not in new_config:
                new_config['scheduler'] = {}
            new_config['scheduler']['hour'] = 3
            new_config['scheduler']['minute'] = 30

            config_manager.save_config('crawler', new_config)
            config_manager.reload()

            # 验证配置
            updated_config = config_manager.get_config('crawler')
            scheduler = updated_config.get('scheduler', {})
            assert scheduler.get('hour') == 3
            assert scheduler.get('minute') == 30

            print(f"[OK] Scheduler Hour: {scheduler.get('hour')}")
            print(f"[OK] Scheduler Minute: {scheduler.get('minute')}")

        finally:
            # 恢复原始配置
            config_manager.save_config('crawler', original_config)
            config_manager.reload()
            print(f"[OK] 已恢复原始配置")

    def test_05_config_persistence(self):
        """测试配置持久化"""
        print("\n=== 测试5: 配置持久化 ===")

        import yaml
        from pathlib import Path as PathLib
        from app.config.config_manager import ConfigManager

        # 保存测试配置
        test_config = {
            'sitemap_url': 'https://persistence.test.com/sitemap.xml',
            'timeout': 45,
            'max_urls': 50,
            'delay_between_requests': 0.8
        }

        config_manager.save_config('crawler', test_config)

        # 从 ConfigManager 的覆盖目录读取文件（测试环境）
        config_dir = ConfigManager._config_dir_override
        if config_dir:
            # 测试环境：使用临时目录
            config_file = config_dir / 'crawler.yaml'
        else:
            # 生产环境：使用项目根目录
            config_file = PathLib(__file__).parent.parent.parent / 'config' / 'crawler.yaml'

        assert config_file.exists(), "配置文件应该存在"

        with open(config_file, 'r', encoding='utf-8') as f:
            file_content = yaml.safe_load(f)

        assert file_content.get('sitemap_url') == 'https://persistence.test.com/sitemap.xml'
        assert file_content.get('timeout') == 45

        print(f"[OK] 配置已持久化到文件")
        print(f"[OK] 文件内容验证通过")

        # 恢复原始配置（由 conftest.py 统一处理）
        print(f"[OK] 持久化测试完成")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
