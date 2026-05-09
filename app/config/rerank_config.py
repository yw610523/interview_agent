"""
Rerank 配置模块

提供类型安全的 Rerank 配置访问
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class RerankConfig:
    """
    重排序模型配置
    
    属性:
        enabled: 是否启用 Rerank
        api_url: Rerank API 地址
        api_key: Rerank API 密钥
        model: Rerank 模型名称
    """
    enabled: bool = False
    api_url: str = "https://cloud.siliconflow.cn/v1"
    api_key: str = ""
    model: str = "BAAI/bge-reranker-v2-m3"
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RerankConfig':
        """从字典创建配置"""
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


def get_rerank_config() -> RerankConfig:
    """
    从 config_manager 加载 Rerank 配置
    
    返回:
        RerankConfig 实例
    """
    from app.config.config_manager import config_manager
    
    rerank_data = config_manager.get_config('rerank')
    return RerankConfig.from_dict(rerank_data)
