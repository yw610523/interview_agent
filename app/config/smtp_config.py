"""
SMTP 配置模块

提供类型安全的 SMTP 配置访问
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class SmtpConfig:
    """
    SMTP 邮件服务配置
    
    属性:
        server: SMTP 服务器地址
        port: SMTP 服务器端口
        user: SMTP 用户名（邮箱地址）
        password: SMTP 密码或授权码
        test_user: 测试接收邮箱
    """
    server: str = "smtp.qq.com"
    port: int = 465
    user: str = ""
    password: str = ""
    test_user: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SmtpConfig':
        """从字典创建配置"""
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


def get_smtp_config() -> SmtpConfig:
    """
    从 config_manager 加载 SMTP 配置
    
    返回:
        SmtpConfig 实例
    """
    from app.config.config_manager import config_manager
    
    smtp_data = config_manager.get_config('smtp')
    return SmtpConfig.from_dict(smtp_data)
