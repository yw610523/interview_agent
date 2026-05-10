"""
Firecrawl 配置模块

提供类型安全的 Firecrawl 配置访问
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class FirecrawlConfig:
    """
    Firecrawl MCP 服务配置
    
    属性:
        enabled: 是否启用 Firecrawl
        api_url: Firecrawl API 地址（必填）
        api_key: Firecrawl API 密钥（可选）
        timeout: 请求超时时间（秒）
        only_main_content: 是否只提取主要内容
    """
    enabled: bool = False
    api_url: str = "http://localhost:3002"
    api_key: Optional[str] = None
    timeout: int = 600
    only_main_content: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FirecrawlConfig':
        """从字典创建配置"""
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


def get_firecrawl_config() -> FirecrawlConfig:
    """
    从 config_manager 加载 Firecrawl 配置
    
    返回:
        FirecrawlConfig 实例
    """
    from app.config.config_manager import config_manager
    
    firecrawl_data = config_manager.get_config('firecrawl')
    return FirecrawlConfig.from_dict(firecrawl_data)
