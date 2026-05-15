"""
审核服务模块

用于管理面试题入库前的审核流程。
所有通过爬虫或API接入的面试题都需要先进入待审核区，
通过审核后才能进入正式的问题库。
"""

import logging
import os
import struct
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional, Optional

from app.config.config_manager import config_manager

logger = logging.getLogger(__name__)


# 尝试导入 Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class PendingQuestion:
    """待审核问题数据结构"""
    id: str
    title: str
    answer: str
    source_url: str
    tags: List[str]
    importance_score: float
    difficulty: str
    category: str
    embedding: Optional[bytes] = None
    created_at: str = ""
    source: str = ""  # batch_async, single_url, api_ingest


class ReviewService:
    """
    审核服务类

    管理面试题的审核流程：
    1. 问题先进入待审核区（pending_review:*）
    2. 管理员审核后，通过的问题进入正式库（question:*）
    3. 拒绝的问题进入拒绝区（rejected_review:*）或被删除
    """

    def __init__(self):
        self.redis_client = None
        self._init_redis_client()

    def _init_redis_client(self):
        """初始化 Redis 客户端"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis 模块未安装")
            return

        try:
            redis_url = config_manager.get_redis_url() or os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()
            logger.info(f"ReviewService Redis 客户端初始化成功 ({redis_url})")
        except Exception as e:
            logger.error(f"ReviewService Redis 客户端初始化失败: {str(e)}")
            self.redis_client = None

    def _create_embedding(self, text: str) -> Optional[bytes]:
        """生成文本向量（复用 vector_service 的逻辑）"""
        from app.services.vector_service import VectorService
        vs = VectorService()
        embedding = vs._create_embedding(text)
        if embedding:
            return struct.pack(f'{len(embedding)}f', *embedding)
        return None

    def save_pending_review(
            self,
            records: List,
            source: str = "api_ingest"
    ) -> int:
        """
        保存问题到待审核区

        参数:
            records: VectorRecord 列表
            source: 来源标识 (batch_async, single_url, api_ingest)

        返回:
            成功保存的数量
        """
        if not self.redis_client:
            logger.error("Redis 客户端未初始化")
            return 0

        count = 0
        timestamp = datetime.now().isoformat()

        for record in records:
            try:
                question_id = str(uuid.uuid4())

                # 生成 embedding
                embedding_bytes = None
                if hasattr(record, 'embedding') and record.embedding:
                    embedding_bytes = struct.pack(f'{len(record.embedding)}f', *record.embedding)
                else:
                    # 为待审核问题生成向量
                    text = getattr(record, 'title', '') + " " + getattr(record, 'answer', '')[:200]
                    embedding = self._create_embedding(text)
                    if embedding:
                        embedding_bytes = struct.pack(f'{len(embedding)}f', *embedding)

                # 构建数据
                tags = getattr(record, 'tags', []) or []
                data = {
                    "id": question_id,
                    "title": getattr(record, 'title', ''),
                    "answer": getattr(record, 'answer', ''),
                    "source_url": getattr(record, 'source_url', ''),
                    "tags": ",".join(tags),
                    "importance_score": str(getattr(record, 'importance_score', 0.0)),
                    "difficulty": getattr(record, 'difficulty', 'medium'),
                    "category": getattr(record, 'category', ''),
                    "embedding": embedding_bytes or b'',
                    "created_at": timestamp,
                    "source": source,
                }

                # 存入 pending_review:{id}
                key = f"pending_review:{question_id}"
                self.redis_client.hset(key, mapping=data)

                # 加入待审核列表（按时间排序的 Sorted Set）
                score = datetime.now().timestamp()
                self.redis_client.zadd("review:pending:list", {question_id: score})

                # 更新统计
                self._increment_stat("pending_count")
                self._increment_stat(f"{source}_count")

                count += 1
                logger.debug(f"保存待审核问题: {question_id} - {getattr(record, 'title', '')[:50]}")

            except Exception as e:
                logger.error(f"保存待审核问题失败: {str(e)}")
                continue

        logger.info(f"保存 {count} 个问题到待审核区 (来源: {source})")
        return count

    def get_pending_list(
            self,
            limit: int = 50,
            offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取待审核问题列表（分页）

        参数:
            limit: 返回数量
            offset: 偏移量

        返回:
            待审核问题列表
        """
        if not self.redis_client:
            return []

        try:
            # 从 Sorted Set 中获取 ID 列表（按时间倒序）
            question_ids = self.redis_client.zrevrange(
                "review:pending:list",
                offset,
                offset + limit - 1
            )

            questions = []
            for qid in question_ids:
                if isinstance(qid, bytes):
                    qid = qid.decode()
                key = f"pending_review:{qid}"
                data = self.redis_client.hgetall(key)

                if data:
                    questions.append(self._parse_pending_data(data))

            return questions

        except Exception as e:
            logger.error(f"获取待审核列表失败: {str(e)}")
            return []

    def get_pending_count(self) -> int:
        """获取待审核问题数量"""
        if not self.redis_client:
            return 0

        try:
            return self.redis_client.zcard("review:pending:list")
        except Exception as e:
            logger.error(f"获取待审核数量失败: {str(e)}")
            return 0

    def get_pending_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取待审核问题详情"""
        if not self.redis_client:
            return None

        try:
            key = f"pending_review:{question_id}"
            data = self.redis_client.hgetall(key)
            if data:
                return self._parse_pending_data(data)
            return None
        except Exception as e:
            logger.error(f"获取待审核问题详情失败: {str(e)}")
            return None

    def _parse_pending_data(self, data: Dict) -> Dict[str, Any]:
        """解析待审核问题数据"""
        embedding_bytes = data.get(b'embedding', b'')
        embedding = None
        if embedding_bytes:
            import struct
            embedding_len = len(embedding_bytes) // 4
            embedding = list(struct.unpack(f'{embedding_len}f', embedding_bytes))

        return {
            "id": data.get(b'id', b'').decode(),
            "title": data.get(b'title', b'').decode(),
            "answer": data.get(b'answer', b'').decode(),
            "source_url": data.get(b'source_url', b'').decode(),
            "tags": data.get(b'tags', b'').decode().split(",") if data.get(b'tags') else [],
            "importance_score": float(data.get(b'importance_score', b'0')),
            "difficulty": data.get(b'difficulty', b'medium').decode(),
            "category": data.get(b'category', b'').decode(),
            "embedding": embedding,
            "created_at": data.get(b'created_at', b'').decode(),
            "source": data.get(b'source', b'').decode(),
        }

    def approve_questions(
            self,
            question_ids: List[str],
            check_similarity: bool = True,
            similarity_threshold: float = 0.85
    ) -> Dict[str, Any]:
        """
        审核通过问题，移动到正式库

        参数:
            question_ids: 问题ID列表
            check_similarity: 是否检查相似问题
            similarity_threshold: 相似度阈值

        返回:
            操作结果统计
        """
        if not self.redis_client:
            return {"status": "error", "message": "Redis 未初始化", "approved": 0}

        from app.services.vector_service import VectorService, VectorRecord
        vs = VectorService()

        approved_count = 0
        skipped_count = 0
        failed_ids = []

        for qid in question_ids:
            try:
                # 获取待审核数据
                pending_key = f"pending_review:{qid}"
                pending_data = self.redis_client.hgetall(pending_key)

                if not pending_data:
                    logger.warning(f"待审核问题不存在: {qid}")
                    skipped_count += 1
                    continue

                # 构建 VectorRecord
                embedding_bytes = pending_data.get(b'embedding', b'')
                embedding = None
                if embedding_bytes:
                    embedding_len = len(embedding_bytes) // 4
                    embedding = list(struct.unpack(f'{embedding_len}f', embedding_bytes))

                record = VectorRecord(
                    id=qid,
                    title=pending_data.get(b'title', b'').decode(),
                    answer=pending_data.get(b'answer', b'').decode(),
                    source_url=pending_data.get(b'source_url', b'').decode(),
                    tags=pending_data.get(b'tags', b'').decode().split(",") if pending_data.get(b'tags') else [],
                    importance_score=float(pending_data.get(b'importance_score', b'0')),
                    difficulty=pending_data.get(b'difficulty', b'medium').decode(),
                    category=pending_data.get(b'category', b'').decode(),
                    embedding=embedding,
                )

                # 检查相似问题
                if check_similarity:
                    similar = vs.find_similar_question(
                        record.title + " " + record.answer[:200],
                        similarity_threshold
                    )
                    if similar:
                        # 合并到已存在的问题
                        vs.merge_into_existing_question(similar['id'], record)
                        logger.info(f"问题 {qid} 合并到已存在问题: {similar['id']}")
                        approved_count += 1
                    else:
                        # 插入新问题
                        if vs.insert_question(record, check_similarity=False):
                            approved_count += 1
                        else:
                            failed_ids.append(qid)
                else:
                    if vs.insert_question(record, check_similarity=False):
                        approved_count += 1
                    else:
                        failed_ids.append(qid)

                # 从待审核区删除
                self.redis_client.delete(pending_key)
                self.redis_client.zrem("review:pending:list", qid)

                # 更新统计
                self._increment_stat("approved_count")
                self._decrement_stat("pending_count")

            except Exception as e:
                logger.error(f"审核通过问题失败 {qid}: {str(e)}")
                failed_ids.append(qid)
                continue

        return {
            "status": "success",
            "approved": approved_count,
            "skipped": skipped_count,
            "failed": len(failed_ids),
            "failed_ids": failed_ids,
        }

    def approve_all(self, check_similarity: bool = True) -> Dict[str, Any]:
        """
        审核通过所有待审核问题

        参数:
            check_similarity: 是否检查相似问题

        返回:
            操作结果统计
        """
        if not self.redis_client:
            return {"status": "error", "message": "Redis 未初始化", "approved": 0}

        # 获取所有待审核 ID
        question_ids = self.redis_client.zrange("review:pending:list", 0, -1)
        if isinstance(question_ids[0], bytes) if question_ids else False:
            question_ids = [qid.decode() for qid in question_ids]

        if not question_ids:
            return {"status": "success", "approved": 0, "message": "没有待审核问题"}

        logger.info(f"开始审核通过所有待审核问题: {len(question_ids)} 个")
        return self.approve_questions(question_ids, check_similarity)

    def reject_questions(
            self,
            question_ids: List[str],
            delete: bool = False
    ) -> Dict[str, Any]:
        """
        审核拒绝问题

        参数:
            question_ids: 问题ID列表
            delete: 是否直接删除（False则移入拒绝区）

        返回:
            操作结果统计
        """
        if not self.redis_client:
            return {"status": "error", "message": "Redis 未初始化", "rejected": 0}

        rejected_count = 0

        for qid in question_ids:
            try:
                if delete:
                    # 直接删除
                    self.redis_client.delete(f"pending_review:{qid}")
                else:
                    # 移入拒绝区
                    pending_key = f"pending_review:{qid}"
                    pending_data = self.redis_client.hgetall(pending_key)

                    if pending_data:
                        rejected_key = f"rejected_review:{qid}"
                        # 添加拒绝时间
                        rejected_data = dict(pending_data)
                        rejected_data[b'rejected_at'] = datetime.now().isoformat().encode()
                        self.redis_client.hset(rejected_key, mapping=rejected_data)
                        self.redis_client.delete(pending_key)
                    else:
                        logger.warning(f"待审核问题不存在: {qid}")

                # 从待审核列表移除
                self.redis_client.zrem("review:pending:list", qid)

                # 更新统计
                self._increment_stat("rejected_count")
                self._decrement_stat("pending_count")

                rejected_count += 1

            except Exception as e:
                logger.error(f"审核拒绝问题失败 {qid}: {str(e)}")
                continue

        return {
            "status": "success",
            "rejected": rejected_count,
        }

    def get_rejected_list(
            self,
            limit: int = 50,
            offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取被拒绝的问题列表"""
        if not self.redis_client:
            return []

        try:
            keys = self.redis_client.keys("rejected_review:*")
            if hasattr(keys, "__await__"):
                import asyncio
                keys = asyncio.get_event_loop().run_until_complete(keys)

            # 分页
            keys = keys[offset:offset + limit]

            questions = []
            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode()
                data = self.redis_client.hgetall(key)
                if data:
                    questions.append({
                        "id": key.replace("rejected_review:", ""),
                        "title": data.get(b'title', b'').decode(),
                        "answer": data.get(b'answer', b'').decode(),
                        "source_url": data.get(b'source_url', b'').decode(),
                        "tags": data.get(b'tags', b'').decode().split(",") if data.get(b'tags') else [],
                        "importance_score": float(data.get(b'importance_score', b'0')),
                        "difficulty": data.get(b'difficulty', b'medium').decode(),
                        "category": data.get(b'category', b'').decode(),
                        "rejected_at": data.get(b'rejected_at', b'').decode(),
                    })
            return questions

        except Exception as e:
            logger.error(f"获取拒绝列表失败: {str(e)}")
            return []

    def restore_rejected(self, question_ids: List[str]) -> int:
        """
        恢复被拒绝的问题到待审核区

        参数:
            question_ids: 问题ID列表

        返回:
            恢复数量
        """
        if not self.redis_client:
            return 0

        restored = 0
        timestamp = datetime.now().timestamp()

        for qid in question_ids:
            try:
                rejected_key = f"rejected_review:{qid}"
                rejected_data = self.redis_client.hgetall(rejected_key)

                if rejected_data:
                    # 移除 rejected_at 字段
                    rejected_data.pop(b'rejected_at', None)

                    # 移回待审核区
                    pending_key = f"pending_review:{qid}"
                    self.redis_client.hset(pending_key, mapping=rejected_data)
                    self.redis_client.zadd("review:pending:list", {qid: timestamp})
                    self.redis_client.delete(rejected_key)

                    self._increment_stat("pending_count")
                    self._decrement_stat("rejected_count")
                    restored += 1

            except Exception as e:
                logger.error(f"恢复被拒绝问题失败 {qid}: {str(e)}")
                continue

        return restored

    def get_stats(self) -> Dict[str, Any]:
        """
        获取审核统计信息

        返回:
            统计数据
        """
        if not self.redis_client:
            return {
                "pending_count": 0,
                "approved_count": 0,
                "rejected_count": 0,
            }

        try:
            stats_key = "review:stats"
            stats = self.redis_client.hgetall(stats_key)

            return {
                "pending_count": self.get_pending_count(),
                "approved_count": int(stats.get(b'approved_count', 0)),
                "rejected_count": int(stats.get(b'rejected_count', 0)),
                "batch_async_count": int(stats.get(b'batch_async_count', 0)),
                "single_url_count": int(stats.get(b'single_url_count', 0)),
                "api_ingest_count": int(stats.get(b'api_ingest_count', 0)),
            }

        except Exception as e:
            logger.error(f"获取审核统计失败: {str(e)}")
            return {
                "pending_count": 0,
                "approved_count": 0,
                "rejected_count": 0,
            }

    def _increment_stat(self, field: str):
        """增加统计计数"""
        if not self.redis_client:
            return
        try:
            self.redis_client.hincrby("review:stats", field, 1)
        except Exception as e:
            logger.debug(f"更新统计失败: {str(e)}")

    def _decrement_stat(self, field: str):
        """减少统计计数"""
        if not self.redis_client:
            return
        try:
            current = self.redis_client.hget("review:stats", field)
            if current and int(current) > 0:
                self.redis_client.hincrby("review:stats", field, -1)
        except Exception as e:
            logger.debug(f"更新统计失败: {str(e)}")


# 全局单例
review_service = ReviewService()