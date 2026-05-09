"""
Content 配置模块

提供类型安全的内容处理配置访问
"""
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List


@dataclass
class ContentConfig:
    """
    内容处理配置
    
    属性:
        max_content_length_per_page: 每页最大内容长度（字符数）
        chunk_size: 块大小（字符数）
        chunk_overlap: 重叠长度（字符数）
        separators: 分隔符策略列表
        chunking_mode: 切分模式（semantic/markdown/fixed）
        max_chunks_per_page: 最大 Chunk 数量
        min_chunk_length: 最小 Chunk 长度（字符数）
    """
    max_content_length_per_page: int = 2000
    chunk_size: int = 512
    chunk_overlap: int = 128
    separators: List[str] = field(default_factory=lambda: ['\n\n', '\n', '。', '！', '？', '.', '!', '?', ' '])
    chunking_mode: str = "semantic"
    max_chunks_per_page: int = 100
    min_chunk_length: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentConfig':
        """从字典创建配置"""
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


def get_content_config() -> ContentConfig:
    """
    从 config_manager 加载 Content 配置
    
    返回:
        ContentConfig 实例
    """
    from app.config.config_manager import config_manager
    
    content_data = config_manager.get_config('content')
    return ContentConfig.from_dict(content_data)
