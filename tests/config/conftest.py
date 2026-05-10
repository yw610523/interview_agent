"""
pytest 配置

在所有测试开始前设置临时配置目录并初始化 Redis 配置存储
"""
import tempfile
import shutil
from pathlib import Path

from tests.config import ORIGINAL_CONFIG_DIR
from app.config.config_manager import ConfigManager


def pytest_sessionstart(session):
    """
    测试会话开始时调用
    创建临时配置目录并复制所有配置文件
    """
    print("\n" + "=" * 80)
    print("[TEST] Config test initialization (Redis 模式)")
    print("=" * 80)

    # 创建临时目录
    temp_dir = Path(tempfile.mkdtemp(prefix='test_config_'))

    # 复制所有配置文件到临时目录
    if ORIGINAL_CONFIG_DIR and ORIGINAL_CONFIG_DIR.exists():
        for file in ORIGINAL_CONFIG_DIR.glob('*.yaml'):
            shutil.copy2(file, temp_dir / file.name)
        print(f"[SETUP] Created temp config dir: {temp_dir}")
        print(f"[SETUP] Copied {len(list(temp_dir.glob('*.yaml')))} config files")

    # 设置 ConfigManager 使用临时目录
    ConfigManager.set_config_dir(temp_dir)
    # 重置单例以便重新初始化
    ConfigManager._instance = None
    ConfigManager._initialized = False
    # 重新创建实例，会触发 Redis 初始化和 YAML 同步
    from app.config.config_manager import config_manager
    print(f"[SETUP] ConfigManager initialized (Redis: {config_manager.redis_client is not None})")


def pytest_sessionfinish(session, exitstatus):
    """
    测试会话结束时调用
    清理临时配置目录
    """
    print("\n" + "=" * 80)
    print("[CLEANUP] Cleaning temp config")
    print("=" * 80)

    # 先保存临时目录引用（在重置之前）
    temp_dir = ConfigManager._config_dir_override

    # 清除配置目录覆盖
    ConfigManager.reset_config_dir()

    # 清理临时目录
    if temp_dir and temp_dir.exists():
        shutil.rmtree(temp_dir)
        print(f"[CLEANUP] Removed temp config dir: {temp_dir}")
