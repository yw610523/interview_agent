"""
爬虫任务管理器模块

提供异步爬虫任务的执行、状态跟踪和终止功能
"""

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class CrawlTask:
    """爬虫任务数据类"""
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    progress: int = 0  # 进度百分比 (0-100)
    total_urls: int = 0
    processed_urls: int = 0
    parsed_questions: int = 0
    inserted_questions: int = 0
    error_message: Optional[str] = None
    stop_flag: threading.Event = field(default_factory=threading.Event)
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "progress": self.progress,
            "total_urls": self.total_urls,
            "processed_urls": self.processed_urls,
            "parsed_questions": self.parsed_questions,
            "inserted_questions": self.inserted_questions,
            "error_message": self.error_message,
        }


class CrawlTaskManager:
    """
    爬虫任务管理器

    负责管理异步爬虫任务的生命周期，包括启动、监控和终止
    """

    def __init__(self):
        self.tasks: Dict[str, CrawlTask] = {}
        self._lock = threading.Lock()

    def create_task(self, task_id: str) -> CrawlTask:
        """创建新的爬虫任务"""
        with self._lock:
            task = CrawlTask(task_id=task_id)
            self.tasks[task_id] = task
            logger.info(f"创建爬虫任务: {task_id}")
            return task

    def get_task(self, task_id: str) -> Optional[CrawlTask]:
        """获取任务信息"""
        with self._lock:
            return self.tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus, **kwargs):
        """更新任务状态"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.status = status
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)

    def stop_task(self, task_id: str) -> bool:
        """停止指定任务"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.RUNNING:
                task.stop_flag.set()
                logger.info(f"请求停止任务: {task_id}")
                return True
            return False

    def remove_task(self, task_id: str):
        """移除已完成的任务"""
        with self._lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                logger.info(f"移除任务: {task_id}")

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """获取所有任务的状态"""
        with self._lock:
            return {
                task_id: task.to_dict()
                for task_id, task in self.tasks.items()
            }


# 全局任务管理器实例
crawl_task_manager = CrawlTaskManager()
