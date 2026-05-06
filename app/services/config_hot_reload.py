"""
配置热加载管理器

支持在不重启服务的情况下动态重新加载配置
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv, find_dotenv
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)


class ConfigHotReloadManager:
    """
    配置热加载管理器
    
    负责在运行时重新加载配置并更新服务实例
    """
    
    def __init__(self):
        self.llm_service: Optional[LLMService] = None
        self.vector_service: Optional[VectorService] = None
    
    def set_services(self, llm_service: LLMService, vector_service: VectorService):
        """设置服务实例引用"""
        self.llm_service = llm_service
        self.vector_service = vector_service
    
    def reload_llm_config(self) -> bool:
        """
        热加载模型配置
        
        Returns:
            bool: 是否成功重新加载
        """
        try:
            logger.info("开始热加载模型配置...")
            
            # 重新加载环境变量
            dotenv_path = find_dotenv()
            if dotenv_path:
                load_dotenv(dotenv_path, override=True)
                logger.info(f"已重新加载环境变量文件: {dotenv_path}")
            
            # 重新初始化LLM服务
            if self.llm_service:
                self.llm_service._init_clients()
                logger.info("✅ LLM服务配置已更新")
                
                # 验证配置
                api_key = os.getenv("OPENAI_API_KEY", "")
                api_base = os.getenv("OPENAI_API_BASE", "")
                model = os.getenv("OPENAI_MODEL", "")
                
                logger.info(f"当前配置:")
                logger.info(f"  - API Base: {api_base or '默认'}")
                logger.info(f"  - Model: {model or '默认'}")
                logger.info(f"  - API Key: {'已配置' if api_key else '未配置'}")
                
                return True
            else:
                logger.warning("LLM服务实例未设置，无法热加载")
                return False
                
        except Exception as e:
            logger.error(f"热加载模型配置失败: {str(e)}")
            return False
    
    def reload_redis_config(self) -> bool:
        """
        热加载Redis配置
        
        Returns:
            bool: 是否成功重新加载
        """
        try:
            logger.info("开始热加载Redis配置...")
            
            # 重新加载环境变量
            dotenv_path = find_dotenv()
            if dotenv_path:
                load_dotenv(dotenv_path, override=True)
                logger.info(f"已重新加载环境变量文件: {dotenv_path}")
            
            # 重新初始化向量服务
            if self.vector_service:
                self.vector_service._init_clients()
                logger.info("✅ Redis/向量服务配置已更新")
                
                # 验证配置
                redis_url = os.getenv("REDIS_URL", "")
                logger.info(f"当前Redis URL: {redis_url}")
                
                # 检查连接状态
                if self.vector_service.redis_client:
                    try:
                        self.vector_service.redis_client.ping()
                        logger.info("✅ Redis连接正常")
                        return True
                    except Exception as e:
                        logger.warning(f"⚠️ Redis连接测试失败: {str(e)}")
                        return False
                else:
                    logger.warning("⚠️ Redis客户端未初始化")
                    return False
            else:
                logger.warning("向量服务实例未设置，无法热加载")
                return False
                
        except Exception as e:
            logger.error(f"热加载Redis配置失败: {str(e)}")
            return False
    
    def reload_email_config(self) -> bool:
        """
        热加载邮件配置
        
        Returns:
            bool: 是否成功重新加载
        """
        try:
            logger.info("开始热加载邮件配置...")
            
            # 重新加载环境变量
            dotenv_path = find_dotenv()
            if dotenv_path:
                load_dotenv(dotenv_path, override=True)
                logger.info(f"已重新加载环境变量文件: {dotenv_path}")
            
            # 验证配置
            smtp_server = os.getenv("SMTP_SERVER", "")
            smtp_port = os.getenv("SMTP_PORT", "")
            smtp_user = os.getenv("SMTP_USER", "")
            
            logger.info(f"当前邮件配置:")
            logger.info(f"  - SMTP服务器: {smtp_server or '未配置'}")
            logger.info(f"  - SMTP端口: {smtp_port or '未配置'}")
            logger.info(f"  - 用户名: {smtp_user or '未配置'}")
            
            if smtp_server and smtp_user:
                logger.info("✅ 邮件配置已更新")
                return True
            else:
                logger.warning("⚠️ 邮件配置不完整")
                return False
                
        except Exception as e:
            logger.error(f"热加载邮件配置失败: {str(e)}")
            return False
    
    def reload_scheduler_config(self, scheduler, new_hour: int, new_minute: int) -> bool:
        """
        热加载定时任务配置
        
        Args:
            scheduler: APScheduler实例
            new_hour: 新的小时
            new_minute: 新的分钟
            
        Returns:
            bool: 是否成功重新加载
        """
        try:
            logger.info(f"开始热加载定时任务配置: {new_hour}:{new_minute:02d}...")
            
            # 移除旧的定时任务
            jobs = scheduler.get_jobs()
            for job in jobs:
                if job.name == 'scheduled_crawl':
                    scheduler.remove_job(job.id)
                    logger.info(f"已移除旧定时任务: {job.id}")
            
            # 添加新的定时任务
            from apscheduler.triggers.cron import CronTrigger
            
            @scheduler.scheduled_job(CronTrigger(hour=new_hour, minute=new_minute), name='scheduled_crawl')
            def new_scheduled_crawl():
                """新的定时爬虫任务"""
                from app.main import run_crawler
                run_crawler()
            
            logger.info(f"✅ 定时任务已更新为每天 {new_hour}:{new_minute:02d} 执行")
            
            # 更新环境变量（供下次启动使用）
            dotenv_path = find_dotenv()
            if dotenv_path:
                from dotenv import set_key
                set_key(dotenv_path, 'SCHEDULER_HOUR', str(new_hour))
                set_key(dotenv_path, 'SCHEDULER_MINUTE', str(new_minute))
                logger.info("已保存定时配置到.env文件")
            
            return True
                
        except Exception as e:
            logger.error(f"热加载定时任务配置失败: {str(e)}")
            return False
    
    def reload_all_configs(self, scheduler=None) -> Dict[str, bool]:
        """
        热加载所有配置
        
        Args:
            scheduler: APScheduler实例（可选）
            
        Returns:
            Dict[str, bool]: 各配置项的加载结果
        """
        logger.info("=" * 60)
        logger.info("开始热加载所有配置...")
        logger.info("=" * 60)
        
        results = {
            "llm": self.reload_llm_config(),
            "redis": self.reload_redis_config(),
            "email": self.reload_email_config(),
        }
        
        # 统计结果
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        
        logger.info("=" * 60)
        logger.info(f"配置热加载完成: {success_count}/{total_count} 成功")
        logger.info("=" * 60)
        
        return results


# 全局配置热加载管理器实例
config_reload_manager = ConfigHotReloadManager()
