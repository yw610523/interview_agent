"""
配置测试包

测试所有配置模块的增删改查和同步功能
使用临时配置目录，避免影响实际配置文件
"""
from pathlib import Path

# 原始配置目录
ORIGINAL_CONFIG_DIR = Path(__file__).parent.parent.parent / 'config'
