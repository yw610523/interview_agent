"""
LLM 配置模块

提供类型安全的 LLM 配置访问，支持嵌套结构
"""
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional


@dataclass
class OpenAIConfig:
    """OpenAI LLM 配置"""
    api_key: str = ""
    api_base: str = ""
    model: str = "gpt-4o-mini"
    max_input_tokens: int = 128000
    max_output_tokens: int = 16384


@dataclass
class EmbeddingConfig:
    """Embedding 配置"""
    api_base: str = ""
    api_key: str = ""
    model: str = "BAAI/bge-m3"
    dimension: int = 1024


@dataclass
class RerankConfig:
    """Rerank 配置"""
    enabled: bool = False
    api_base: str = ""
    api_key: str = ""
    model: str = "BAAI/bge-reranker-v2-m3"


@dataclass
class LlmConfig:
    """
    大语言模型配置（包含 OpenAI、Embedding 和 Rerank）
    
    属性:
        openai: OpenAI LLM 配置
        embedding: Embedding 配置
        rerank: Rerank 配置
    """
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    rerank: RerankConfig = field(default_factory=RerankConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return {
            'openai': self.openai.__dict__,
            'embedding': self.embedding.__dict__,
            'rerank': self.rerank.__dict__
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LlmConfig':
        """从字典创建配置（支持嵌套结构和平铺结构）"""
        # 检查是否是嵌套结构
        if 'openai' in data or 'embedding' in data or 'rerank' in data:
            # 嵌套结构
            openai_data = data.get('openai', {})
            embedding_data = data.get('embedding', {})
            rerank_data = data.get('rerank', {})
            
            return cls(
                openai=OpenAIConfig(**{k: v for k, v in openai_data.items() if k in OpenAIConfig.__dataclass_fields__}),
                embedding=EmbeddingConfig(**{k: v for k, v in embedding_data.items() if k in EmbeddingConfig.__dataclass_fields__}),
                rerank=RerankConfig(**{k: v for k, v in rerank_data.items() if k in RerankConfig.__dataclass_fields__})
            )
        else:
            # 平铺结构（向后兼容）
            openai_fields = {k: v for k, v in data.items() if k in OpenAIConfig.__dataclass_fields__}
            embedding_fields = {k: v for k, v in data.items() if k in EmbeddingConfig.__dataclass_fields__}
            rerank_fields = {
                'enabled': data.get('rerank_enabled', False),
                'model': data.get('rerank_model_name', 'BAAI/bge-reranker-v2-m3')
            }
            # 添加其他 rerank 字段
            if 'rerank_api_base' in data:
                rerank_fields['api_base'] = data['rerank_api_base']
            if 'rerank_api_key' in data:
                rerank_fields['api_key'] = data['rerank_api_key']
            
            return cls(
                openai=OpenAIConfig(**openai_fields),
                embedding=EmbeddingConfig(**embedding_fields),
                rerank=RerankConfig(**{k: v for k, v in rerank_fields.items() if k in RerankConfig.__dataclass_fields__})
            )


def get_llm_config() -> LlmConfig:
    """
    从 config_manager 加载 LLM 配置
    
    返回:
        LlmConfig 实例
    """
    from app.config.config_manager import config_manager
    
    llm_data = config_manager.get_config('llm')
    return LlmConfig.from_dict(llm_data)
