"""
统一配置管理器（Redis 存储模式）

配置存储策略：
1. Redis 作为运行时配置的唯一存储
2. YAML 文件仅作为默认配置来源
3. 启动时将 YAML 配置同步到 Redis（如果 Redis 中没有）
4. 前端修改配置时仅更新 Redis
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import redis as redis_lib
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

# 初始化 ruamel.yaml 实例
ruamel = YAML()
ruamel.preserve_quotes = True
ruamel.indent(mapping=2, sequence=4, offset=2)


class ConfigManager:
    """
    配置管理器单例类

    配置架构：
    - Redis：运行时配置存储（唯一数据源）
    - YAML：默认配置模板（启动时同步到 Redis）
    
    读取优先级：
    1. Redis 中的运行时配置
    2. YAML 默认配置
    3. 硬编码默认值
    """

    _instance = None
    _config_dir_override: Optional[Path] = None  # 用于测试的配置目录覆盖
    redis_client = None  # Redis 客户端
    _yaml_defaults: Dict[str, Any] = {}  # YAML 默认配置缓存
    _redis_prefix = "config:"  # Redis 键前缀

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._init_redis_client()
        self._load_yaml_defaults()
        self._sync_defaults_to_redis()
        logger.info("配置管理器初始化成功（Redis 配置模式）")

    def _init_redis_client(self):
        """
        初始化 Redis 客户端
        
        注意：Redis 配置优先从环境变量读取，确保能够连接到 Redis
        其他配置模块由 _sync_defaults_to_redis() 处理
        """
        try:
            # 优先从环境变量读取 Redis 连接信息（避免循环依赖）
            host = os.getenv('REDIS_HOST') or 'localhost'
            port = int(os.getenv('REDIS_PORT', '6379'))
            password = os.getenv('REDIS_PASSWORD', '')
            db = int(os.getenv('REDIS_DB', '0'))
            
            if password:
                redis_url = f"redis://:{password}@{host}:{port}/{db}"
            else:
                redis_url = f"redis://{host}:{port}/{db}"
            
            self.redis_client = redis_lib.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info(f"Redis 配置存储初始化成功 ({host}:{port}/{db})")
        except Exception as e:
            logger.error(f"Redis 配置存储初始化失败: {e}")
            logger.warning("将使用内存模式（配置修改不会持久化）")
            self.redis_client = None

    def _resolve_env_variables(self, config: Any) -> Any:
        """递归解析配置中的环境变量"""
        if isinstance(config, dict):
            return {key: self._resolve_env_variables(value) for key, value in config.items()}
        elif isinstance(config, list):
            return [self._resolve_env_variables(item) for item in config]
        elif isinstance(config, str):
            pattern = r'\$\{([^}]+?)\}'
            match = re.fullmatch(pattern, config.strip())
            if match:
                expr = match.group(1)
                if ':-' in expr:
                    var_name, default_value = expr.split(':-', 1)
                    value = os.getenv(var_name, default_value)
                else:
                    value = os.getenv(expr, None)
                    if value is None:
                        return config
                return self._convert_type(value)

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
        """智能类型转换"""
        if not isinstance(value, str):
            return value
        if value.lower() in ('true', 'yes', 'on'):
            return True
        if value.lower() in ('false', 'no', 'off'):
            return False
        if value.lower() in ('null', 'none', ''):
            return None
        try:
            if '.' not in value:
                return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def _has_env_variables(self, config: Any) -> bool:
        """递归检查配置中是否包含环境变量占位符"""
        if isinstance(config, dict):
            return any(self._has_env_variables(v) for v in config.values())
        elif isinstance(config, list):
            return any(self._has_env_variables(item) for item in config)
        elif isinstance(config, str):
            return '${' in config
        return False

    def _load_config(self) -> Dict[str, Any]:
        """从配置文件目录加载配置"""
        if self._config_dir_override:
            logger.info(f"使用覆盖的配置目录: {self._config_dir_override}")
            return self._load_from_directory(self._config_dir_override)

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
            raise FileNotFoundError("Configuration directory not found.")

        return self._load_from_directory(config_dir)

    def _load_from_directory(self, config_dir: Path) -> Dict[str, Any]:
        """从指定目录加载所有 YAML 配置文件"""
        merged_config = {}
        yaml_files = list(config_dir.glob('*.yaml'))

        if not yaml_files:
            logger.error(f"配置目录 {config_dir} 中没有找到 YAML 文件")
            raise FileNotFoundError(f"No YAML files found in {config_dir}.")

        for yaml_file in yaml_files:
            try:
                config_key = yaml_file.stem
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    file_config = ruamel.load(f)
                if file_config:
                    merged_config[config_key] = file_config
                else:
                    merged_config[config_key] = {}
            except Exception as e:
                logger.error(f"加载配置文件 {yaml_file.name} 失败: {e}")
                merged_config[yaml_file.stem] = {}

        logger.info(f"成功加载 {len(merged_config)} 个配置模块")
        return merged_config

    def _load_yaml_defaults(self):
        """
        加载 YAML 默认配置并解析环境变量
        
        注意：保存原始配置（未解析）用于检测环境变量变化
        """
        raw_config = self._load_config()
        self._raw_yaml_config = raw_config.copy()  # 保存原始配置
        self._yaml_defaults = self._resolve_env_variables(raw_config)
        logger.info("YAML 默认配置加载完成")

    def _sync_defaults_to_redis(self):
        """
        将 YAML 默认配置同步到 Redis
        
        策略：
        1. 只有当 Redis 中没有该模块的配置时，才从 YAML 同步
        2. 如果 Redis 中已有配置（用户通过前端修改），则保留不变
        3. 排除 redis 模块，避免循环依赖问题
        """
        if not self.redis_client:
            return

        # 排除的模块列表（不能存储到 Redis 中）
        excluded_modules = {'redis'}

        synced_count = 0
        for module_name, module_config in self._yaml_defaults.items():
            # 跳过排除的模块
            if module_name in excluded_modules:
                logger.debug(f"跳过同步 {module_name} 配置到 Redis（避免循环依赖）")
                continue
            
            redis_key = f"{self._redis_prefix}{module_name}"
            existing = self.redis_client.get(redis_key)
            
            if existing is None:
                # Redis 中没有配置，从 YAML 同步默认值
                self.redis_client.set(redis_key, json.dumps(module_config, ensure_ascii=False))
                synced_count += 1
                logger.debug(f"同步默认配置到 Redis: {module_name}")
            else:
                # Redis 中已有配置（可能是用户修改的），保留不变
                logger.debug(f"Redis 中已有 {module_name} 配置，跳过同步")

        if synced_count > 0:
            logger.info(f"已将 {synced_count} 个模块的默认配置同步到 Redis")

    def _get_from_redis(self, module_name: str) -> Optional[Dict[str, Any]]:
        """从 Redis 获取配置"""
        if not self.redis_client:
            return None
        
        redis_key = f"{self._redis_prefix}{module_name}"
        try:
            data = self.redis_client.get(redis_key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"从 Redis 读取配置失败: {e}")
        return None

    def _save_to_redis(self, module_name: str, config_data: Dict[str, Any]) -> bool:
        """保存配置到 Redis，如果 Redis 不可用则降级到内存"""
        redis_key = f"{self._redis_prefix}{module_name}"
        
        # 尝试保存到 Redis
        if self.redis_client:
            try:
                self.redis_client.set(redis_key, json.dumps(config_data, ensure_ascii=False))
                return True
            except Exception as e:
                logger.error(f"保存配置到 Redis 失败: {e}")
        
        # 降级到内存存储
        self._yaml_defaults[module_name] = config_data
        logger.debug(f"配置已保存到内存: {module_name}")
        return True

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        通过点号分隔的路径获取配置值
        
        注意：redis 模块直接从 YAML/内存读取，避免循环依赖
        其他模块优先从 Redis 读取
        
        示例:
            config_manager.get('redis.host')  # 从 YAML 读取
            config_manager.get('llm.model')   # 从 Redis 读取
        """
        keys = key_path.split('.')
        module_name = keys[0]
        
        # redis 模块特殊处理：直接从内存读取
        if module_name == 'redis':
            module_config = self._yaml_defaults.get('redis', {})
        else:
            # 其他模块：优先从 Redis 获取
            module_config = self._get_from_redis(module_name)
            
            # Redis 为空则使用 YAML 默认值
            if module_config is None:
                module_config = self._yaml_defaults.get(module_name, {})
        
        # 嵌套路径查找
        value = module_config
        for key in keys[1:]:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default

    def get_config(self, module_name: str) -> Dict[str, Any]:
        """
        获取指定模块的完整配置
        
        注意：redis 模块直接从 YAML/内存读取，避免循环依赖
        其他模块优先从 Redis 读取，回退到 YAML
        """
        # redis 模块特殊处理：直接从内存读取（来自 YAML）
        if module_name == 'redis':
            return self._yaml_defaults.get('redis', {})
        
        # 其他模块：优先从 Redis 获取
        redis_config = self._get_from_redis(module_name)
        if redis_config is not None:
            return redis_config
        
        # 回退到 YAML 默认值（已包含内存修改）
        return self._yaml_defaults.get(module_name, {})

    def build_redis_url(self) -> str:
        """构建 Redis URL（用于向量服务）"""
        redis_config = self.get_config('redis')
        host = redis_config.get('host', 'localhost')
        port = redis_config.get('port', 6379)
        password = redis_config.get('password', '')
        
        if password:
            return f"redis://:{password}@{host}:{port}"
        else:
            return f"redis://{host}:{port}"

    def get_redis_url(self) -> str:
        """获取 Redis URL（build_redis_url 的别名）"""
        return self.build_redis_url()

    def reload(self):
        """重新加载配置（从 YAML 同步到 Redis）"""
        logger.info("重新加载配置...")
        self._load_yaml_defaults()
        self._sync_defaults_to_redis()
        logger.info("配置重新加载完成")

    @classmethod
    def set_config_dir(cls, config_dir: Path):
        """设置配置目录（用于测试）"""
        cls._config_dir_override = config_dir

    @classmethod
    def reset_config_dir(cls):
        """重置配置目录覆盖"""
        cls._config_dir_override = None

    def save_config(self, module_name: str, config_data: Dict[str, Any], persist_to_file: bool = False) -> bool:
        """
        保存配置到 Redis
        
        参数:
            module_name: 配置模块名称
            config_data: 配置数据
            persist_to_file: 是否同时持久化到文件（默认 False）
        
        注意：redis 模块不能保存到 Redis，避免循环依赖
        """
        # 排除 redis 模块
        if module_name == 'redis':
            logger.warning("无法保存 redis 配置到 Redis（避免循环依赖），已保存到内存")
            self._yaml_defaults['redis'] = config_data
            return True
        
        # 保存到 Redis
        success = self._save_to_redis(module_name, config_data)
        
        # 可选：持久化到文件（一般不建议）
        if persist_to_file:
            self._save_to_file(module_name, config_data)
        
        return success
    
    def _save_to_file(self, module_name: str, config_data: Dict[str, Any]):
        """将配置保存到文件（内部方法）"""
        try:
            if self._config_dir_override:
                config_dir = self._config_dir_override
            else:
                project_root = Path(__file__).parent.parent.parent
                config_dir_candidates = [project_root / "config", Path(__file__).parent]
                config_dir = None
                for candidate in config_dir_candidates:
                    if candidate.exists() and candidate.is_dir():
                        config_dir = candidate
                        break
                if not config_dir:
                    return

            file_path = config_dir / f"{module_name}.yaml"
            
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_data = ruamel.load(f)
                if isinstance(existing_data, dict) and isinstance(config_data, dict):
                    for key, value in config_data.items():
                        existing_data[key] = value
                    data_to_save = existing_data
                else:
                    data_to_save = config_data
            else:
                data_to_save = config_data
            
            with open(file_path, 'w', encoding='utf-8') as f:
                ruamel.dump(data_to_save, f)
            
            logger.info(f"配置已保存到文件: {file_path}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")

    @property
    def all_config(self) -> Dict[str, Any]:
        """获取所有配置（从 Redis，排除 redis 模块）"""
        result = {}
        if self.redis_client:
            for module_name in self._yaml_defaults.keys():
                # 排除 redis 模块
                if module_name == 'redis':
                    continue
                redis_key = f"{self._redis_prefix}{module_name}"
                data = self.redis_client.get(redis_key)
                if data:
                    result[module_name] = json.loads(data)
        return result or self._yaml_defaults.copy()


# 全局配置实例
config_manager = ConfigManager()


def get_config_value(key_path: str, default: Any = None) -> Any:
    """便捷函数：获取配置值"""
    return config_manager.get(key_path, default)
