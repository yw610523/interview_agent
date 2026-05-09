"""
Prompts 配置模块

提供类型安全的提示词配置访问
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class PromptsConfig:
    """
    LLM 系统提示词配置
    
    属性:
        question_extraction_system: 问题提取系统提示词
        answer_generation_system: 答案生成系统提示词
    """
    question_extraction_system: str = ""
    answer_generation_system: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptsConfig':
        """从字典创建配置"""
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


def get_prompts_config() -> PromptsConfig:
    """
    从 config_manager 加载 Prompts 配置
    
    返回:
        PromptsConfig 实例
    """
    from app.config.config_manager import config_manager
    
    prompts_data = config_manager.get_config('prompts')
    return PromptsConfig.from_dict(prompts_data)
