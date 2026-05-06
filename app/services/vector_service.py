# app/services/vector_service.py
"""
向量数据库服务模块

用于存储和检索面试问题的向量表示。
"""

import struct
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# 尝试导入 Redis
try:
    import redis
    from redis.commands.search.query import Query
    from redis.commands.search.field import VectorField, TagField, TextField

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# 尝试导入 OpenAI Embedding
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)
load_dotenv()


@dataclass
class VectorRecord:
    """
    向量记录数据结构
    """

    id: str
    title: str
    answer: str
    source_url: str
    tags: List[str]
    importance_score: float
    difficulty: str
    category: str
    embedding: Optional[List[float]] = None


class VectorService:
    """
    向量数据库服务类
    """

    def __init__(self):
        self.redis_client = None
        self.openai_client = None
        self.index_name = "interview_questions_idx"
        self._init_clients()

    def _init_clients(self):
        """
        初始化客户端（Redis 和 OpenAI）
        """
        # 1. 初始化 Redis 客户端
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url)
            # 测试连接
            self.redis_client.ping()
            logger.info("Redis 客户端初始化成功")
        except Exception as e:
            logger.error(f"Redis 客户端初始化失败: {str(e)}")

        # 2. 初始化 OpenAI 客户端（用于生成 Embedding）
        api_key = os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE")

        if api_key and OPENAI_AVAILABLE:
            try:
                if api_base:
                    self.openai_client = OpenAI(api_key=api_key, base_url=api_base)
                else:
                    self.openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI Embedding 客户端初始化成功")
            except Exception as e:
                logger.error(f"OpenAI 客户端初始化失败: {str(e)}")
            
            
    def _create_embedding(self, text: str) -> List[float]:
        """
        生成文本的向量表示
        """
        if not self.openai_client:
            logger.warning("OpenAI 客户端未初始化，使用简单哈希生成向量")
            return self._simple_hash_embedding(text)

        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            )

            # 检查响应格式是否正确
            if not hasattr(response, "data") or not response.data:
                logger.error(f"Embedding API 响应格式异常: {response}")
                # 记录详细的错误信息
                if isinstance(response, str):
                    logger.error(f"API 返回字符串而不是对象: {response[:200]}")
                else:
                    logger.error(f"API 响应类型: {type(response)}")
                raise Exception(
                    f"Embedding API 响应格式异常: {type(response)} - {response}"
                )

            if not hasattr(response.data[0], "embedding"):
                logger.error(f"Embedding API 响应数据格式异常: {response.data}")
                raise Exception("Embedding API 响应数据格式异常")

            return response.data[0].embedding
        except Exception as e:
            logger.error(f"生成 Embedding 失败: {str(e)}")
            logger.warning("使用简单哈希生成向量作为备用方案")
            return self._simple_hash_embedding(text)

    def _simple_hash_embedding(self, text: str) -> List[float]:
        """
        使用简单哈希生成向量（备用方案）
        """
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        # 生成一个简单的 384 维向量
        vector = []
        for i in range(384):
            vector.append(((hash_val >> (i * 8)) & 0xFF) / 255.0)
        return vector

    def _ensure_index(self):
        """
        确保搜索索引存在
        """
        if not self.redis_client:
            return False

        try:
            # 检查索引是否存在
            info = self.redis_client.ft(self.index_name).info()
            # info 可能是字典或对象，兼容处理
            if isinstance(info, dict):
                num_docs = info.get('num_docs', 0)
            else:
                num_docs = getattr(info, 'num_docs', 0)
            logger.info(f"索引 {self.index_name} 已存在，文档数: {num_docs}")
            return True
        except Exception as e:
            error_msg = str(e)
            # 如果是因为索引不存在导致的错误，则创建索引
            if "Unknown index name" in error_msg or "does not exist" in error_msg.lower():
                logger.info(f"索引不存在，准备创建")
            else:
                # 其他错误，也尝试创建（可能索引损坏）
                logger.warning(f"检查索引时出错: {error_msg}，尝试重新创建")
            
            # 创建索引
            try:
                embedding_dim = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
                schema = [
                    TextField("title", weight=2.0),
                    TextField("answer", weight=1.0),
                    TagField("tags"),
                    TagField("difficulty"),
                    TagField("category"),
                    VectorField(
                        "embedding",
                        "FLAT",
                        {"TYPE": "FLOAT32", "DIM": embedding_dim, "DISTANCE_METRIC": "COSINE"},
                    ),
                ]

                self.redis_client.ft(self.index_name).create_index(schema)
                logger.info(f"创建索引 {self.index_name} 成功")
                return True
            except Exception as create_error:
                # 如果是因为索引已存在，说明并发创建或之前已创建成功
                if "Index already exists" in str(create_error):
                    logger.info(f"索引 {self.index_name} 已存在（可能由其他进程创建）")
                    return True
                else:
                    logger.error(f"创建索引失败: {str(create_error)}")
                    return False



    def insert_question(self, question: VectorRecord) -> bool:
        """
        插入单个问题到向量数据库

        参数:
            question: 问题记录

        返回:
            是否成功
        """
        if not self.redis_client:
            logger.error("Redis 客户端未初始化")
            return False

        # 确保索引存在（重要：必须在插入前创建索引）
        self._ensure_index()

        if not question.embedding:
            question.embedding = self._create_embedding(
                question.title + " " + question.answer
            )

        try:
            # 生成唯一 ID
            import uuid

            if not question.id:
                question.id = str(uuid.uuid4())

            # 存储到 Redis
            key = f"question:{question.id}"
            # 将 embedding 列表转换为二进制格式（float32）
            embedding_bytes = struct.pack(f'{len(question.embedding)}f', *question.embedding)
            data = {
                "id": question.id,
                "title": question.title,
                "answer": question.answer,
                "source_url": question.source_url,
                "tags": ",".join(question.tags),
                "importance_score": str(question.importance_score),
                "difficulty": question.difficulty,
                "category": question.category,
                "embedding": embedding_bytes,
            }

            self.redis_client.hset(key, mapping=data)
            logger.info(f"插入问题成功: {question.title} (ID: {question.id})")
            return True

        except Exception as e:
            logger.error(f"插入问题失败: {str(e)}")
            return False

    def insert_questions(self, questions: List[VectorRecord]) -> int:
        """
        批量插入问题

        参数:
            questions: 问题列表

        返回:
            成功插入的数量
        """
        count = 0
        for question in questions:
            if self.insert_question(question):
                count += 1
        return count

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, List[str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索相关问题

        参数:
            query: 搜索查询词
            limit: 返回数量限制
            filters: 过滤条件（如 tags、difficulty、category）

        返回:
            匹配的问题列表
        """
        if not self.redis_client:
            logger.error("Redis 客户端未初始化")
            return []

        # 确保索引存在
        self._ensure_index()

        try:
            # 生成查询向量
            query_embedding = self._create_embedding(query)

            # 构建查询
            base_query = f"*=>[KNN {limit} @embedding $vector AS score]"

            # 添加过滤条件
            if filters:
                filter_parts = []
                if "tags" in filters:
                    tags = [f"{{{tag}}}" for tag in filters["tags"]]
                    filter_parts.append(f"@tags:({'|'.join(tags)})")
                if "difficulty" in filters:
                    difficulties = [f"{{{d}}}" for d in filters["difficulty"]]
                    filter_parts.append(f"@difficulty:({'|'.join(difficulties)})")
                if "category" in filters:
                    categories = [f"{{{c}}}" for c in filters["category"]]
                    filter_parts.append(f"@category:({'|'.join(categories)})")

                if filter_parts:
                    base_query = f"({base_query}) @ ({' '.join(filter_parts)})"

            query_obj = (
                Query(base_query)
                .return_fields(
                    "id",
                    "title",
                    "answer",
                    "source_url",
                    "tags",
                    "importance_score",
                    "difficulty",
                    "category",
                    "score",
                )
                .sort_by("score")
                .dialect(2)
            )

            # 执行查询
            # 将 embedding 列表转换为二进制格式（float32）
            query_embedding_bytes = struct.pack(f'{len(query_embedding)}f', *query_embedding)
            params = {"vector": query_embedding_bytes}
            results = self.redis_client.ft(self.index_name).search(
                query_obj, query_params=params
            )

            # 处理结果
            questions = []
            for doc in results.docs:
                questions.append(
                    {
                        "id": doc.id.replace("question:", ""),
                        "title": doc.title,
                        "answer": doc.answer,
                        "source_url": doc.source_url,
                        "tags": doc.tags.split(",") if doc.tags else [],
                        "importance_score": float(doc.importance_score),
                        "difficulty": doc.difficulty,
                        "category": doc.category,
                        "score": float(doc.score),
                    }
                )

            return questions

        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return []

    def get_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取问题

        参数:
            question_id: 问题 ID

        返回:
            问题详情
        """
        if not self.redis_client:
            return None

        try:
            key = f"question:{question_id}"
            data = self.redis_client.hgetall(key)

            if not data:
                return None

            return {
                "id": question_id,
                "title": data.get(b"title", b"").decode(),
                "answer": data.get(b"answer", b"").decode(),
                "source_url": data.get(b"source_url", b"").decode(),
                "tags": (
                    data.get(b"tags", b"").decode().split(",")
                    if data.get(b"tags")
                    else []
                ),
                "importance_score": float(data.get(b"importance_score", b"0")),
                "difficulty": data.get(b"difficulty", b"").decode(),
                "category": data.get(b"category", b"").decode(),
            }

        except Exception as e:
            logger.error(f"获取问题失败: {str(e)}")
            return None

    def delete_by_id(self, question_id: str) -> bool:
        """
        删除指定问题

        参数:
            question_id: 问题 ID

        返回:
            是否成功
        """
        if not self.redis_client:
            return False

        try:
            key = f"question:{question_id}"
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"删除问题失败: {str(e)}")
            return False

    def get_all(self) -> List[Dict[str, Any]]:
        """
        获取所有问题

        返回:
            所有问题列表
        """
        if not self.redis_client:
            return []

        try:
            keys = self.redis_client.keys("question:*")
            if hasattr(keys, "__await__"):
                import asyncio

                keys = asyncio.get_event_loop().run_until_complete(keys)

            questions = []

            for key in keys:
                data = self.redis_client.hgetall(key)
                question_id = key.decode().replace("question:", "")

                questions.append(
                    {
                        "id": question_id,
                        "title": data.get(b"title", b"").decode(),
                        "answer": data.get(b"answer", b"").decode(),
                        "source_url": data.get(b"source_url", b"").decode(),
                        "tags": (
                            data.get(b"tags", b"").decode().split(",")
                            if data.get(b"tags")
                            else []
                        ),
                        "importance_score": float(data.get(b"importance_score", b"0")),
                        "difficulty": data.get(b"difficulty", b"").decode(),
                        "category": data.get(b"category", b"").decode(),
                    }
                )

            return questions

        except Exception as e:
            logger.error(f"获取所有问题失败: {str(e)}")
            return []

    def count(self) -> int:
        """
        获取问题总数

        返回:
            问题数量
        """
        if not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys("question:*")
            return len(keys)
        except Exception as e:
            logger.error(f"统计问题数量失败: {str(e)}")
            return 0