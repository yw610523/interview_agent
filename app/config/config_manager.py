"""
统一配置管理器

从 config.yaml 加载所有配置，替代 .env 文件
"""

import os
import re
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

# 初始化 ruamel.yaml 实例
ruamel = YAML()
ruamel.preserve_quotes = True
ruamel.indent(mapping=2, sequence=4, offset=2)


class ConfigManager:
    """
    配置管理器单例类

    负责从 config.yaml 加载和管理所有应用配置
    """

    _instance = None
    _config = None
    _config_dir_override: Optional[Path] = None  # 用于测试的配置目录覆盖

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._config = self._load_config()
        # 解析配置中的环境变量
        self._config = self._resolve_env_variables(self._config)
        logger.info("配置管理器初始化成功")

    def _resolve_env_variables(self, config: Any) -> Any:
        """
        递归解析配置中的环境变量

        支持格式:
        - ${VAR_NAME:-default_value}  (有默认值)
        - ${VAR_NAME}  (无默认值，如果环境变量不存在则保持原样)

        参数:
            config: 配置数据（可以是字典、列表或字符串）

        返回:
            解析后的配置数据
        """
        if isinstance(config, dict):
            return {key: self._resolve_env_variables(value) for key, value in config.items()}
        elif isinstance(config, list):
            return [self._resolve_env_variables(item) for item in config]
        elif isinstance(config, str):
            # 匹配 ${VAR_NAME:-default} 或 ${VAR_NAME}
            pattern = r'\$\{([^}]+?)\}'

            # 检查是否整个字符串都是环境变量
            match = re.fullmatch(pattern, config.strip())
            if match:
                expr = match.group(1)
                if ':-' in expr:
                    var_name, default_value = expr.split(':-', 1)
                    value = os.getenv(var_name, default_value)
                else:
                    value = os.getenv(expr, None)
                    if value is None:
                        return config  # 保持原样

                # 智能类型转换
                return self._convert_type(value)

            # 部分包含环境变量，只进行字符串替换
            def replace_env(match):
                expr = match.group(1)
                if ':-' in expr:
                    var_name, default_value = expr.split(':-', 1)
                    return os.getenv(var_name, default_value)
                else:
                    return os.getenv(expr, match.group(0))

            return re.sub(pattern, replace_env, config)
        else:
            return config

    def _convert_type(self, value: str) -> Any:
        """
        智能类型转换

        将字符串转换为合适的 Python 类型：
        - 'true'/'false' -> bool
        - 'null'/'None' -> None
        - 纯数字 -> int 或 float
        - 其他 -> str
        """
        if not isinstance(value, str):
            return value

        # 布尔值
        if value.lower() in ('true', 'yes', 'on'):
            return True
        if value.lower() in ('false', 'no', 'off'):
            return False

        # None
        if value.lower() in ('null', 'none', ''):
            return None

        # 整数
        try:
            if '.' not in value:
                return int(value)
        except ValueError:
            pass

        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass

        # 默认返回字符串
        return value

    def _load_config(self) -> Dict[str, Any]:
        """
        从多个独立配置文件加载配置

        支持两种模式：
        1. 多文件模式（推荐）：从 config/*.yaml 加载
        2. 单文件模式（兼容）：从 config.yaml 加载

        返回:
            配置字典
        """
        # 如果设置了配置目录覆盖（测试用），直接使用
        if self._config_dir_override:
            logger.info(f"使用覆盖的配置目录: {self._config_dir_override}")
            return self._load_from_directory(self._config_dir_override)

        # 正常模式：查找配置目录
        project_root = Path(__file__).parent.parent.parent
        config_dir_candidates = [
            project_root / "config",  # 项目根目录的 config/ (Docker部署时使用)
            Path(__file__).parent,     # app/config/ (开发时使用)
        ]

        # 找到第一个存在的配置目录
        config_dir = None
        for candidate in config_dir_candidates:
            if candidate.exists() and candidate.is_dir():
                config_dir = candidate
                break

        if not config_dir:
            logger.error("未找到配置目录")
            raise FileNotFoundError(
                "Configuration directory not found. "
                "Please ensure config/*.yaml files exist in the project root or app/config/ directory."
            )

        return self._load_from_directory(config_dir)

    def _load_from_directory(self, config_dir: Path) -> Dict[str, Any]:
        """
        从指定目录自动加载所有 YAML 配置文件

        自动发现机制：
        - 扫描目录下所有 .yaml 文件
        - 文件名（不含扩展名）作为配置键
        - 文件内容作为配置值

        参数:
            config_dir: 配置文件目录路径

        返回:
            合并后的配置字典
        """
        merged_config = {}

        # 自动扫描所有 YAML 文件
        yaml_files = list(config_dir.glob('*.yaml'))

        if not yaml_files:
            logger.error(f"配置目录 {config_dir} 中没有找到 YAML 文件")
            raise FileNotFoundError(
                f"No YAML configuration files found in {config_dir}. "
                f"Please ensure at least one *.yaml file exists."
            )

        for yaml_file in yaml_files:
            try:
                # 文件名（不含扩展名）作为配置键
                config_key = yaml_file.stem

                with open(yaml_file, 'r', encoding='utf-8') as f:
                    file_config = ruamel.load(f)

                if file_config:
                    merged_config[config_key] = file_config
                    logger.debug(f"加载配置: {yaml_file.name} -> {config_key}")
                else:
                    merged_config[config_key] = {}

            except Exception as e:
                logger.error(f"加载配置文件 {yaml_file.name} 失败: {str(e)}")
                # 使用空配置，避免整个系统崩溃
                merged_config[yaml_file.stem] = {}

        logger.info(f"成功加载 {len(merged_config)} 个配置模块")
        return merged_config

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        通过点号分隔的路径获取配置值

        例如:
        - get('smtp.server') 获取 smtp.server 的值
        - get('llm.model') 获取 llm.model 的值
        - get('redis') 获取整个 redis 配置字典

        参数:
            key_path: 配置键路径（支持点号分隔）
            default: 默认值

        返回:
            配置值
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def get_config(self, module_name: str) -> Dict[str, Any]:
        """
        获取指定模块的配置

        这是一个通用方法，替代所有 get_xxx_config() 方法

        例如:
        - get_config('smtp') 替代 get_smtp_config()
        - get_config('llm') 替代 get_llm_config()
        - get_config('redis') 替代 get_redis_config()

        参数:
            module_name: 配置模块名称（如 'smtp', 'llm', 'redis' 等）

        返回:
            配置字典，如果不存在则返回空字典
        """
        return self._config.get(module_name, {})

    def build_redis_url(self) -> str:
        """
        构建 Redis URL

        返回:
            Redis URL 字符串，格式: redis://[:password@]host:port
        """
        redis_config = self.get_config('redis')
        host = redis_config.get('host', 'localhost')
        port = redis_config.get('port', 6379)
        password = redis_config.get('password', '')

        if password:
            return f"redis://:{password}@{host}:{port}"
        else:
            return f"redis://{host}:{port}"

    def reload(self):
        """重新加载配置文件"""
        logger.info("重新加载配置文件...")
        self._config = self._load_config()
        logger.info("配置文件重新加载完成")

    @classmethod
    def set_config_dir(cls, config_dir: Path):
        """
        设置配置目录（用于测试）

        参数:
            config_dir: 配置目录路径
        """
        cls._config_dir_override = config_dir
        logger.info(f"配置目录已设置为: {config_dir}")

    @classmethod
    def reset_config_dir(cls):
        """重置配置目录覆盖（清除测试设置）"""
        cls._config_dir_override = None
        logger.info("配置目录覆盖已清除")

    def save_config(self, config_key: str, config_data: Dict[str, Any]) -> bool:
        """
        保存单个配置项到对应的配置文件

        参数:
            config_key: 配置键（如 'crawler', 'llm', 'smtp' 等）
            config_data: 配置数据字典

        返回:
            是否保存成功
        """
        try:
            # 确定配置目录：优先使用覆盖目录（测试），否则查找标准目录
            if self._config_dir_override:
                config_dir = self._config_dir_override
            else:
                project_root = Path(__file__).parent.parent.parent
                config_dir_candidates = [
                    project_root / "config",
                    Path(__file__).parent,
                ]

                config_dir = None
                for candidate in config_dir_candidates:
                    if candidate.exists() and candidate.is_dir():
                        config_dir = candidate
                        break

                if not config_dir:
                    logger.error("未找到配置目录")
                    return False

            filename = f"{config_key}.yaml"
            file_path = config_dir / filename
                        
            # 如果文件存在，读取并合并（保留注释）
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_data = ruamel.load(f)
                            
                # 合并新数据到现有数据（保留原有键的注释）
                if isinstance(existing_data, dict) and isinstance(config_data, dict):
                    for key, value in config_data.items():
                        existing_data[key] = value
                    data_to_save = existing_data
                else:
                    data_to_save = config_data
            else:
                data_to_save = config_data
                        
            # 写回文件（保留注释）
            with open(file_path, 'w', encoding='utf-8') as f:
                ruamel.dump(data_to_save, f)

            logger.info(f"配置已保存到: {file_path}")

            # 重新加载所有配置以应用更改
            self.reload()

            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return False

    @property
    def all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()


# 全局配置实例
config_manager = ConfigManager()


def get_config_value(key_path: str, default: Any = None) -> Any:
    """
    便捷函数：获取配置值

    参数:
        key_path: 配置键路径
        default: 默认值

    返回:
        配置值
    """
    return config_manager.get(key_path, default)
