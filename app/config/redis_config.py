"""
Redis 配置模块

提供类型安全的 Redis 配置访问
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class RedisConfig:
    """
    Redis 数据库配置
    
    属性:
        host: Redis 服务器地址
        port: Redis 服务器端口
        password: Redis 密码（可选）
    """
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RedisConfig':
        """从字典创建配置"""
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
    
    def build_url(self) -> str:
        """
        构建 Redis URL
        
        返回:
            Redis URL 字符串，格式: redis://[:password@]host:port
        """
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}"
        else:
            return f"redis://{self.host}:{self.port}"


def get_redis_config() -> RedisConfig:
    """
    从 config_manager 加载 Redis 配置
    
    返回:
        RedisConfig 实例
    """
    from app.config.config_manager import config_manager
    
    redis_data = config_manager.get_config('redis')
    return RedisConfig.from_dict(redis_data)
