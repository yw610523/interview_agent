"""
Service 配置模块

提供类型安全的服务端口配置访问
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class ServiceConfig:
    """
    服务端口配置
    
    属性:
        app_port: 应用服务端口
    """
    app_port: int = 9023
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceConfig':
        """从字典创建配置"""
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


def get_service_config() -> ServiceConfig:
    """
    从 config_manager 加载 Service 配置
    
    返回:
        ServiceConfig 实例
    """
    from app.config.config_manager import config_manager
    
    service_data = config_manager.get_config('service')
    return ServiceConfig.from_dict(service_data)
