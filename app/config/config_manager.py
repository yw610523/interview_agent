"""
统一配置管理器

使用YAML格式统一管理所有系统配置，支持：
- 分层配置结构
- 热加载更新
- 环境变量覆盖（用于敏感信息）
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigManager:
    """统一配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为 app/config/config.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self):
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}

            logger.info(f"配置已加载: {self.config_path}")

            # 应用环境变量覆盖（优先级更高）
            self._apply_env_overrides()

        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            raise

    def _apply_env_overrides(self):
        """
        应用环境变量覆盖
        允许通过环境变量覆盖YAML配置中的值
        例如: APP_PORT=8080 会覆盖 app.port
        """
        # 加载.env文件
        env_file = Path(__file__).parent.parent.parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)

        # 定义环境变量映射
        env_mappings = {
            "APP_PORT": "app.port",
            "OPENAI_API_KEY": "llm.api_key",
            "OPENAI_API_BASE": "llm.api_base",
            "OPENAI_MODEL": "llm.model",
            "OPENAI_EMBEDDING_MODEL": "llm.embedding_model",
            "EMBEDDING_DIMENSION": "llm.embedding_dimension",
            "MODEL_MAX_INPUT_TOKENS": "llm.max_input_tokens",
            "MODEL_MAX_OUTPUT_TOKENS": "llm.max_output_tokens",
            "REDIS_URL": "redis.url",
            "SMTP_SERVER": "email.smtp_server",
            "SMTP_PORT": "email.smtp_port",
            "SMTP_USER": "email.smtp_user",
            "SMTP_PASSWORD": "email.smtp_password",
            "SMTP_TEST_USER": "email.test_user",
            "SCHEDULER_HOUR": "scheduler.hour",
            "SCHEDULER_MINUTE": "scheduler.minute",
        }

        for env_key, config_key in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value is not None and env_value != "":
                # 转换类型
                current_value = self.get(config_key)
                if isinstance(current_value, int):
                    try:
                        env_value = int(env_value)
                    except ValueError:
                        pass
                elif isinstance(current_value, float):
                    try:
                        env_value = float(env_value)
                    except ValueError:
                        pass

                self.set(config_key, env_value)
                logger.debug(f"环境变量覆盖: {env_key} -> {config_key} = {env_value}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号访问嵌套配置

        Args:
            key: 配置键，支持点号分隔的嵌套路径，如 'llm.api_key'
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value

    def set(self, key: str, value: Any):
        """
        设置配置值

        Args:
            key: 配置键，支持点号分隔的嵌套路径
            value: 配置值
        """
        keys = key.split(".")
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def save(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.config,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
            logger.info(f"配置已保存: {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            raise

    def to_dict(self) -> Dict[str, Any]:
        """返回配置字典副本"""
        import copy

        return copy.deepcopy(self.config)

    def reload(self):
        """重新加载配置"""
        self.load()
        logger.info("配置已重新加载")

    # ========== 便捷方法 ==========

    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        return self.get("llm", {})

    def get_redis_config(self) -> Dict[str, Any]:
        """获取Redis配置"""
        return self.get("redis", {})

    def get_email_config(self) -> Dict[str, Any]:
        """获取邮件配置"""
        return self.get("email", {})

    def get_crawler_config(self) -> Dict[str, Any]:
        """获取爬虫配置"""
        return self.get("crawler", {})

    def get_scheduler_config(self) -> Dict[str, Any]:
        """获取定时任务配置"""
        return self.get("scheduler", {})

    def get_app_config(self) -> Dict[str, Any]:
        """获取应用配置"""
        return self.get("app", {})


# 全局配置实例
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """获取全局配置管理器实例"""
    return config_manager
