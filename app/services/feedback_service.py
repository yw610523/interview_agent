# app/services/feedback_service.py
"""
用户反馈服务模块

提供面试题的反馈机制，包括：
1. 掌握程度评分
2. 收藏/错题本管理
3. 基于艾宾浩斯遗忘曲线的权重计算
4. 智能推荐算法
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from dotenv import load_dotenv

# 尝试导入 Redis
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)
load_dotenv()


@dataclass
class QuestionFeedback:
    """题目反馈数据"""
    question_id: str
    user_id: str = "default"  # 当前简化为单用户
    mastery_level: int = 0  # 掌握程度 0-5 (0=未学习, 5=完全掌握)
    last_reviewed_at: Optional[str] = None  # 最后复习时间 ISO格式
    review_count: int = 0  # 复习次数
    next_review_at: Optional[str] = None  # 下次复习时间 ISO格式
    is_favorite: bool = False  # 是否收藏
    is_wrong_book: bool = False  # 是否在错题本
    created_at: Optional[str] = None  # 创建时间
    updated_at: Optional[str] = None  # 更新时间


class FeedbackService:
    """用户反馈服务类"""

    def __init__(self):
        self.redis_client = None
        self.openai_client = None
        self.rerank_enabled = False
        self.rerank_model = "rerank-sf"
        self._init_redis()
        self._init_rerank()

    def _init_redis(self):
        """初始化 Redis 客户端"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()
            logger.info("FeedbackService: Redis 客户端初始化成功")
        except Exception as e:
            logger.error(f"FeedbackService: Redis 客户端初始化失败: {str(e)}")

    def _init_rerank(self):
        """初始化 Rerank 客户端（复用 LLM 的配置）"""
        try:
            from openai import OpenAI

            # 读取 Rerank 配置
            self.rerank_enabled = os.getenv("RERANK_ENABLED", "false").lower() == "true"
            self.rerank_model = os.getenv("RERANK_MODEL", "rerank-sf")

            if not self.rerank_enabled:
                logger.info("FeedbackService: Rerank 未启用")
                return

            # 获取 Rerank API 配置，如果为空则复用 OpenAI 配置
            rerank_api_key = os.getenv("RERANK_API_KEY", "").strip()
            rerank_api_base = os.getenv("RERANK_API_URL", "").strip()

            # 如果 Rerank 配置为空，复用 OpenAI 配置
            if not rerank_api_key:
                rerank_api_key = os.getenv("OPENAI_API_KEY")
                logger.info("FeedbackService: Rerank API Key 未配置，复用 OPENAI_API_KEY")

            if not rerank_api_base:
                # 如果 Rerank API URL 未配置，复用 OPENAI_API_BASE
                rerank_api_base = os.getenv("OPENAI_API_BASE")
                logger.info("FeedbackService: Rerank API URL 未配置，复用 OPENAI_API_BASE")

            # 初始化客户端
            if rerank_api_key:
                if rerank_api_base:
                    self.openai_client = OpenAI(api_key=rerank_api_key, base_url=rerank_api_base)
                else:
                    self.openai_client = OpenAI(api_key=rerank_api_key)
                logger.info(
                    f"FeedbackService: Rerank 客户端初始化成功 (model={self.rerank_model})"
                )
            else:
                logger.warning("FeedbackService: Rerank 已启用但 API Key 未配置")

        except Exception as e:
            logger.error(f"FeedbackService: Rerank 客户端初始化失败: {str(e)}")

    def reload_rerank_config(self):
        """重新加载 Rerank 配置（热更新）"""
        logger.info("重新加载 Rerank 配置...")
        self._init_rerank()

    def _get_feedback_key(self, question_id: str, user_id: str = "default") -> str:
        """生成反馈数据的 Redis key"""
        return f"feedback:{user_id}:{question_id}"

    def submit_feedback(self, question_id: str, feedback_data: Dict[str, Any]) -> bool:
        """
        提交题目反馈

        参数:
            question_id: 题目ID
            feedback_data: 反馈数据字典，包含:
                - mastery_level: 掌握程度 (0-5)
                - is_favorite: 是否收藏
                - is_wrong_book: 是否加入错题本

        返回:
            是否成功
        """
        if not self.redis_client:
            logger.error("Redis 客户端未初始化")
            return False

        try:
            key = self._get_feedback_key(question_id)
            now = datetime.now().isoformat()

            # 获取现有反馈
            existing = self.get_feedback(question_id)

            if existing:
                # 更新现有反馈
                feedback = existing

                # 记录是否发生了实质性的学习行为
                should_increment_review = False

                if 'mastery_level' in feedback_data:
                    old_mastery = feedback.mastery_level
                    new_mastery = feedback_data['mastery_level']

                    logger.info(f"评分变化检查: question_id={question_id}, old={old_mastery}, new={new_mastery}")

                    feedback.mastery_level = new_mastery

                    # 只有在以下情况才增加复习次数：
                    # - 掌握程度实质性提升（增加 >= 2 级）
                    # 不包括：
                    # - 微调评分（如 1→2 或 2→1，变化幅度太小）
                    # - 从 0 变为非0（首次评分）
                    # - 从非0变为 0（取消评分）
                    # - 相同评分重复提交
                    mastery_diff = new_mastery - old_mastery
                    if mastery_diff >= 2:
                        # 实质性提升，视为重新学习
                        should_increment_review = True
                        logger.info(f"实质性提升: {old_mastery} -> {new_mastery} (+{mastery_diff})")
                    elif mastery_diff == 1:
                        logger.info(f"微调评分: {old_mastery} -> {new_mastery} (+1)，不增加复习次数")
                    elif mastery_diff < 0:
                        logger.info(f"评分下降: {old_mastery} -> {new_mastery} ({mastery_diff})，不增加复习次数")
                    else:
                        logger.info(f"评分未变化: {old_mastery} == {new_mastery}，不增加复习次数")

                if 'is_favorite' in feedback_data:
                    feedback.is_favorite = feedback_data['is_favorite']
                if 'is_wrong_book' in feedback_data:
                    feedback.is_wrong_book = feedback_data['is_wrong_book']

                # 如果需要增加复习次数，更新复习信息
                if should_increment_review:
                    feedback.last_reviewed_at = now
                    feedback.review_count += 1
                    # 计算下次复习时间（基于艾宾浩斯曲线）
                    feedback.next_review_at = self._calculate_next_review(
                        feedback.mastery_level,
                        feedback.review_count
                    ).isoformat()
                    logger.info(f"复习次数增加: question_id={question_id}, count={feedback.review_count}")
                else:
                    logger.info(f"复习次数不变: question_id={question_id}, count={feedback.review_count}")

                feedback.updated_at = now
            else:
                # 创建新反馈
                feedback = QuestionFeedback(
                    question_id=question_id,
                    mastery_level=feedback_data.get('mastery_level', 0),
                    is_favorite=feedback_data.get('is_favorite', False),
                    is_wrong_book=feedback_data.get('is_wrong_book', False),
                    created_at=now,
                    updated_at=now
                )

                # 如果提交了掌握程度，设置复习信息
                if 'mastery_level' in feedback_data:
                    feedback.last_reviewed_at = now
                    feedback.review_count = 1
                    feedback.next_review_at = self._calculate_next_review(
                        feedback.mastery_level,
                        feedback.review_count
                    ).isoformat()

            # 存储到 Redis
            self.redis_client.hset(key, mapping={
                'question_id': feedback.question_id,
                'user_id': feedback.user_id,
                'mastery_level': str(feedback.mastery_level),
                'last_reviewed_at': feedback.last_reviewed_at or '',
                'review_count': str(feedback.review_count),
                'next_review_at': feedback.next_review_at or '',
                'is_favorite': str(feedback.is_favorite),
                'is_wrong_book': str(feedback.is_wrong_book),
                'created_at': feedback.created_at or '',
                'updated_at': feedback.updated_at or ''
            })

            logger.info(f"提交反馈成功: question_id={question_id}, mastery={feedback.mastery_level}")
            return True

        except Exception as e:
            logger.error(f"提交反馈失败: {str(e)}")
            return False

    def get_feedback(self, question_id: str, user_id: str = "default") -> Optional[QuestionFeedback]:
        """
        获取题目反馈

        参数:
            question_id: 题目ID
            user_id: 用户ID

        返回:
            反馈对象，不存在则返回 None
        """
        if not self.redis_client:
            return None

        try:
            key = self._get_feedback_key(question_id, user_id)
            data = self.redis_client.hgetall(key)

            if not data:
                return None

            return QuestionFeedback(
                question_id=data.get(b'question_id', b'').decode(),
                user_id=data.get(b'user_id', b'default').decode(),
                mastery_level=int(data.get(b'mastery_level', b'0')),
                last_reviewed_at=data.get(b'last_reviewed_at', b'').decode() or None,
                review_count=int(data.get(b'review_count', b'0')),
                next_review_at=data.get(b'next_review_at', b'').decode() or None,
                is_favorite=data.get(b'is_favorite', b'False').decode() == 'True',
                is_wrong_book=data.get(b'is_wrong_book', b'False').decode() == 'True',
                created_at=data.get(b'created_at', b'').decode() or None,
                updated_at=data.get(b'updated_at', b'').decode() or None
            )

        except Exception as e:
            logger.error(f"获取反馈失败: {str(e)}")
            return None

    def get_favorites(self, user_id: str = "default") -> List[str]:
        """
        获取收藏的题目ID列表

        返回:
            收藏的题目ID列表
        """
        if not self.redis_client:
            return []

        try:
            pattern = f"feedback:{user_id}:*"
            keys = self.redis_client.keys(pattern)
            favorites = []

            for key in keys:
                data = self.redis_client.hgetall(key)
                if data.get(b'is_favorite', b'False').decode() == 'True':
                    question_id = data.get(b'question_id', b'').decode()
                    if question_id:
                        favorites.append(question_id)

            return favorites

        except Exception as e:
            logger.error(f"获取收藏列表失败: {str(e)}")
            return []

    def get_wrong_book(self, user_id: str = "default") -> List[str]:
        """
        获取错题本中的题目ID列表

        返回:
            错题本中的题目ID列表
        """
        if not self.redis_client:
            return []

        try:
            pattern = f"feedback:{user_id}:*"
            keys = self.redis_client.keys(pattern)
            wrong_books = []

            for key in keys:
                data = self.redis_client.hgetall(key)
                if data.get(b'is_wrong_book', b'False').decode() == 'True':
                    question_id = data.get(b'question_id', b'').decode()
                    if question_id:
                        wrong_books.append(question_id)

            return wrong_books

        except Exception as e:
            logger.error(f"获取错题本失败: {str(e)}")
            return []

    def remove_from_collection(self, question_id: str, collection_type: str, user_id: str = "default") -> bool:
        """
        从收藏或错题本中移除题目

        参数:
            question_id: 题目ID
            collection_type: 类型 ('favorite' 或 'wrong_book')
            user_id: 用户ID

        返回:
            是否成功
        """
        if collection_type not in ['favorite', 'wrong_book']:
            logger.error(f"无效的集合类型: {collection_type}")
            return False

        feedback_data = {}
        if collection_type == 'favorite':
            feedback_data['is_favorite'] = False
        else:
            feedback_data['is_wrong_book'] = False

        return self.submit_feedback(question_id, feedback_data)

    def calculate_priority_score(self, question: Dict[str, Any], feedback: Optional[QuestionFeedback] = None) -> float:
        """
        计算题目的优先级分数（用于智能推荐）

        算法:
        priority = importance_score * (1 - mastery_level/5) * time_decay_factor

        参数:
            question: 题目数据
            feedback: 用户反馈（可选）

        返回:
            优先级分数 (0-1)，越高越应该优先展示
        """
        importance_score = question.get('importance_score', 0.5)

        if not feedback:
            # 没有反馈记录，使用原始重要性分数
            return importance_score

        # 掌握程度因子：未掌握的题目优先级更高
        mastery_factor = 1.0 - (feedback.mastery_level / 5.0)

        # 时间衰减因子（基于艾宾浩斯遗忘曲线）
        time_decay_factor = self._calculate_time_decay(feedback)

        # 最终优先级分数
        priority = importance_score * mastery_factor * time_decay_factor

        return max(0.0, min(1.0, priority))  # 限制在 0-1 范围

    def rerank_questions(
        self,
        user_profile: str,
        questions: List[Dict[str, Any]],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        使用 Rerank 模型对题目进行重排序

        参数:
            user_profile: 用户画像/查询文本（例如："我需要复习 Python 异步编程相关的题目"）
            questions: 候选题目列表
            top_k: 返回的题目数量

        返回:
            重排序后的题目列表
        """
        if not self.rerank_enabled or not self.openai_client or not questions:
            logger.warning("Rerank 未启用或客户端未初始化，跳过重排序")
            return questions[:top_k]

        try:
            # 构建文档列表（题目标题 + 答案前100字）
            documents = []
            for q in questions:
                doc_text = f"{q['title']}\n{q.get('answer', '')[:100]}"
                documents.append(doc_text)

            # 调用 Rerank API - 使用标准的 /v1/rerank endpoint
            import requests

            # 获取 base_url 并构造 rerank endpoint
            base_url = str(self.openai_client.base_url).rstrip('/')
            rerank_url = f"{base_url}/rerank"

            headers = {
                "Authorization": f"Bearer {self.openai_client.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.rerank_model,
                "query": user_profile,
                "documents": documents,
                "top_n": len(documents)
            }

            response = requests.post(rerank_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            # 解析 Rerank 结果
            if 'results' in result and result['results']:
                scored_questions = []
                for item in result['results']:
                    index = item.get('index')
                    score = item.get('relevance_score', 0.0)

                    if index is not None and index < len(questions):
                        scored_questions.append({
                            **questions[index],
                            'rerank_score': float(score)
                        })

                # 按 Rerank 分数降序排序
                if scored_questions:
                    scored_questions.sort(key=lambda x: x['rerank_score'], reverse=True)
                    logger.info(f"Rerank 完成: {len(scored_questions)} 个题目已重排序")
                    return scored_questions[:top_k]
                else:
                    logger.warning("Rerank 未返回有效分数，降级为规则排序")
                    return questions[:top_k]
            else:
                logger.warning(f"Rerank API 返回格式异常: {result}，降级为规则排序")
                return questions[:top_k]

        except Exception as e:
            logger.error(f"Rerank 失败: {str(e)}，降级为规则排序")
            return questions[:top_k]

    def _calculate_next_review(self, mastery_level: int, review_count: int) -> datetime:
        """
        基于艾宾浩斯遗忘曲线计算下次复习时间

        间隔规律: 1天, 2天, 4天, 7天, 15天, 30天（最多30天）
        掌握程度越高，间隔越长

        参数:
            mastery_level: 掌握程度 (0-5)
            review_count: 复习次数

        返回:
            下次复习时间
        """
        # 基础间隔（天数）- 缩短间隔，更频繁的复习
        base_intervals = [1, 2, 4, 7, 15, 30]

        # 根据复习次数选择基础间隔
        interval_index = min(review_count - 1, len(base_intervals) - 1)
        base_interval = base_intervals[interval_index]

        # 根据掌握程度调整间隔（但最多不超过30天）
        mastery_multiplier = 1.0 + (mastery_level * 0.2)  # 每级增加20%间隔

        final_interval = int(base_interval * mastery_multiplier)

        # 限制最大间隔为30天
        final_interval = min(final_interval, 30)

        return datetime.now() + timedelta(days=final_interval)

    def _calculate_time_decay(self, feedback: QuestionFeedback) -> float:
        """
        计算时间衰减因子

        基于距离上次复习的时间，越久未复习，衰减越小（优先级越高）

        参数:
            feedback: 用户反馈

        返回:
            时间衰减因子 (0.3-1.0)
        """
        if not feedback.last_reviewed_at:
            return 1.0  # 从未复习，最高优先级

        try:
            last_reviewed = datetime.fromisoformat(feedback.last_reviewed_at)
            days_since_review = (datetime.now() - last_reviewed).days

            # 艾宾浩斯遗忘曲线近似
            if days_since_review <= 1:
                return 1.0
            elif days_since_review <= 3:
                return 0.9
            elif days_since_review <= 7:
                return 0.7
            elif days_since_review <= 15:
                return 0.5
            elif days_since_review <= 30:
                return 0.4
            else:
                return 0.3  # 超过30天未复习，需要重新学习

        except Exception as e:
            logger.error(f"计算时间衰减失败: {str(e)}")
            return 1.0

    def update_all_weights(self) -> int:
        """
        定时任务：更新所有题目的权重

        每天执行一次，根据艾宾浩斯曲线更新 next_review_at

        返回:
            更新的题目数量
        """
        if not self.redis_client:
            return 0

        try:
            pattern = "feedback:*"
            keys = self.redis_client.keys(pattern)
            updated_count = 0

            for key in keys:
                data = self.redis_client.hgetall(key)
                if not data:
                    continue

                question_id = data.get(b'question_id', b'').decode()
                mastery_level = int(data.get(b'mastery_level', b'0'))
                review_count = int(data.get(b'review_count', b'0'))

                if not question_id:
                    continue

                # 重新计算下次复习时间
                next_review = self._calculate_next_review(mastery_level, review_count)

                # 更新 Redis
                self.redis_client.hset(key, 'next_review_at', next_review.isoformat())
                updated_count += 1

            logger.info(f"权重更新完成: 更新了 {updated_count} 个题目")
            return updated_count

        except Exception as e:
            logger.error(f"更新权重失败: {str(e)}")
            return 0

    def get_due_questions(self, user_id: str = "default") -> List[str]:
        """
        获取到期需要复习的题目ID列表

        参数:
            user_id: 用户ID

        返回:
            到期题目ID列表
        """
        if not self.redis_client:
            return []

        try:
            pattern = f"feedback:{user_id}:*"
            keys = self.redis_client.keys(pattern)
            due_questions = []
            now = datetime.now()

            for key in keys:
                data = self.redis_client.hgetall(key)
                next_review_str = data.get(b'next_review_at', b'').decode()

                if not next_review_str:
                    continue

                try:
                    next_review = datetime.fromisoformat(next_review_str)
                    if next_review <= now:
                        question_id = data.get(b'question_id', b'').decode()
                        if question_id:
                            due_questions.append(question_id)
                except ValueError:
                    continue

            return due_questions

        except Exception as e:
            logger.error(f"获取到期题目失败: {str(e)}")
            return []

# Trigger reload
