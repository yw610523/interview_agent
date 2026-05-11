"""
配置热加载管理器

支持在不重启服务的情况下动态重新加载配置
"""

import logging
import os
from typing import Dict, Optional

import yaml
from pathlib import Path

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

            # 从 config.yaml 重新加载配置
            from app.config.config_manager import config_manager
            config_manager.reload()

            # 重新初始化LLM服务
            if self.llm_service:
                self.llm_service._init_clients()
                logger.info("✅ LLM服务配置已更新")

                # 验证配置
                llm_config = config_manager.get_config('llm')
                openai_config = llm_config.get('openai', {})
                api_key = openai_config.get('api_key', '')
                api_base = openai_config.get('api_base', '')
                model = openai_config.get('model', '')

                logger.info("当前配置:")
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
    
            # 从 config.yaml 重新加载配置
            from app.config.config_manager import config_manager
            config_manager.reload()
    
            # 重新初始化向量服务
            if self.vector_service:
                self.vector_service._init_clients()
                logger.info("✅ Redis/向量服务配置已更新")
    
                # 验证配置
                redis_config = config_manager.get_config('redis')
                redis_url = config_manager.get_redis_url()
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

            # 从 config.yaml 重新加载配置
            from app.config.config_manager import config_manager
            config_manager.reload()

            # 验证配置
            smtp_config = config_manager.get_config('smtp')
            smtp_server = smtp_config.get('server', '')
            smtp_port = smtp_config.get('port', '')
            smtp_user = smtp_config.get('user', '')

            logger.info("当前邮件配置:")
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

    def reload_crawler_config(self) -> bool:
        """
        热加载爬虫配置

        Returns:
            bool: 是否成功重新加载
        """
        try:
            logger.info("开始热加载爬虫配置...")

            # 从 config.yaml 重新加载配置
            from app.config.config_manager import config_manager
            config_manager.reload()

            # 验证配置
            crawler_config = config_manager.get_config('crawler')
            sitemap_url = crawler_config.get('sitemap_url', '')
            timeout = crawler_config.get('timeout', '')

            logger.info("当前爬虫配置:")
            logger.info(f"  - Sitemap URL: {sitemap_url or '未配置'}")
            logger.info(f"  - 超时时间: {timeout or '默认'}")

            if sitemap_url:
                logger.info("✅ 爬虫配置已更新")
                return True
            else:
                logger.warning("⚠️ 爬虫配置不完整")
                return False

        except Exception as e:
            logger.error(f"热加载爬虫配置失败: {str(e)}")
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

            # 更新定时任务的触发时间（不重新定义函数）
            from apscheduler.triggers.cron import CronTrigger
            
            jobs = scheduler.get_jobs()
            updated = False
            for job in jobs:
                if job.name == 'scheduled_crawl':
                    # 只修改触发器，保留原有的任务函数
                    job.modify(trigger=CronTrigger(hour=new_hour, minute=new_minute))
                    logger.info(f"已更新定时任务触发时间: {new_hour}:{new_minute:02d}")
                    updated = True
                    break
            
            if not updated:
                logger.warning("未找到名为 'scheduled_crawl' 的定时任务")

            logger.info(f"✅ 定时任务已更新为每天 {new_hour}:{new_minute:02d} 执行")

            # 更新配置文件（供下次启动使用）
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # 确保 crawler.scheduler 存在
                if 'crawler' not in config:
                    config['crawler'] = {}
                if 'scheduler' not in config['crawler']:
                    config['crawler']['scheduler'] = {}
                
                config['crawler']['scheduler']['hour'] = new_hour
                config['crawler']['scheduler']['minute'] = new_minute
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                
                logger.info("已保存定时配置到config.yaml文件")

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
