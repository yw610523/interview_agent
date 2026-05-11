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

# 尝试导入 Redis
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class QuestionFeedback:
    """题目反馈数据"""
    question_id: str
    user_id: str = "default"  # 当前简化为单用户
    mastery_level: int = 0  # 掌握程度 0-5 (0=未学习, 5=完全掌握)
    is_favorite: bool = False  # 是否收藏
    is_wrong_book: bool = False  # 是否在错题本
    hide_from_recommendation: bool = False  # 是否从推荐中隐藏（软删除）
    hidden_at: Optional[str] = None  # 隐藏时间（用于30天后自动恢复）
    last_reviewed_at: Optional[str] = None  # 上次复习时间
    created_at: Optional[str] = None  # 创建时间
    updated_at: Optional[str] = None  # 更新时间


class FeedbackService:
    """用户反馈服务类"""

    def __init__(self):
        self.redis_client = None
        self.openai_client = None
        self.rerank_enabled = False
        self.rerank_model = "BAAI/bge-reranker-v2-m3"
        self.rerank_api_base = ""  # 保存 Rerank API base URL
        self._init_redis()
        self._init_rerank()

    def _init_redis(self):
        """初始化 Redis 客户端"""
        try:
            from app.config.config_manager import config_manager
            
            # 从 config.yaml 读取 Redis 配置并构建 URL
            redis_url = config_manager.get_redis_url()
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()
            logger.info(f"FeedbackService: Redis 客户端初始化成功 ({redis_url})")
        except Exception as e:
            logger.error(f"FeedbackService: Redis 客户端初始化失败: {str(e)}")

    def _init_rerank(self):
        """初始化 Rerank 客户端（使用独立的配置）"""
        try:
            from openai import OpenAI
            
            # 导入统一配置管理器
            from app.config.config_manager import config_manager

            # 读取 LLM 配置（包含 rerank 嵌套结构）
            llm_config = config_manager.get_config('llm')
            
            # 支持嵌套结构和平铺结构
            if 'rerank' in llm_config:
                # 嵌套结构
                rerank_cfg = llm_config.get('rerank', {})
                self.rerank_enabled = rerank_cfg.get('enabled', False)
                self.rerank_model = rerank_cfg.get('model', 'BAAI/bge-reranker-v2-m3')
                rerank_api_key = rerank_cfg.get('api_key', '')
                rerank_api_base = rerank_cfg.get('api_base', '')
            else:
                # 平铺结构（向后兼容）
                rerank_enabled = llm_config.get('rerank_enabled', False)
                if isinstance(rerank_enabled, str):
                    rerank_enabled = rerank_enabled.lower() in ('true', '1', 'yes')
                self.rerank_enabled = rerank_enabled
                self.rerank_model = llm_config.get('rerank_model_name', 'BAAI/bge-reranker-v2-m3')
                rerank_api_key = llm_config.get('rerank_api_key', '')
                rerank_api_base = llm_config.get('rerank_api_base', '')

            if not self.rerank_enabled:
                logger.info("FeedbackService: Rerank 未启用")
                return

            # 如果 Rerank API Key 为空，尝试从环境变量获取
            if not rerank_api_key:
                rerank_api_key = os.getenv("RERANK_API_KEY", "").strip()

            # 如果 Rerank API Base 为空，尝试从环境变量获取
            if not rerank_api_base:
                rerank_api_base = os.getenv("RERANK_API_BASE", "https://siliconflow.cn/v1").strip()

            # 保存 rerank_api_base 供后续使用
            self.rerank_api_base = rerank_api_base

            # 初始化客户端
            if rerank_api_key:
                if rerank_api_base:
                    self.openai_client = OpenAI(api_key=rerank_api_key, base_url=rerank_api_base)
                else:
                    self.openai_client = OpenAI(api_key=rerank_api_key)
                logger.info(
                    f"FeedbackService: Rerank 客户端初始化成功 (model={self.rerank_model}, base_url={rerank_api_base})"
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

    def should_auto_hide(self, mastery_level: int, importance_score: float) -> dict:
        """
        根据掌握程度和重要性判断是否应该自动软删除
        
        规则:
        - level = int(importance_score / 0.2)  # 0.2 = 1/5，将0-1映射到0-5
        - mastery_level >= level: 弹窗询问（让用户决定是否隐藏）
        - mastery_level < level: 继续规划出现时间
        
        参数:
            mastery_level: 掌握程度 (0-5)
            importance_score: 题目重要性 (0-1)，从题目数据中获取
            
        返回:
            {
                'should_hide': bool,  # 是否应该隐藏
                'need_confirm': bool  # 是否需要用户确认
            }
        """
        # 计算对应的级别阈值
        level_threshold = int(importance_score / 0.2) if importance_score >= 0.2 else 0
        
        if mastery_level >= level_threshold and mastery_level > 0:
            # 达到或超过阈值时弹窗询问（但至少要有1级掌握）
            return {'should_hide': True, 'need_confirm': True}
        else:
            # 低于阈值时不处理
            return {'should_hide': False, 'need_confirm': False}

    def calculate_next_appearance_days(self, mastery_level: int, importance_score: float) -> int:
        """
        计算下次出现的间隔天数
        
        基于重要性和掌握程度的动态算法:
        - 重要性越高，出现频率越高（间隔越短）
        - 掌握程度越高，出现频率越低（间隔越长）
        
        公式: days = max(1, int((1 - importance_score) * 30 + mastery_level * 7))
        
        参数:
            mastery_level: 掌握程度 (0-5)
            importance_score: 重要性 (0-1)
            
        返回:
            间隔天数 (至少1天)
        """
        # 基础间隔：重要性越低，间隔越长
        base_days = (1 - importance_score) * 30
        
        # 掌握程度调整：掌握越好，间隔越长
        mastery_adjustment = mastery_level * 7
        
        # 总间隔
        total_days = int(base_days + mastery_adjustment)
        
        # 至少1天，最多90天
        return max(1, min(90, total_days))

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

                if 'mastery_level' in feedback_data:
                    old_mastery = feedback.mastery_level
                    new_mastery = feedback_data['mastery_level']
                    logger.info(f"评分变化: question_id={question_id}, old={old_mastery}, new={new_mastery}")
                    feedback.mastery_level = new_mastery

                if 'is_favorite' in feedback_data:
                    feedback.is_favorite = feedback_data['is_favorite']
                if 'is_wrong_book' in feedback_data:
                    feedback.is_wrong_book = feedback_data['is_wrong_book']
                if 'hide_from_recommendation' in feedback_data:
                    feedback.hide_from_recommendation = feedback_data['hide_from_recommendation']
                    if feedback.hide_from_recommendation and not feedback.hidden_at:
                        feedback.hidden_at = now

                feedback.updated_at = now
            else:
                # 创建新反馈
                feedback = QuestionFeedback(
                    question_id=question_id,
                    mastery_level=feedback_data.get('mastery_level', 0),
                    is_favorite=feedback_data.get('is_favorite', False),
                    is_wrong_book=feedback_data.get('is_wrong_book', False),
                    hide_from_recommendation=feedback_data.get('hide_from_recommendation', False),
                    created_at=now,
                    updated_at=now
                )
                
                # 如果创建时就标记隐藏，设置隐藏时间
                if feedback.hide_from_recommendation:
                    feedback.hidden_at = now

            # 存储到 Redis
            self.redis_client.hset(key, mapping={
                'question_id': feedback.question_id,
                'user_id': feedback.user_id,
                'mastery_level': str(feedback.mastery_level),
                'is_favorite': str(feedback.is_favorite),
                'is_wrong_book': str(feedback.is_wrong_book),
                'hide_from_recommendation': str(feedback.hide_from_recommendation),
                'hidden_at': feedback.hidden_at or '',
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
                is_favorite=data.get(b'is_favorite', b'False').decode() == 'True',
                is_wrong_book=data.get(b'is_wrong_book', b'False').decode() == 'True',
                hide_from_recommendation=data.get(b'hide_from_recommendation', b'False').decode() == 'True',
                hidden_at=data.get(b'hidden_at', b'').decode() or None,
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

            # 使用独立的 Rerank API base URL（不与 OpenAI 耦合）
            rerank_url = f"{self.rerank_api_base.rstrip('/')}/rerank"

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
            
            # 检查 HTTP 状态码
            if response.status_code != 200:
                logger.error(f"Rerank API 返回错误状态码: {response.status_code}, 响应: {response.text[:200]}")
                return questions[:top_k]
            
            # 检查响应内容是否为空
            if not response.text or not response.text.strip():
                logger.error(f"Rerank API 返回空响应, URL: {rerank_url}")
                return questions[:top_k]
            
            # 尝试解析 JSON
            try:
                result = response.json()
            except Exception as json_err:
                logger.error(f"Rerank API 响应解析失败: {str(json_err)}, 响应内容: {response.text[:200]}")
                return questions[:top_k]

            # 解析 Rerank 结果
            if 'results' in result and result['results']:
                scored_questions = []
                for item in result['results']:
                    index = item.get('index')
                    score = item.get('relevance_score', 0.0)

                    if index is not None and index < len(questions):
                        question = questions[index]
                        
                        # 检查是否应该从推荐中排除（隐藏的题目）
                        feedback = self.get_feedback(question.get('id', ''))
                        if feedback and self.should_exclude_from_recommendation(question.get('id', '')):
                            # 隐藏的题目分数大幅降低，排在最后
                            score = score * 0.1  # 降低到原来的10%
                        
                        scored_questions.append({
                            **question,
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

    def check_and_restore_hidden_questions(self, user_id: str = "default") -> int:
        """
        检查并恢复过期的隐藏题目（30天后自动恢复）
        
        参数:
            user_id: 用户ID
            
        返回:
            恢复的题目数量
        """
        if not self.redis_client:
            return 0
        
        try:
            pattern = f"feedback:{user_id}:*"
            keys = self.redis_client.keys(pattern)
            restored_count = 0
            now = datetime.now()
            
            for key in keys:
                data = self.redis_client.hgetall(key)
                hide_flag = data.get(b'hide_from_recommendation', b'False').decode() == 'True'
                hidden_at_str = data.get(b'hidden_at', b'').decode()
                
                if not hide_flag or not hidden_at_str:
                    continue
                
                try:
                    hidden_at = datetime.fromisoformat(hidden_at_str)
                    days_hidden = (now - hidden_at).days
                    
                    # 如果超过30天，自动恢复
                    if days_hidden >= 30:
                        question_id = data.get(b'question_id', b'').decode()
                        self.redis_client.hset(key, mapping={
                            'hide_from_recommendation': 'False',
                            'hidden_at': ''
                        })
                        logger.info(f"题目已自动恢复: question_id={question_id}, 隐藏天数={days_hidden}")
                        restored_count += 1
                except ValueError:
                    continue
            
            if restored_count > 0:
                logger.info(f"共恢复 {restored_count} 个过期隐藏题目")
            
            return restored_count
            
        except Exception as e:
            logger.error(f"检查隐藏题目失败: {str(e)}")
            return 0

    def delete_question_feedback(self, question_id: str, user_id: str = "default") -> bool:
        """
        删除题目反馈（软删除，保留30天）
        
        参数:
            question_id: 题目ID
            user_id: 用户ID
            
        返回:
            是否成功
        """
        if not self.redis_client:
            return False
        
        try:
            key = self._get_feedback_key(question_id, user_id)
            now = datetime.now().isoformat()
            
            # 标记为隐藏并设置隐藏时间
            self.redis_client.hset(key, mapping={
                'hide_from_recommendation': 'True',
                'hidden_at': now,
                'mastery_level': '5',  # 设置为满级
                'updated_at': now
            })
            
            logger.info(f"题目已软删除: question_id={question_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除题目反馈失败: {str(e)}")
            return False

    def should_exclude_from_recommendation(self, question_id: str, user_id: str = "default") -> bool:
        """
        检查题目是否应该从推荐中排除
        
        参数:
            question_id: 题目ID
            user_id: 用户ID
            
        返回:
            True=应该排除，False=可以推荐
        """
        feedback = self.get_feedback(question_id, user_id)
        if not feedback:
            return False
        
        # 如果标记为隐藏且未过期，则排除
        if feedback.hide_from_recommendation and feedback.hidden_at:
            try:
                hidden_at = datetime.fromisoformat(feedback.hidden_at)
                days_hidden = (datetime.now() - hidden_at).days
                # 30天内排除
                return days_hidden < 30
            except ValueError:
                return False
        
        return False

    def get_hidden_questions(self, user_id: str = "default") -> List[str]:
        """
        获取已隐藏（软删除）的题目ID列表
        
        参数:
            user_id: 用户ID
            
        返回:
            隐藏的题目ID列表
        """
        if not self.redis_client:
            return []
        
        try:
            pattern = f"feedback:{user_id}:*"
            keys = self.redis_client.keys(pattern)
            hidden_ids = []
            now = datetime.now()
            
            for key in keys:
                data = self.redis_client.hgetall(key)
                hide_flag = data.get(b'hide_from_recommendation', b'False').decode() == 'True'
                hidden_at_str = data.get(b'hidden_at', b'').decode()
                
                if not hide_flag or not hidden_at_str:
                    continue
                
                try:
                    hidden_at = datetime.fromisoformat(hidden_at_str)
                    days_hidden = (now - hidden_at).days
                    
                    # 只返回30天内的隐藏题目
                    if days_hidden < 30:
                        question_id = data.get(b'question_id', b'').decode()
                        if question_id:
                            hidden_ids.append(question_id)
                except ValueError:
                    continue
            
            return hidden_ids
            
        except Exception as e:
            logger.error(f"获取隐藏题目失败: {str(e)}")
            return []

# Trigger reload


