# app/services/vector_service.py
"""
向量数据库服务模块

用于存储和检索面试问题的向量表示。
"""

import struct
import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# 导入统一配置管理器
from app.config.config_manager import config_manager

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
            # 优先从 config.yaml 读取，兼容环境变量
            redis_url = config_manager.get_redis_url() or os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url)
            # 测试连接
            self.redis_client.ping()
            logger.info(f"Redis 客户端初始化成功 ({redis_url})")
        except Exception as e:
            logger.error(f"Redis 客户端初始化失败: {str(e)}")

        # 2. 初始化 OpenAI 客户端（用于生成 Embedding）
        # 优先使用独立的 Embedding 配置，兼容 LLM 配置
        # config_manager 会自动从 YAML 读取并解析环境变量
        api_key = config_manager.get('llm.embedding.api_key') or \
                  config_manager.get('llm.openai.api_key')
        api_base = config_manager.get('llm.embedding.api_base') or \
                   config_manager.get('llm.openai.api_base')

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
            # 优先从 config.yaml 读取 Embedding 模型名称和维度
            embedding_model = config_manager.get('llm.embedding.model') or \
                             config_manager.get('llm.embedding_model') or \
                             os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
            embedding_dim = config_manager.get('llm.embedding.dimension') or \
                           config_manager.get('llm.embedding_dimension') or \
                           int(os.getenv("EMBEDDING_DIMENSION", "1024"))
            
            # 构建请求参数
            request_params = {
                "input": text,
                "model": embedding_model,
            }
            
            # 对于支持动态维度的模型（如 OpenAI text-embedding-3系列），传入 dimensions 参数
            # BAAI/bge-m3 等固定维度模型会忽略此参数
            if "text-embedding-3" in embedding_model:
                request_params["dimensions"] = embedding_dim
            
            response = self.openai_client.embeddings.create(**request_params)

            # 检查响应类型，确保不是字符串
            if isinstance(response, str):
                logger.error(f"Embedding API 返回字符串而不是对象: {response[:200]}")
                raise Exception(f"API 返回字符串响应: {response[:100]}...")

            # 检查响应格式是否正确
            if not hasattr(response, "data") or not response.data:
                logger.error(f"Embedding API 响应格式异常: {type(response)} - {response}")
                raise Exception(
                    f"Embedding API 响应格式异常: {type(response)} - {response}"
                )

            if not hasattr(response.data[0], "embedding"):
                logger.error(f"Embedding API 响应数据格式异常: {response.data}")
                raise Exception("Embedding API 响应数据格式异常")

            embedding = response.data[0].embedding
            
            # 验证向量维度是否与配置一致
            actual_dim = len(embedding)
            if actual_dim != embedding_dim:
                logger.warning(
                    f"向量维度不匹配: 模型 '{embedding_model}' 返回 {actual_dim} 维，"
                    f"但配置为 {embedding_dim} 维。这可能导致搜索失败。"
                )
            
            return embedding
        except Exception as e:
            error_msg = str(e)
            logger.error(f"生成 Embedding 失败: {error_msg}")
            
            # 如果是网络错误或API错误，记录详细信息
            if "Connection" in error_msg or "HTTP" in error_msg or "307" in error_msg:
                logger.error(f"可能是 API 端点配置错误，请检查 EMBEDDING_API_BASE 配置")
            
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
                attributes = info.get('attributes', [])
            else:
                num_docs = getattr(info, 'num_docs', 0)
                attributes = getattr(info, 'attributes', [])
            
            # 确保 attributes 是列表
            if not isinstance(attributes, list):
                logger.warning(f"attributes 不是列表类型: {type(attributes)}")
                attributes = []
            
            # 检查是否包含 importance_score 字段
            has_importance_field = any(
                (isinstance(attr, dict) and attr.get('identifier') == 'importance_score') or
                (hasattr(attr, 'identifier') and getattr(attr, 'identifier', None) == 'importance_score')
                for attr in attributes
            )
            
            if has_importance_field:
                logger.info(f"索引 {self.index_name} 已存在，文档数: {num_docs}")
                return True
            else:
                # 索引存在但缺少 importance_score 字段，需要重建
                logger.warning(f"索引 {self.index_name} 缺少 importance_score 字段，需要重建")
                raise Exception("Index schema outdated")
                
        except Exception as e:
            error_msg = str(e)
            # 如果是因为索引不存在导致的错误，则创建索引
            if "Unknown index name" in error_msg or "does not exist" in error_msg.lower() or "schema outdated" in error_msg.lower():
                logger.info("索引不存在或需要重建，准备创建")
            else:
                # 其他错误，也尝试创建（可能索引损坏）
                logger.warning(f"检查索引时出错: {error_msg}，尝试重新创建")

            # 如果索引已存在，先删除旧索引
            try:
                self.redis_client.ft(self.index_name).dropindex(delete_documents=False)
                logger.info(f"已删除旧索引 {self.index_name}")
            except Exception as drop_error:
                logger.debug(f"删除索引失败（可能不存在）: {str(drop_error)}")

            # 创建新索引
            try:
                # 优先从 config.yaml 读取，兼容环境变量
                embedding_dim = config_manager.get('llm.embedding.dimension') or \
                               config_manager.get('llm.embedding_dimension') or \
                               int(os.getenv("EMBEDDING_DIMENSION", "1024"))
                from redis.commands.search.field import NumericField
                schema = [
                    TextField("title", weight=2.0),
                    TextField("answer", weight=1.0),
                    TagField("tags"),
                    TagField("difficulty"),
                    TagField("category"),
                    NumericField("importance_score"),
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

    def insert_question(
            self,
            question: VectorRecord,
            check_similarity: bool = True,
            similarity_threshold: float = 0.85) -> bool:
        """
        插入单个问题到向量数据库

        参数:
            question: 问题记录
            check_similarity: 是否检查相似问题（默认True）
            similarity_threshold: 相似度阈值（默认0.85）

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

            # 检查是否存在相似问题（使用标题+答案的组合提高准确性）
            if check_similarity:
                search_text = question.title + " " + question.answer[:200]  # 使用前200字符的答案
                similar_question = self.find_similar_question(search_text, similarity_threshold)
                if similar_question:
                    logger.info(
                        f"发现相似问题: {question.title} -> "
                        f"{similar_question['title']} "
                        f"(相似度: {similar_question['score']:.2f})"
                    )
                    # 合并问题而不是插入新的
                    return self.merge_into_existing_question(similar_question['id'], question)

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

    def insert_questions(
            self,
            questions: List[VectorRecord],
            check_similarity: bool = True,
            similarity_threshold: float = 0.85) -> int:
        """
        批量插入问题

        参数:
            questions: 问题列表
            check_similarity: 是否检查相似问题（默认True）
            similarity_threshold: 相似度阈值（默认0.85）

        返回:
            成功插入的数量
        """
        count = 0
        for question in questions:
            if self.insert_question(question, check_similarity, similarity_threshold):
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
                # 解析合并后的来源 URL
                "source_urls": data.get(b"source_url", b"").decode().split(';') if data.get(b"source_url") else [],
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

    def update(self, question_id: str, question_data: Dict[str, Any]) -> bool:
        """
        更新题目数据
        
        参数:
            question_id: 题目ID
            question_data: 题目数据字典
            
        返回:
            是否成功
        """
        if not self.redis_client:
            return False
        
        try:
            key = f"question:{question_id}"
            
            # 构建更新数据
            data = {
                "title": question_data.get('title', ''),
                "answer": question_data.get('answer', ''),
                "source_url": question_data.get('source_url', ''),
                "tags": ",".join(question_data.get('tags', [])),
                "importance_score": str(question_data.get('importance_score', 0)),
                "difficulty": question_data.get('difficulty', ''),
                "category": question_data.get('category', ''),
            }
            
            self.redis_client.hset(key, mapping=data)
            
            # 重要：RediSearch 会自动索引 Hash 字段的变化
            # 但为了确保索引同步，我们记录日志
            logger.info(f"题目更新成功: {question_id}, importance_score={question_data.get('importance_score')}")
            return True
            
        except Exception as e:
            logger.error(f"更新题目失败: {str(e)}")
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

    def _find_most_similar_question(self, text: str, threshold: float = 0.85) -> Optional[Dict[str, Any]]:
        """
        查找最相似的问题

        参数:
            text: 用于搜索的文本（建议使用标题+答案的组合）
            threshold: 相似度阈值

        返回:
            相似问题信息（包含 id, title, score），如果没有找到则返回 None
        """
        try:
            # 生成查询向量
            query_embedding = self._create_embedding(text)

            # 使用 KNN 搜索最相似的问题（返回前5个候选）
            base_query = "*=>[KNN 5 @embedding $vector AS score]"
            query_obj = (
                Query(base_query)
                .return_fields("id", "title", "answer", "score")
                .sort_by("score")
                .dialect(2)
            )

            # 执行查询
            query_embedding_bytes = struct.pack(f'{len(query_embedding)}f', *query_embedding)
            params = {"vector": query_embedding_bytes}
            results = self.redis_client.ft(self.index_name).search(
                query_obj, query_params=params
            )

            # 检查结果是否超过阈值
            if results.docs and len(results.docs) > 0:
                # 遍历所有候选，找到最相似的
                for doc in results.docs:
                    # RediSearch 返回的 score 是距离值（越小越相似），需要转换
                    # COSINE 距离 = 1 - cosine_similarity
                    similarity = 1.0 - float(doc.score)

                    if similarity >= threshold:
                        logger.debug(f"找到相似问题: {doc.title} (相似度: {similarity:.2f})")
                        return {
                            "id": doc.id.replace("question:", ""),
                            "title": doc.title,
                            "answer": doc.answer,
                            "score": similarity
                        }

            return None

        except Exception as e:
            logger.error(f"查找相似问题失败: {str(e)}")
            return None

    def _merge_into_existing_question(self, existing_id: str, new_question: VectorRecord) -> bool:
        """
        将新问题合并到已存在的问题中

        合并策略:
        1. 保留较长的答案（通常更详细）
        2. 合并来源 URL（去重）
        3. 合并标签（去重）
        4. 保留较高的重要性评分

        参数:
            existing_id: 已存在的问题 ID
            new_question: 新问题

        返回:
            是否成功
        """
        try:
            # 获取已存在的问题
            existing_question = self.get_by_id(existing_id)
            if not existing_question:
                logger.error(f"未找到已存在的问题: {existing_id}")
                return False

            # 1. 选择较长的答案
            new_answer = new_question.answer if len(new_question.answer) > len(
                existing_question['answer']) else existing_question['answer']

            # 2. 合并来源 URL（去重）
            existing_urls = existing_question['source_url'].split(';') if ';' in existing_question['source_url'] else [
                existing_question['source_url']]
            all_urls = list(set(existing_urls + [new_question.source_url]))
            merged_source_url = ';'.join(all_urls)

            # 3. 合并标签（去重）
            existing_tags = set(existing_question['tags'])
            new_tags = set(new_question.tags)
            merged_tags = list(existing_tags | new_tags)

            # 4. 保留较高的重要性评分
            merged_importance = max(existing_question['importance_score'], new_question.importance_score)

            # 更新到 Redis
            key = f"question:{existing_id}"
            data = {
                "title": existing_question['title'],  # 保留原标题
                "answer": new_answer,
                "source_url": merged_source_url,
                "tags": ",".join(merged_tags),
                "importance_score": str(merged_importance),
                "difficulty": existing_question['difficulty'],  # 保留原难度
                "category": existing_question['category'],  # 保留原分类
            }

            self.redis_client.hset(key, mapping=data)

            logger.info(f"合并问题成功: {existing_question['title']} (合并了 {new_question.source_url})")
            return True

        except Exception as e:
            logger.error(f"合并问题失败: {str(e)}")
            return False

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

    def exact_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, List[str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        精确搜索（关键词匹配）

        使用 Redis FT.SEARCH 进行文本匹配，支持标题和答案的关键词搜索

        参数:
            query: 搜索查询词
            limit: 返回数量限制
            filters: 过滤条件

        返回:
            匹配的问题列表
        """
        if not self.redis_client:
            logger.error("Redis 客户端未初始化")
            return []

        # 确保索引存在
        self._ensure_index()

        try:
            # 构建文本搜索查询（在 title 和 answer 字段中搜索）
            # Redis FT.SEARCH 不支持 @field1|@field2:term，需要用 ( @field1:term | @field2:term )
            search_terms = query.strip().split()

            # 对于单个词
            if len(search_terms) == 1:
                term = search_terms[0]
                base_query = f"(@title:*{term}* | @answer:*{term}*)"
            else:
                # 多个词用 | 连接（OR 关系）
                title_parts = " | ".join([f"@title:*{term}*" for term in search_terms])
                answer_parts = " | ".join([f"@answer:*{term}*" for term in search_terms])
                base_query = f"({title_parts} | {answer_parts})"

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
                    base_query = f"{base_query} ({' '.join(filter_parts)})"

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
                )
                .dialect(2)
            )

            # 执行查询
            results = self.redis_client.ft(self.index_name).search(query_obj)

            # 处理结果
            questions = []
            for doc in results.docs[:limit]:
                questions.append({
                    "id": doc.id.replace("question:", ""),
                    "title": doc.title,
                    "answer": doc.answer,
                    "source_url": doc.source_url,
                    "tags": doc.tags.split(",") if doc.tags else [],
                    "importance_score": float(doc.importance_score),
                    "difficulty": doc.difficulty,
                    "category": doc.category,
                    "score": 1.0,  # 精确搜索给固定分数
                })

            logger.info(f"精确搜索找到 {len(questions)} 个结果")
            return questions

        except Exception as e:
            logger.error(f"精确搜索失败: {str(e)}")
            return []

    def merge_search_results(
        self,
        semantic_results: List[Dict[str, Any]],
        exact_results: List[Dict[str, Any]],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        合并语义搜索和精确搜索结果

        策略：
        1. 去重（基于 question id）
        2. 优先保留同时在两个结果中的题目
        3. 然后按精确匹配 > 语义匹配的优先级排序

        参数:
            semantic_results: 语义搜索结果
            exact_results: 精确搜索结果
            limit: 最终返回数量

        返回:
            合并后的结果列表
        """
        # 使用字典去重，记录每个题目的来源
        merged_dict = {}

        # 先添加精确搜索结果（赋予更高权重）
        for item in exact_results:
            qid = item['id']
            merged_dict[qid] = {
                **item,
                'match_type': 'exact',
                'combined_score': item.get('score', 1.0) * 1.5,  # 精确匹配权重更高
            }

        # 再添加语义搜索结果（如果已存在则跳过）
        for item in semantic_results:
            qid = item['id']
            if qid not in merged_dict:
                merged_dict[qid] = {
                    **item,
                    'match_type': 'semantic',
                    'combined_score': item.get('score', 0.0),
                }
            else:
                # 如果同时出现在两个结果中，提升分数
                merged_dict[qid]['match_type'] = 'both'
                merged_dict[qid]['combined_score'] += item.get('score', 0.0) * 0.5

        # 按综合分数排序
        sorted_results = sorted(
            merged_dict.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )

        # 移除临时字段，返回前 limit 个
        final_results = []
        for item in sorted_results[:limit]:
            result = {k: v for k, v in item.items() if k not in ['match_type', 'combined_score']}
            final_results.append(result)

        logger.info(f"混合搜索合并结果: {len(final_results)} 个 (精确:{len(exact_results)}, 语义:{len(semantic_results)})")
        return final_results

    def find_similar_question(
        self,
        text: str,
        threshold: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        """
        查找相似问题
        
        参数:
            text: 搜索文本（标题+答案）
            threshold: 相似度阈值（0-1）
            
        返回:
            最相似的问题，如果相似度低于阈值则返回 None
        """
        try:
            # 使用语义搜索查找相似问题
            results = self.search(text, limit=1)
            
            if not results:
                return None
            
            # 检查相似度是否达到阈值
            best_match = results[0]
            score = best_match.get('score', 0.0)
            
            # RediSearch KNN 返回的是距离，需要转换为相似度
            # COSINE 距离范围 [0, 2]，相似度 = 1 - distance/2
            similarity = 1.0 - (score / 2.0)
            
            if similarity >= threshold:
                best_match['score'] = similarity
                return best_match
            else:
                logger.debug(f"最高相似度 {similarity:.2f} 低于阈值 {threshold}")
                return None
                
        except Exception as e:
            logger.error(f"查找相似问题失败: {str(e)}")
            return None
    
    def merge_into_existing_question(
        self,
        existing_id: str,
        new_question: VectorRecord
    ) -> bool:
        """
        将新问题合并到已存在的问题中
        
        策略：
        1. 保留原有问题的 ID、向量、重要性等核心信息
        2. 合并来源 URL（用分号分隔）
        3. 合并标签（去重）
        4. 更新答案（如果新问题答案更长）
        
        参数:
            existing_id: 已存在问题的 ID
            new_question: 新问题
            
        返回:
            是否成功
        """
        try:
            # 获取已存在的问题
            existing_key = f"question:{existing_id}"
            existing_data = self.redis_client.hgetall(existing_key)
            
            if not existing_data:
                logger.warning(f"已存在的问题不存在: {existing_id}")
                return False
            
            # 合并来源 URL
            existing_url = existing_data.get(b'source_url', b'').decode()
            new_url = new_question.source_url
            
            if existing_url and new_url and new_url not in existing_url:
                merged_url = f"{existing_url};{new_url}"
            elif new_url:
                merged_url = new_url
            else:
                merged_url = existing_url
            
            # 合并标签
            existing_tags = existing_data.get(b'tags', b'').decode().split(',') if existing_data.get(b'tags') else []
            new_tags = new_question.tags
            merged_tags = list(set(existing_tags + new_tags))  # 去重
            
            # 选择更长的答案
            existing_answer = existing_data.get(b'answer', b'').decode()
            if len(new_question.answer) > len(existing_answer):
                final_answer = new_question.answer
            else:
                final_answer = existing_answer
            
            # 更新 Redis
            self.redis_client.hset(existing_key, mapping={
                'source_url': merged_url,
                'tags': ','.join(merged_tags),
                'answer': final_answer,
            })
            
            logger.info(f"问题合并成功: {new_question.title} -> {existing_id}")
            return True
            
        except Exception as e:
            logger.error(f"合并问题失败: {str(e)}")
            return False
