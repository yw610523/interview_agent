import asyncio
import json
import logging
from pathlib import Path
from queue import Queue, Empty
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any
from datetime import datetime

import uvicorn
# 定时任务相关
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl

from app.config.crawler_config import (
    CrawlerConfig,
    get_config_from_env,
    get_scheduler_config,
)
# 导入配置热加载管理器
from app.services.config_hot_reload import config_reload_manager
# 导入大模型和向量服务
from app.services.llm_service import LLMService
# 导入爬虫相关模块
from app.services.sitemap_crawler import SitemapCrawler
from app.services.vector_service import VectorService, VectorRecord
# 导入任务管理器
from app.services.crawl_task_manager import crawl_task_manager, TaskStatus
# 导入反馈服务
from app.services.feedback_service import FeedbackService

app = FastAPI(title="Interview AI Agent")

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 全局变量存储最近一次爬取结果
last_crawl_result: Optional[Dict[str, Any]] = None

# SSE日志队列（用于单页爬取的实时日志推送）
sse_log_queues: Dict[str, Queue] = {}

# 初始化服务
llm_service = LLMService()
vector_service = VectorService()
feedback_service = FeedbackService()

# 线程池（用于将同步I/O操作放入后台执行，不阻塞事件循环）
executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="sync_io")

# 设置配置热加载管理器的服务引用
config_reload_manager.set_services(llm_service, vector_service)


def run_sync(func, *args, **kwargs):
    """
    在后台线程中运行同步函数，不阻塞事件循环

    用法: result = await run_sync(vector_service.search, query, limit)
    """
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(executor, lambda: func(*args, **kwargs))

# 定义面试题数据模型


class InterviewQuestion(BaseModel):
    title: str
    answer: str
    source_url: HttpUrl
    tags: List[str]
    importance_score: Optional[float] = 0.0
    difficulty: Optional[str] = "medium"
    category: Optional[str] = ""

# 爬取结果模型


class CrawlResult(BaseModel):
    status: str
    message: str
    statistics: Optional[Dict[str, Any]] = None
    result_count: Optional[int] = 0
    parsed_questions: Optional[int] = 0
    inserted_questions: Optional[int] = 0

# 搜索结果模型


class SearchResult(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total: int
    rerank_used: bool = False  # 是否使用了 Rerank


@app.post("/api/questions/ingest", summary="接收并存储面试题")
async def ingest_question(questions: List[InterviewQuestion]):
    """
    接收来自爬虫或大模型分析后的面试题列表，并存入向量数据库
    """
    try:
        # 转换为 VectorRecord
        records = []
        for q in questions:
            record = VectorRecord(
                id="",
                title=q.title,
                answer=q.answer,
                source_url=str(q.source_url),
                tags=q.tags,
                importance_score=q.importance_score or 0.0,
                difficulty=q.difficulty or "medium",
                category=q.category or "",
            )
            records.append(record)

        # 插入向量数据库
        count = await run_sync(vector_service.insert_questions, records)

        return {"status": "success", "count": count, "message": "数据已入库"}

    except Exception as e:
        logger.error(f"Ingest error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def run_crawler() -> Dict[str, Any]:
    """
    执行爬虫任务，并将结果存入向量数据库
    """
    global last_crawl_result

    logger.info("开始执行定时爬虫任务...")

    try:
        # 加载配置
        DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "crawler_config.json"

        if DEFAULT_CONFIG_PATH.exists():
            logger.info(f"使用默认配置文件: {DEFAULT_CONFIG_PATH}")
            config = CrawlerConfig.from_json(str(DEFAULT_CONFIG_PATH))
        else:
            config = get_config_from_env()

        # 从环境变量覆盖 Firecrawl 配置（确保最新配置生效）
        env_config = get_config_from_env()
        config.use_firecrawl = env_config.use_firecrawl
        config.firecrawl_api_url = env_config.firecrawl_api_url
        config.firecrawl_api_key = env_config.firecrawl_api_key
        config.firecrawl_timeout = env_config.firecrawl_timeout
        config.firecrawl_use_official = env_config.firecrawl_use_official
        config.firecrawl_only_main_content = env_config.firecrawl_only_main_content

        if not config.sitemap_url:
            logger.error("配置错误：未指定 Sitemap URL")
            return {"status": "error", "message": "未指定 Sitemap URL"}

        # 创建并运行爬虫
        crawler = SitemapCrawler(config=config)

        # 统计已插入的问题数量
        inserted_count = 0
        total_parsed_questions = 0

        # 定义页面处理回调函数（边扫描边解析）

        def on_page_processed(page_data):
            nonlocal total_parsed_questions
            try:
                logger.info(f"开始处理页面: {page_data.get('url', '')}")

                # 将单个页面数据转换为列表格式传给大模型
                page_list = [page_data]

                # 定义即时入库回调函数

                def on_question_found(questions):
                    nonlocal inserted_count
                    records = []
                    for q in questions:
                        record = VectorRecord(
                            id="",
                            title=q.title,
                            answer=q.answer,
                            source_url=q.source_url,
                            tags=q.tags,
                            importance_score=q.importance_score,
                            difficulty=q.difficulty,
                            category=q.category,
                        )
                        records.append(record)
                    count = vector_service.insert_questions(records)
                    inserted_count += count
                    logger.info(f"本页识别 {len(questions)} 个问题，已插入 {count} 个到向量数据库")

                # 调用大模型处理单个页面
                parsed_questions = llm_service.parse_crawl_results(
                    page_list, on_question_found=on_question_found
                )
                total_parsed_questions += len(parsed_questions)
                logger.info(f"页面处理完成，累计识别 {total_parsed_questions} 个问题")

            except Exception as e:
                logger.error(f"页面处理失败: {str(e)}")

        # 启动爬虫，传入页面处理回调
        results = crawler.crawl(page_processed_callback=on_page_processed)

        # 打印报告
        crawler.print_report()

        # 禁用本地保存结果，避免磁盘空间暴涨
        # if config.save_results:
        #     filepath = crawler.save_results()
        #     logger.info(f"结果已保存到: {filepath}")

        logger.info(
            f"解析出 {total_parsed_questions} 个面试问题，成功插入 {inserted_count} 个问题到向量数据库"
        )

        # 构建返回结果
        stats = crawler.statistics
        result = {
            "status": "success",
            "message": "爬取完成",
            "statistics": {
                "total_urls": stats.total_urls,
                "successful_scans": stats.successful_scans,
                "failed_scans": stats.failed_scans,
                "total_load_time": stats.total_load_time,
                "start_time": stats.start_time,
                "end_time": stats.end_time,
            },
            "result_count": len(results),
            "parsed_questions": total_parsed_questions,
            "inserted_questions": inserted_count,
        }

        # 更新全局变量
        last_crawl_result = result

        # 将结果存入 Redis，设置1天过期时间
        try:
            if vector_service.redis_client:
                result_json = json.dumps(result)
                vector_service.redis_client.setex(
                    "crawl:last_result", 86400, result_json  # 1天 = 86400秒
                )
                # 记录爬取时间
                import datetime

                crawl_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                vector_service.redis_client.setex(
                    "crawl:last_time", 86400, crawl_time  # 1天过期
                )
                logger.info("爬虫结果已存入 Redis")
        except Exception as e:
            logger.warning(f"存储爬虫结果到 Redis 失败: {str(e)}")

        logger.info(f"爬虫任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"爬虫任务失败: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/api/crawl/run", summary="手动触发爬虫任务")
async def trigger_crawl():
    """
    手动触发爬虫任务（同步，会阻塞直到完成）
    """
    try:
        result = run_crawler()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/crawl/run-async", summary="异步触发爬虫任务")
async def trigger_crawl_async():
    """
    异步触发爬虫任务（不阻塞，立即返回任务ID）
    """
    import uuid

    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 创建任务
        task = crawl_task_manager.create_task(task_id)

        # 在后台线程中执行爬虫任务

        def run_async_crawl():
            try:
                # 更新任务状态为运行中
                crawl_task_manager.update_task_status(
                    task_id,
                    TaskStatus.RUNNING,
                    start_time=datetime.now().isoformat()
                )

                # 加载配置
                DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "crawler_config.json"

                if DEFAULT_CONFIG_PATH.exists():
                    logger.info(f"使用默认配置文件: {DEFAULT_CONFIG_PATH}")
                    config = CrawlerConfig.from_json(str(DEFAULT_CONFIG_PATH))
                else:
                    config = get_config_from_env()

                # 从环境变量覆盖 Firecrawl 配置（确保最新配置生效）
                env_config = get_config_from_env()
                config.use_firecrawl = env_config.use_firecrawl
                config.firecrawl_api_url = env_config.firecrawl_api_url
                config.firecrawl_api_key = env_config.firecrawl_api_key
                config.firecrawl_timeout = env_config.firecrawl_timeout
                config.firecrawl_use_official = env_config.firecrawl_use_official
                config.firecrawl_only_main_content = env_config.firecrawl_only_main_content

                if not config.sitemap_url:
                    raise ValueError("未指定 Sitemap URL")

                # 创建爬虫
                crawler = SitemapCrawler(config=config)

                # 统计变量
                inserted_count = 0
                total_parsed_questions = 0

                # 定义页面处理回调函数

                def on_page_processed(page_data):
                    nonlocal total_parsed_questions
                    try:
                        # 检查是否应该停止
                        if task.stop_flag.is_set():
                            return

                        page_list = [page_data]

                        def on_question_found(questions):
                            nonlocal inserted_count
                            records = []
                            for q in questions:
                                record = VectorRecord(
                                    id="",
                                    title=q.title,
                                    answer=q.answer,
                                    source_url=q.source_url,
                                    tags=q.tags,
                                    importance_score=q.importance_score,
                                    difficulty=q.difficulty,
                                    category=q.category,
                                )
                                records.append(record)
                            count = vector_service.insert_questions(records)
                            inserted_count += count

                            # 更新任务进度
                            task.parsed_questions += len(questions)
                            task.inserted_questions = inserted_count

                        parsed_questions = llm_service.parse_crawl_results(
                            page_list, on_question_found=on_question_found
                        )
                        total_parsed_questions += len(parsed_questions)

                        # 更新已处理的URL数量
                        task.processed_urls += 1

                    except Exception as e:
                        logger.error(f"页面处理失败: {str(e)}")

                # 启动爬虫，传入停止标志和回调
                results = crawler.crawl(
                    page_processed_callback=on_page_processed,
                    stop_flag=task.stop_flag
                )

                # 检查是否是正常完成还是被中断
                if task.stop_flag.is_set():
                    # 任务被中断
                    crawl_task_manager.update_task_status(
                        task_id,
                        TaskStatus.STOPPED,
                        end_time=datetime.now().isoformat(),
                        error_message="任务被用户中断"
                    )
                    logger.info(f"任务 {task_id} 已被用户中断")

                    # 更新全局爬取状态到Redis
                    try:
                        if vector_service.redis_client:
                            stats = crawler.statistics
                            result = {
                                "status": "stopped",
                                "message": "任务被用户中断",
                                "statistics": {
                                    "total_urls": stats.total_urls,
                                    "successful_scans": stats.successful_scans,
                                    "failed_scans": stats.failed_scans,
                                    "total_load_time": stats.total_load_time,
                                    "start_time": stats.start_time,
                                    "end_time": stats.end_time,
                                },
                                "result_count": len(results),
                                "parsed_questions": total_parsed_questions,
                                "inserted_questions": inserted_count,
                            }
                            result_json = json.dumps(result)
                            vector_service.redis_client.setex(
                                "crawl:last_result", 86400, result_json
                            )
                            crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            vector_service.redis_client.setex(
                                "crawl:last_time", 86400, crawl_time
                            )
                            logger.info("已更新中断任务的全局状态到 Redis")
                    except Exception as e:
                        logger.warning(f"存储中断任务状态到 Redis 失败: {str(e)}")
                else:
                    # 任务正常完成
                    stats = crawler.statistics
                    task.total_urls = stats.total_urls
                    task.processed_urls = stats.successful_scans + stats.failed_scans
                    task.parsed_questions = total_parsed_questions
                    task.inserted_questions = inserted_count

                    result = {
                        "status": "success",
                        "message": "爬取完成",
                        "statistics": {
                            "total_urls": stats.total_urls,
                            "successful_scans": stats.successful_scans,
                            "failed_scans": stats.failed_scans,
                            "total_load_time": stats.total_load_time,
                            "start_time": stats.start_time,
                            "end_time": stats.end_time,
                        },
                        "result_count": len(results),
                        "parsed_questions": total_parsed_questions,
                        "inserted_questions": inserted_count,
                    }

                    crawl_task_manager.update_task_status(
                        task_id,
                        TaskStatus.COMPLETED,
                        end_time=datetime.now().isoformat(),
                        result=result
                    )
                    logger.info(f"任务 {task_id} 已完成")

                    # 更新全局爬取状态到Redis
                    try:
                        if vector_service.redis_client:
                            result_json = json.dumps(result)
                            vector_service.redis_client.setex(
                                "crawl:last_result", 86400, result_json
                            )
                            crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            vector_service.redis_client.setex(
                                "crawl:last_time", 86400, crawl_time
                            )
                            logger.info("已更新全局爬取状态到 Redis")
                    except Exception as e:
                        logger.warning(f"存储爬虫结果到 Redis 失败: {str(e)}")

            except Exception as e:
                logger.error(f"任务 {task_id} 执行失败: {str(e)}")
                crawl_task_manager.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    end_time=datetime.now().isoformat(),
                    error_message=str(e)
                )

        # 启动后台线程
        thread = Thread(target=run_async_crawl, daemon=True)
        thread.start()

        return {
            "status": "accepted",
            "message": "爬虫任务已启动",
            "task_id": task_id
        }

    except Exception as e:
        logger.error(f"启动异步爬虫任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/crawl/task/{task_id}", summary="获取爬虫任务状态")
async def get_crawl_task_status(task_id: str):
    """
    获取指定爬虫任务的状态
    """
    task = crawl_task_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task.to_dict()


@app.post("/api/crawl/stop/{task_id}", summary="停止爬虫任务")
async def stop_crawl_task(task_id: str):
    """
    停止正在运行的爬虫任务
    """
    success = crawl_task_manager.stop_task(task_id)

    if not success:
        raise HTTPException(status_code=400, detail="无法停止任务（可能已完成或不存在）")

    return {
        "status": "success",
        "message": "已请求停止任务",
        "task_id": task_id
    }


@app.get("/api/crawl/tasks", summary="获取所有爬虫任务")
async def get_all_crawl_tasks():
    """
    获取所有爬虫任务的状态
    """
    return crawl_task_manager.get_all_tasks()


@app.get("/api/crawl/status", summary="获取爬虫状态")
async def get_crawl_status():
    """
    获取爬虫状态（包括调度配置、下次运行时间、上次爬取结果）
    """
    status_info = {
        "status": "idle",
        "message": "等待调度任务执行或手动触发",
        "scheduler_config": {
            "hour": SCHEDULER_HOUR,
            "minute": SCHEDULER_MINUTE,
            "next_run": None,
        },
        "last_crawl": None,
    }

    # 获取下次调度时间
    try:
        if scheduler:
            jobs = scheduler.get_jobs()
            if jobs:
                job = jobs[0]
                # APScheduler 3.x 使用 next_run_time 属性
                # APScheduler 4.x 可能需要不同的访问方式
                next_run = getattr(job, 'next_run_time', None)
                if next_run:
                    status_info["scheduler_config"]["next_run"] = next_run.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
    except Exception as e:
        logger.warning(f"获取调度信息失败: {str(e)}")

    # 检查上次爬取结果
    try:
        if vector_service.redis_client:
            last_result = vector_service.redis_client.get("crawl:last_result")
            last_time = vector_service.redis_client.get("crawl:last_time")

            if last_result:
                # 处理字节类型
                if isinstance(last_result, bytes):
                    result_json = last_result.decode("utf-8")
                else:
                    result_json = str(last_result)

                result_data = json.loads(result_json)
                status_info["last_crawl"] = {
                    "timestamp": (
                        last_time.decode("utf-8")
                        if isinstance(last_time, bytes)
                        else str(last_time) if last_time else None
                    ),
                    "statistics": result_data.get("statistics", {}),
                    "result_count": result_data.get("result_count", 0),
                    "parsed_questions": result_data.get("parsed_questions", 0),
                    "inserted_questions": result_data.get("inserted_questions", 0),
                }
                status_info["status"] = "completed"
                status_info["message"] = "上次爬取已完成"

            # 如果没有结果但有调度配置，显示即将运行的信息
            if (
                    status_info["status"] == "idle"
                    and status_info["scheduler_config"]["next_run"]
            ):
                status_info["message"] = (
                    f"等待下次调度运行（预计 {status_info['scheduler_config']['next_run']}）"
                )
    except Exception as e:
        logger.warning(f"从 Redis 读取爬虫状态失败: {str(e)}")

    # 备用：从全局变量读取
    if status_info["last_crawl"] is None and last_crawl_result is not None:
        status_info["last_crawl"] = {
            "statistics": last_crawl_result.get("statistics", {}),
            "result_count": last_crawl_result.get("result_count", 0),
            "parsed_questions": last_crawl_result.get("parsed_questions", 0),
            "inserted_questions": last_crawl_result.get("inserted_questions", 0),
        }
        status_info["status"] = "completed"
        status_info["message"] = "上次爬取已完成"

    return status_info


@app.get("/api/questions/search", summary="搜索面试题")
async def search_questions(
        query: str,
        limit: int = Query(10, ge=1, le=100),
        tags: Optional[List[str]] = Query(None),
        difficulty: Optional[List[str]] = Query(None),
        category: Optional[List[str]] = Query(None),
        search_mode: str = Query("hybrid", pattern="^(semantic|exact|hybrid)$"),
        use_rerank: bool = Query(True, description="是否使用 Rerank 模型重排序搜索结果（默认开启，自动降级）"),
):
    """
    根据关键词搜索面试题

    参数:
        query: 搜索关键词
        limit: 返回数量限制
        tags: 标签过滤（如：Python,算法）
        difficulty: 难度过滤（easy/medium/hard）
        category: 分类过滤
        search_mode: 搜索模式（semantic=语义搜索, exact=精确搜索, hybrid=混合搜索）
        use_rerank: 是否使用 Rerank 模型对搜索结果进行重排序（默认True，后端会自动降级）
    """
    try:
        # 构建过滤条件
        filters = {}
        if tags:
            filters["tags"] = tags
        if difficulty:
            filters["difficulty"] = difficulty
        if category:
            filters["category"] = category

        # 根据搜索模式执行不同的搜索策略
        if search_mode == "semantic":
            # 纯语义搜索（向量相似度）
            results = await run_sync(vector_service.search, query, limit, filters if filters else None)
            logger.info(f"语义搜索: '{query}' -> {len(results)} 个结果")

        elif search_mode == "exact":
            # 纯精确搜索（关键词匹配）
            results = await run_sync(vector_service.exact_search, query, limit, filters if filters else None)
            logger.info(f"精确搜索: '{query}' -> {len(results)} 个结果")

        elif search_mode == "hybrid":
            # 混合搜索：结合语义和精确搜索结果（并行执行）
            semantic_results, exact_results = await asyncio.gather(
                run_sync(vector_service.search, query, limit * 2, filters if filters else None),
                run_sync(vector_service.exact_search, query, limit * 2, filters if filters else None),
            )

            # 合并结果并去重（优先保留精确匹配的高分结果）
            merged_results = vector_service.merge_search_results(
                semantic_results, exact_results, limit
            )
            results = merged_results
            logger.info(f"混合搜索: '{query}' -> {len(results)} 个结果 (语义:{len(semantic_results)}, 精确:{len(exact_results)})")

        else:
            raise HTTPException(status_code=400, detail=f"不支持的搜索模式: {search_mode}")

        # 如果启用 Rerank，对搜索结果进行重排序
        rerank_success = False
        if use_rerank and feedback_service.rerank_enabled and results:
            try:
                reranked_results = await run_sync(
                    feedback_service.rerank_questions, query, results, limit
                )
                results = reranked_results
                rerank_success = True
                logger.info(f"Rerank 重排序完成: '{query}' -> {len(results)} 个结果")
            except Exception as e:
                logger.warning(f"Rerank 失败，使用原始搜索结果: {str(e)}")
                # Rerank 失败不影响搜索结果，继续使用原始结果
        
        # 为每个结果添加反馈信息（用于前端标记）
        for result in results:
            feedback = feedback_service.get_feedback(result['id'])
            if feedback:
                result['mastery_level'] = feedback.mastery_level
                result['is_favorite'] = feedback.is_favorite
                result['is_wrong_book'] = feedback.is_wrong_book
                result['hide_from_recommendation'] = feedback.hide_from_recommendation
                
                # 如果题目被隐藏，添加提示信息
                if feedback_service.should_exclude_from_recommendation(result['id']):
                    result['status_hint'] = '已掌握' if feedback.mastery_level >= 5 else '低优先级'

        return SearchResult(query=query, results=results, total=len(results), rerank_used=rerank_success)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/questions/count", summary="获取面试题总数")
async def get_question_count():
    """
    获取向量数据库中面试题的总数
    """
    try:
        count = await run_sync(vector_service.count)
        return {"count": count}
    except Exception as e:
        logger.error(f"Count error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/questions/generate-batch", summary="批量生成面试题")
async def generate_batch_questions(
        count: int = Query(10, ge=1, le=50),
        difficulty: Optional[str] = Query(None),
        category: Optional[str] = Query(None),
        tags: Optional[List[str]] = Query(None)
):
    """
    从向量数据库中随机获取指定条件的面试题

    参数:
        count: 题目数量 (1-50)
        difficulty: 难度过滤 (easy/medium/hard)
        category: 分类过滤
        tags: 标签过滤
    """
    logger.info(f"收到批量生成请求: count={count}, difficulty={difficulty}, category={category}, tags={tags}")
    try:
        # 获取所有题目
        all_questions = await run_sync(vector_service.get_all)
        logger.info(f"从向量数据库获取到 {len(all_questions)} 个问题")

        if not all_questions:
            logger.warning("数据库中没有面试题")
            raise HTTPException(status_code=404, detail="数据库中没有面试题")

        # 过滤条件
        filtered_questions = all_questions

        if difficulty:
            filtered_questions = [q for q in filtered_questions if q.get('difficulty') == difficulty]
            logger.info(f"按难度 '{difficulty}' 过滤后剩余 {len(filtered_questions)} 个问题")

        if category:
            filtered_questions = [q for q in filtered_questions if q.get('category') == category]
            logger.info(f"按分类 '{category}' 过滤后剩余 {len(filtered_questions)} 个问题")

        if tags:
            filtered_questions = [
                q for q in filtered_questions
                if any(tag in q.get('tags', []) for tag in tags)
            ]
            logger.info(f"按标签 {tags} 过滤后剩余 {len(filtered_questions)} 个问题")

        if not filtered_questions:
            logger.warning("没有找到符合条件的面试题")
            raise HTTPException(status_code=404, detail="没有找到符合条件的面试题")

        # 随机选择指定数量的题目
        import random
        selected_questions = random.sample(
            filtered_questions,
            min(count, len(filtered_questions))
        )

        logger.info(f"成功生成 {len(selected_questions)} 道面试题")
        return {
            "status": "success",
            "count": len(selected_questions),
            "questions": selected_questions
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量生成面试题失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/questions/generate", summary="使用大模型生成答案")
async def generate_answer(question: str):
    """
    使用大模型为给定问题生成答案
    """
    try:
        answer = await run_sync(llm_service.generate_answer, question)
        return {"question": question, "answer": answer}
    except Exception as e:
        logger.error(f"Generate answer error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/questions/recommended", summary="智能推荐题目")
async def get_recommended_questions(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    exclude_mastered: bool = Query(True, description="是否排除已掌握的题目"),
    use_rerank: bool = Query(True, description="是否使用 Rerank 模型重排序（默认开启，自动降级）")
):
    """
    基于用户反馈和艾宾浩斯曲线智能推荐题目

    参数:
        limit: 返回数量
        exclude_mastered: 是否排除完全掌握的题目（mastery_level=5）
        use_rerank: 是否使用 Rerank 模型进行重排序（默认True，后端会自动降级）
    """
    try:
        # 获取所有题目
        all_questions = await run_sync(vector_service.get_all)

        if not all_questions:
            return {"questions": [], "total": 0}

        # 计算每个题目的优先级分数
        scored_questions = []
        for question in all_questions:
            feedback = feedback_service.get_feedback(question['id'])

            # 排除已掌握的题目
            if exclude_mastered and feedback and feedback.mastery_level >= 5:
                continue
            
            # 排除从推荐中隐藏的题目（软删除）
            if feedback and feedback_service.should_exclude_from_recommendation(question['id']):
                continue

            priority_score = feedback_service.calculate_priority_score(question, feedback)

            scored_questions.append({
                **question,
                "priority_score": priority_score,
                "mastery_level": feedback.mastery_level if feedback else 0,
                "is_favorite": feedback.is_favorite if feedback else False,
                "is_wrong_book": feedback.is_wrong_book if feedback else False,
                "hide_from_recommendation": feedback.hide_from_recommendation if feedback else False
            })

        # 按优先级分数降序排序
        scored_questions.sort(key=lambda x: x['priority_score'], reverse=True)

        # 如果启用 Rerank，先取更多候选，然后重排序
        rerank_success = False
        if use_rerank and feedback_service.rerank_enabled:
            try:
                # 取 3 倍数量的候选题目，增加随机性避免每次都是同样的题
                import random
                candidate_pool_size = min(limit * 5, len(scored_questions))
                candidate_pool = scored_questions[:candidate_pool_size]
                # 从候选池中随机抽样
                candidate_count = min(limit * 3, len(candidate_pool))
                candidates = random.sample(candidate_pool, candidate_count)

                # 构建用户画像（简化版：基于用户的错题本和收藏）
                user_profile = "我需要复习以下类型的面试题"
                wrong_books = feedback_service.get_wrong_book()
                favorites = feedback_service.get_favorites()

                if wrong_books or favorites:
                    # 如果有错题或收藏，可以构建更精确的用户画像
                    user_profile += (
                        f"（共 {len(wrong_books)} 道错题，{len(favorites)} 道收藏）"
                    )

                # 执行 Rerank
                reranked = await run_sync(
                    feedback_service.rerank_questions,
                    user_profile, candidates, limit
                )
                recommended = reranked
                rerank_success = True
                logger.info(f"推荐接口 Rerank 成功，返回 {len(recommended)} 道题目")
            except Exception as e:
                logger.warning(f"Rerank 失败，降级为默认排序: {str(e)}")
                # Rerank 失败，降级为默认排序（带随机性）
                import random
                candidate_pool_size = min(limit * 3, len(scored_questions))
                candidate_pool = scored_questions[:candidate_pool_size]
                random.shuffle(candidate_pool)
                recommended = candidate_pool[:limit]
        else:
            # 直接返回前 limit 个（带随机性，从候选池中随机抽样）
            import random
            candidate_pool_size = min(limit * 3, len(scored_questions))
            candidate_pool = scored_questions[:candidate_pool_size]
            random.shuffle(candidate_pool)
            recommended = candidate_pool[:limit]

        return {
            "questions": recommended,
            "total": len(recommended),
            "rerank_used": rerank_success
        }

    except Exception as e:
        logger.error(f"Get recommended questions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/questions/{question_id}", summary="获取单个面试题详情")
async def get_question(question_id: str):
    """
    根据 ID 获取面试题详情
    """
    try:
        question = vector_service.get_by_id(question_id)

        if not question:
            raise HTTPException(status_code=404, detail="问题不存在")

        return question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get question error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/questions/{question_id}/importance", summary="更新题目重要性")
async def update_question_importance(question_id: str, importance_score: float = Query(..., ge=0, le=1, description="重要性评分 0-1")):
    """
    更新题目的重要性评分（用户自定义）
    
    参数:
        question_id: 题目ID
        importance_score: 新的重要性评分 (0-1)
    """
    try:
        # 获取题目
        question = vector_service.get_by_id(question_id)
        if not question:
            raise HTTPException(status_code=404, detail="题目不存在")
        
        # 更新重要性评分
        question['importance_score'] = importance_score
        
        # 保存回向量数据库
        success = vector_service.update(question_id, question)
        
        if not success:
            raise HTTPException(status_code=500, detail="更新失败")
        
        return {
            "status": "success",
            "message": "重要性已更新",
            "importance_score": importance_score
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update importance error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/questions/{question_id}", summary="删除面试题")
async def delete_question(question_id: str):
    """
    删除指定的面试题
    """
    try:
        success = vector_service.delete_by_id(question_id)

        if not success:
            raise HTTPException(status_code=404, detail="问题不存在")

        return {"status": "success", "message": "删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete question error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 用户反馈相关 API (RESTful) ====================


@app.post("/api/questions/{question_id}/feedback", summary="提交题目反馈")
async def submit_feedback(
    question_id: str,
    mastery_level: Optional[int] = Query(None, ge=0, le=5, description="掌握程度 0-5"),
    is_favorite: Optional[bool] = Query(None, description="是否收藏"),
    is_wrong_book: Optional[bool] = Query(None, description="是否加入错题本"),
    hide_from_recommendation: Optional[bool] = Query(None, description="是否从推荐中隐藏（软删除）")
):
    """
    提交题目反馈

    参数:
        question_id: 题目ID
        mastery_level: 掌握程度 (0-5)，0=未学习，5=完全掌握
        is_favorite: 是否收藏
        is_wrong_book: 是否加入错题本
        hide_from_recommendation: 是否从推荐中隐藏（达到条件时自动或手动）
    """
    try:
        feedback_data = {}
        if mastery_level is not None:
            feedback_data['mastery_level'] = mastery_level
        if is_favorite is not None:
            feedback_data['is_favorite'] = is_favorite
        if is_wrong_book is not None:
            feedback_data['is_wrong_book'] = is_wrong_book
        if hide_from_recommendation is not None:
            feedback_data['hide_from_recommendation'] = hide_from_recommendation

        if not feedback_data:
            raise HTTPException(status_code=400, detail="至少提供一个反馈字段")

        success = feedback_service.submit_feedback(question_id, feedback_data)

        if not success:
            raise HTTPException(status_code=500, detail="提交反馈失败")
        
        # 获取更新后的反馈和题目数据，返回给前端
        feedback = feedback_service.get_feedback(question_id)
        question = vector_service.get_by_id(question_id)
        
        response_data = {"status": "success", "message": "反馈已保存"}
        
        if feedback and question:
            # 从题目数据中获取重要性评分
            importance_score = question.get('importance_score', 0.5)
            
            # 检查是否需要弹窗确认
            auto_hide_result = feedback_service.should_auto_hide(
                feedback.mastery_level, 
                importance_score
            )
            response_data['auto_hide'] = auto_hide_result
            response_data['feedback'] = {
                'mastery_level': feedback.mastery_level,
                'hide_from_recommendation': feedback.hide_from_recommendation
            }
            response_data['question_importance'] = importance_score
            
            # 计算下次出现时间
            next_days = feedback_service.calculate_next_appearance_days(
                feedback.mastery_level,
                importance_score
            )
            response_data['next_appearance_days'] = next_days

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Submit feedback error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/questions/{question_id}/feedback", summary="获取题目反馈")
async def get_question_feedback(question_id: str):
    """
    获取指定题目的用户反馈
    """
    try:
        feedback = feedback_service.get_feedback(question_id)

        if not feedback:
            return {
                "question_id": question_id,
                "has_feedback": False
            }

        return {
            "question_id": question_id,
            "has_feedback": True,
            "feedback": {
                "mastery_level": feedback.mastery_level,
                "is_favorite": feedback.is_favorite,
                "is_wrong_book": feedback.is_wrong_book,
                "hide_from_recommendation": feedback.hide_from_recommendation,
                "hidden_at": feedback.hidden_at
            }
        }

    except Exception as e:
        logger.error(f"Get feedback error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/me/favorites", summary="获取我的收藏列表")
async def get_favorites():
    """
    获取收藏的题目列表（带完整题目信息）
    """
    try:
        favorite_ids = await run_sync(feedback_service.get_favorites)

        if not favorite_ids:
            return {"questions": [], "total": 0}

        # 获取所有题目
        all_questions = await run_sync(vector_service.get_all)
        favorites = [q for q in all_questions if q['id'] in favorite_ids]

        return {
            "questions": favorites,
            "total": len(favorites)
        }

    except Exception as e:
        logger.error(f"Get favorites error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/users/me/favorites/{question_id}", summary="取消收藏")
async def remove_from_favorites(question_id: str):
    """
    从收藏中移除题目
    """
    try:
        success = await run_sync(feedback_service.remove_from_collection, question_id, 'favorite')

        if not success:
            raise HTTPException(status_code=500, detail="操作失败")

        return {"status": "success", "message": "已取消收藏"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Remove from favorites error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/me/wrong-books", summary="获取我的错题本")
async def get_wrong_book():
    """
    获取错题本中的题目列表（带完整题目信息）
    """
    try:
        wrong_book_ids = await run_sync(feedback_service.get_wrong_book)

        if not wrong_book_ids:
            return {"questions": [], "total": 0}

        # 获取所有题目
        all_questions = await run_sync(vector_service.get_all)
        wrong_books = [q for q in all_questions if q['id'] in wrong_book_ids]

        return {
            "questions": wrong_books,
            "total": len(wrong_books)
        }

    except Exception as e:
        logger.error(f"Get wrong book error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/users/me/wrong-books/{question_id}", summary="从错题本移除")
async def remove_from_wrong_book(question_id: str):
    """
    从错题本中移除题目
    """
    try:
        success = await run_sync(feedback_service.remove_from_collection, question_id, 'wrong_book')

        if not success:
            raise HTTPException(status_code=500, detail="操作失败")

        return {"status": "success", "message": "已从错题本移除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Remove from wrong book error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/questions/{question_id}", summary="删除题目（软删除）")
async def delete_question(question_id: str):
    """
    删除题目（软删除，保留30天）
    
    删除后的题目：
    - 不会出现在推荐列表中
    - 搜索时仍会出现，但标记为“已掌握”或“低优先级”
    - Rerank排序时会靠后
    - 30天后自动恢复
    """
    try:
        success = await run_sync(feedback_service.delete_question_feedback, question_id)

        if not success:
            raise HTTPException(status_code=500, detail="删除失败")

        return {
            "status": "success",
            "message": "题目已删除（30天后可恢复）"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete question error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/me/hidden-questions", summary="获取已掌握（软删除）的题目")
async def get_hidden_questions():
    """
    获取已隐藏（软删除）的题目列表
    这些题目可以在这里进行永久删除
    """
    try:
        hidden_ids = await run_sync(feedback_service.get_hidden_questions)

        if not hidden_ids:
            return {"questions": [], "total": 0}

        # 获取所有题目
        all_questions = await run_sync(vector_service.get_all)
        hidden_questions = [q for q in all_questions if q['id'] in hidden_ids]

        return {
            "questions": hidden_questions,
            "total": len(hidden_questions)
        }

    except Exception as e:
        logger.error(f"Get hidden questions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/users/me/hidden-questions/{question_id}", summary="永久删除题目")
async def permanently_delete_question(question_id: str):
    """
    永久删除题目（从向量数据库中删除）
    只能在“已掌握”列表中操作
    """
    try:
        # 先从反馈中删除
        key = feedback_service._get_feedback_key(question_id)
        if feedback_service.redis_client:
            feedback_service.redis_client.delete(key)
        
        # 再从向量数据库中删除
        success = await run_sync(vector_service.delete_by_id, question_id)

        if not success:
            raise HTTPException(status_code=404, detail="题目不存在")

        return {
            "status": "success",
            "message": "题目已永久删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Permanently delete question error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/weights/update", summary="手动更新权重")
async def update_weights():
    """
    手动触发权重更新任务（基于艾宾浩斯曲线）
    """
    try:
        updated_count = await run_sync(feedback_service.update_all_weights)

        return {
            "status": "success",
            "message": f"已更新 {updated_count} 个题目的权重",
            "updated_count": updated_count
        }

    except Exception as e:
        logger.error(f"Update weights error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/questions", summary="获取所有面试题")
async def get_all_questions(
        limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)
):
    """
    获取所有面试题列表（分页）
    """
    try:
        # 获取所有题目
        all_questions = await run_sync(vector_service.get_all)

        # 简单分页
        total = len(all_questions)
        paginated = all_questions[offset: offset + limit]

        return {
            "questions": paginated,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Get all questions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/debug/vector-status", summary="调试：查看向量数据库状态")
async def debug_vector_status():
    """
    调试接口：查看向量数据库的状态，包括索引信息和样本数据
    """
    try:
        status = {
            "redis_connected": vector_service.redis_client is not None,
            "index_name": vector_service.index_name,
        }

        if vector_service.redis_client:
            # 检查索引信息
            try:
                index_info = vector_service.redis_client.ft(vector_service.index_name).info()
                status["index_info"] = index_info
            except Exception as e:
                status["index_error"] = str(e)

            # 获取问题总数
            status["question_count"] = vector_service.count()

            # 获取所有键
            keys = vector_service.redis_client.keys("question:*")
            status["total_keys"] = len(keys)

            # 获取前3个问题作为样本
            if keys:
                sample_questions = []
                for key in keys[:3]:
                    data = vector_service.redis_client.hgetall(key)
                    question_id = key.decode().replace("question:", "")
                    sample_questions.append({
                        "id": question_id,
                        "title": data.get(b"title", b"").decode(),
                        "has_embedding": b"embedding" in data,
                        "embedding_size": len(data.get(b"embedding", b"")) if b"embedding" in data else 0,
                    })
                status["sample_questions"] = sample_questions

        return status
    except Exception as e:
        logger.error(f"Debug vector status error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/debug/reset-index", summary="调试：重置向量索引")
async def reset_vector_index():
    """
    调试接口：删除旧索引和所有数据，以便重新创建
    """
    try:
        if not vector_service.redis_client:
            raise HTTPException(status_code=500, detail="Redis未连接")

        # 1. 删除所有问题数据
        keys = vector_service.redis_client.keys("question:*")
        deleted_count = 0
        if keys:
            deleted_count = vector_service.redis_client.delete(*keys)

        # 2. 删除索引
        try:
            vector_service.redis_client.ft(vector_service.index_name).dropindex(delete_documents=True)
            logger.info(f"已删除索引 {vector_service.index_name}")
        except Exception as e:
            logger.warning(f"删除索引失败（可能不存在）: {str(e)}")

        return {
            "status": "success",
            "message": "索引和数据已清空",
            "deleted_keys": deleted_count
        }
    except Exception as e:
        logger.error(f"Reset index error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/debug/merge-duplicates", summary="调试：合并重复问题")
async def merge_duplicate_questions(
        similarity_threshold: float = Query(0.85, ge=0.0, le=1.0, description="相似度阈值"),
        dry_run: bool = Query(False, description="是否仅模拟运行（不实际合并）")
):
    """
    调试接口：检测并合并相似问题

    参数:
        similarity_threshold: 相似度阈值（0-1），默认0.85
        dry_run: 是否仅模拟运行，不实际合并

    返回:
        合并统计信息
    """
    try:
        if not vector_service.redis_client:
            raise HTTPException(status_code=500, detail="Redis未连接")

        logger.info(f"开始检测重复问题（相似度阈值: {similarity_threshold}, 模拟运行: {dry_run}）")

        # 获取所有问题
        all_questions = vector_service.get_all()
        total_questions = len(all_questions)

        if total_questions == 0:
            return {
                "status": "success",
                "message": "没有需要处理的问题",
                "total_questions": 0,
                "merged_count": 0,
                "details": []
            }

        logger.info(f"共有 {total_questions} 个问题需要检查")

        # 统计信息
        merged_count = 0
        details = []
        processed_ids = set()

        # 遍历所有问题，检查是否有相似问题
        for i, question in enumerate(all_questions):
            if question['id'] in processed_ids:
                continue

            # 每10个问题打印进度
            if (i + 1) % 10 == 0:
                logger.info(f"进度: {i + 1}/{total_questions}")

            # 查找相似问题（排除自己）
            similar = vector_service._find_most_similar_question(
                question['title'],
                similarity_threshold
            )

            if similar and similar['id'] != question['id'] and similar['id'] not in processed_ids:
                # 找到相似问题
                detail = {
                    "original": {
                        "id": question['id'],
                        "title": question['title'],
                        "source_url": question['source_url']
                    },
                    "similar": {
                        "id": similar['id'],
                        "title": similar['title'],
                        "score": similar['score']
                    }
                }

                if not dry_run:
                    # 实际执行合并
                    # 构建 VectorRecord
                    from app.services.vector_service import VectorRecord
                    new_question = VectorRecord(
                        id="",
                        title=question['title'],
                        answer=question['answer'],
                        source_url=question['source_url'],
                        tags=question['tags'],
                        importance_score=question['importance_score'],
                        difficulty=question['difficulty'],
                        category=question['category']
                    )

                    success = vector_service._merge_into_existing_question(
                        similar['id'],
                        new_question
                    )

                    if success:
                        merged_count += 1
                        processed_ids.add(question['id'])
                        detail["action"] = "merged"
                        detail["message"] = f"已合并到: {similar['title']}"
                    else:
                        detail["action"] = "failed"
                        detail["message"] = "合并失败"
                else:
                    detail["action"] = "would_merge"
                    detail["message"] = f"将合并到: {similar['title']}"

                details.append(detail)

        result = {
            "status": "success",
            "message": "重复问题检测完成",
            "total_questions": total_questions,
            "merged_count": merged_count if not dry_run else len(details),
            "similarity_threshold": similarity_threshold,
            "dry_run": dry_run,
            "details": details[:50]  # 最多返回50条详细信息
        }

        logger.info(f"重复问题处理完成: 总计 {total_questions}, 合并 {merged_count}")
        return result

    except Exception as e:
        logger.error(f"Merge duplicates error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/crawl/single-page", summary="智能爬取单个页面")
async def crawl_single_page(url: str):
    """
    智能爬取单个页面，识别其中的面试问题并存入向量数据库

    参数:
        url: 要爬取的页面URL
    """
    try:
        from app.services.url_scanner import URLScanner
        from app.services.vector_service import VectorRecord
        import time

        start_time = time.time()
        logger.info(f"开始爬取单个页面: {url}")

        # 1. 扫描页面
        logger.info("步骤1: 正在扫描页面...")

        # 从配置中读取 Firecrawl 设置
        from app.config.crawler_config import get_config_from_env
        crawler_config = get_config_from_env()

        scanner = URLScanner(
            timeout=crawler_config.timeout,
            follow_redirects=crawler_config.follow_redirects,
            verify_ssl=crawler_config.verify_ssl,
            max_content_length=crawler_config.max_content_length,
            use_firecrawl=crawler_config.use_firecrawl,
            firecrawl_api_url=crawler_config.firecrawl_api_url,
            firecrawl_api_key=crawler_config.firecrawl_api_key,
            firecrawl_timeout=crawler_config.firecrawl_timeout,
            firecrawl_use_official=crawler_config.firecrawl_use_official,
            firecrawl_only_main_content=crawler_config.firecrawl_only_main_content,
        )
        scan_result = scanner.scan(url)

        if scan_result.error:
            raise HTTPException(status_code=400, detail=f"页面扫描失败: {scan_result.error}")

        logger.info(f"页面扫描成功: {scan_result.title}, 内容长度: {len(scan_result.text_content or '')} 字符")

        # 2. 构建页面数据
        page_data = {
            "url": url,
            "title": scan_result.title or "",
            "text_content": scan_result.text_content or "",
            "html_content": scan_result.html_content or "",
        }

        # 3. 使用大模型解析页面内容
        inserted_count = 0
        parsed_questions = []
        processing_steps = [
            {"step": 1, "message": "页面扫描完成", "progress": 20},
        ]

        def on_question_found(questions):
            nonlocal inserted_count
            records = []
            for q in questions:
                record = VectorRecord(
                    id="",
                    title=q.title,
                    answer=q.answer,
                    source_url=q.source_url,
                    tags=q.tags,
                    importance_score=q.importance_score,
                    difficulty=q.difficulty,
                    category=q.category,
                )
                records.append(record)
            count = vector_service.insert_questions(records)
            inserted_count += count
            logger.info(f"识别到 {len(questions)} 个问题，已插入 {count} 个到向量数据库")

        # 调用大模型处理单个页面
        logger.info("步骤2: 正在使用AI识别面试问题...")
        processing_steps.append({"step": 2, "message": "正在分析页面内容...", "progress": 40})

        parsed_questions = llm_service.parse_crawl_results(
            [page_data], on_question_found=on_question_found
        )

        processing_steps.append({"step": 3, "message": "问题识别完成", "progress": 80})
        processing_steps.append({"step": 4, "message": "正在存入向量数据库...", "progress": 90})

        end_time = time.time()
        total_time = end_time - start_time

        result = {
            "status": "success",
            "message": "页面爬取完成",
            "url": url,
            "title": scan_result.title,
            "parsed_questions": len(parsed_questions),
            "inserted_questions": inserted_count,
            "word_count": scan_result.word_count,
            "load_time": scan_result.load_time,
            "total_processing_time": round(total_time, 2),
            "processing_steps": processing_steps,
        }

        logger.info(f"单页爬取完成: {result}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"单页爬取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/crawl/single-page/stream", summary="单页爬取实时日志流")
async def crawl_single_page_stream(url: str):
    """
    SSE流式接口：实时推送单页爬取的日志和进度

    参数:
        url: 要爬取的页面URL
    """
    from app.services.url_scanner import URLScanner
    from app.services.vector_service import VectorRecord
    import time

    # 创建唯一的会话ID
    import uuid
    session_id = str(uuid.uuid4())

    # 为此会话创建日志队列
    log_queue = Queue()
    sse_log_queues[session_id] = log_queue

    async def event_generator():
        try:
            start_time = time.time()

            # 发送初始状态
            yield f"data: {json.dumps({'type': 'start', 'message': '开始爬取', 'progress': 0})}\n\n"

            # 定义日志回调函数

            def log_callback(message: str, progress: int, step: str = "info"):
                log_data = {
                    "type": "log",
                    "message": message,
                    "progress": progress,
                    "step": step,
                    "timestamp": time.time()
                }
                log_queue.put(json.dumps(log_data))

            # 在后台线程中执行爬取任务

            def run_crawl():
                try:
                    log_callback("正在扫描页面...", 10, "scanning")

                    # 1. 扫描页面
                    from app.config.crawler_config import get_config_from_env
                    crawler_config = get_config_from_env()

                    scanner = URLScanner(
                        timeout=crawler_config.timeout,
                        follow_redirects=crawler_config.follow_redirects,
                        verify_ssl=crawler_config.verify_ssl,
                        max_content_length=crawler_config.max_content_length,
                        use_firecrawl=crawler_config.use_firecrawl,
                        firecrawl_api_url=crawler_config.firecrawl_api_url,
                        firecrawl_api_key=crawler_config.firecrawl_api_key,
                        firecrawl_timeout=crawler_config.firecrawl_timeout,
                        firecrawl_use_official=crawler_config.firecrawl_use_official,
                        firecrawl_only_main_content=crawler_config.firecrawl_only_main_content,
                    )
                    scan_result = scanner.scan(url)

                    if scan_result.error:
                        log_callback(f"页面扫描失败: {scan_result.error}", 0, "error")
                        log_queue.put("ERROR")
                        return

                    log_callback(f"页面扫描成功: {scan_result.title}", 20, "scanned")
                    log_callback(f"内容长度: {len(scan_result.text_content or '')} 字符", 25, "info")

                    # 2. 构建页面数据
                    page_data = {
                        "url": url,
                        "title": scan_result.title or "",
                        "text_content": scan_result.text_content or "",
                        "html_content": scan_result.html_content or "",
                    }

                    # 3. 使用大模型解析
                    inserted_count = 0

                    def on_question_found(questions):
                        nonlocal inserted_count
                        records = []
                        for q in questions:
                            record = VectorRecord(
                                id="",
                                title=q.title,
                                answer=q.answer,
                                source_url=q.source_url,
                                tags=q.tags,
                                importance_score=q.importance_score,
                                difficulty=q.difficulty,
                                category=q.category,
                            )
                            records.append(record)
                        count = vector_service.insert_questions(records)
                        inserted_count += count
                        log_callback(f"识别到 {len(questions)} 个问题，已插入 {count} 个", 75, "inserting")

                    log_callback("正在使用AI识别面试问题...", 30, "analyzing")

                    # 临时重定向日志输出到SSE（推送所有日志）
        # original_handlers = logger.handlers.copy()

                    class SSELogHandler(logging.Handler):

                        def emit(self, record):
                            try:
                                # 获取格式化的日志消息
                                log_message = self.format(record)

                                # 根据日志级别确定类型和进度
                                if record.levelno >= logging.ERROR:
                                    log_type = "error"
                                    progress = 0
                                elif record.levelno >= logging.WARNING:
                                    log_type = "warning"
                                    progress = 50
                                else:  # INFO and DEBUG
                                    log_type = "info"
                                    # 对于INFO级别，尝试从日志内容推断进度
                                    progress = 50  # 默认进度

                                    # 根据关键词估算进度
                                    if "扫描" in log_message or "scan" in log_message.lower():
                                        progress = 20
                                    elif "分析" in log_message or "analyze" in log_message.lower() or "识别" in log_message:
                                        progress = 40
                                    elif "chunk" in log_message.lower():
                                        progress = 60
                                    elif "插入" in log_message or "insert" in log_message.lower():
                                        progress = 75
                                    elif "完成" in log_message or "complete" in log_message.lower():
                                        progress = 90

                                # 创建日志数据并推送到队列
                                log_data = {
                                    "type": "log",
                                    "message": log_message,
                                    "progress": progress,
                                    "step": log_type,
                                    "timestamp": time.time(),
                                    "level": record.levelname
                                }
                                log_queue.put(json.dumps(log_data))
                            except Exception:
                                # 避免日志处理异常影响主流程
                                pass

                    sse_handler = SSELogHandler()
                    sse_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
                    logger.addHandler(sse_handler)

                    try:
                        parsed_questions = llm_service.parse_crawl_results(
                            [page_data], on_question_found=on_question_found
                        )
                    finally:
                        logger.removeHandler(sse_handler)

                    log_callback(f"问题识别完成，共识别 {len(parsed_questions)} 个问题", 80, "completed")
                    log_callback("正在存入向量数据库...", 90, "finalizing")

                    end_time = time.time()
                    total_time = end_time - start_time

                    result = {
                        "status": "success",
                        "message": "页面爬取完成",
                        "url": url,
                        "title": scan_result.title,
                        "parsed_questions": len(parsed_questions),
                        "inserted_questions": inserted_count,
                        "word_count": scan_result.word_count,
                        "load_time": scan_result.load_time,
                        "total_processing_time": round(total_time, 2),
                    }

                    log_callback(f"爬取完成！总耗时: {round(total_time, 2)}秒", 100, "finished")

                    # 发送最终结果
                    final_data = {
                        "type": "complete",
                        "result": result
                    }
                    log_queue.put(json.dumps(final_data))

                except Exception as e:
                    error_msg = f"爬取失败: {str(e)}"
                    log_callback(error_msg, 0, "error")
                    log_queue.put("ERROR")
                    logger.error(error_msg)

            # 启动后台线程
            crawl_thread = Thread(target=run_crawl, daemon=True)
            crawl_thread.start()

            # 持续从队列读取并发送SSE事件
            while True:
                try:
                    # 非阻塞方式获取消息
                    message = log_queue.get(timeout=1)

                    if message == "ERROR":
                        yield f"data: {json.dumps({'type': 'error', 'message': '爬取过程中发生错误'})}\n\n"
                        break

                    yield f"data: {message}\n\n"

                    # 检查是否是完成消息
                    if isinstance(message, str):
                        try:
                            data = json.loads(message)
                            if data.get("type") == "complete":
                                break
                        except Exception:
                            pass

                except Empty:
                    # 检查线程是否结束
                    if not crawl_thread.is_alive():
                        break
                    continue

            # 清理队列
            if session_id in sse_log_queues:
                del sse_log_queues[session_id]

        except asyncio.CancelledError:
            # 客户端断开连接
            if session_id in sse_log_queues:
                del sse_log_queues[session_id]
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用Nginx缓冲
        }
    )


@app.get("/api/config", summary="获取爬虫配置")
async def get_crawler_config():
    """
    获取当前爬虫配置
    """
    try:
        DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "crawler_config.json"

        if DEFAULT_CONFIG_PATH.exists():
            config = CrawlerConfig.from_json(str(DEFAULT_CONFIG_PATH))
        else:
            config = get_config_from_env()

        return {
            "status": "success",
            "config": config.to_dict()
        }
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/config", summary="更新爬虫配置")
async def update_crawler_config(config_data: Dict[str, Any]):
    """
    更新爬虫配置并保存到文件
    """
    try:
        DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "crawler_config.json"

        # 创建新配置
        config = CrawlerConfig.from_dict(config_data)

        # 保存到文件
        config.to_json(str(DEFAULT_CONFIG_PATH))

        logger.info(f"配置已更新并保存到: {DEFAULT_CONFIG_PATH}")

        return {
            "status": "success",
            "message": "配置更新成功",
            "config": config.to_dict()
        }
    except Exception as e:
        logger.error(f"更新配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scheduler-config", summary="获取定时任务配置")
async def get_scheduler_config_api():
    """
    获取定时任务配置
    """
    try:
        config = get_scheduler_config()
        return {
            "status": "success",
            "config": config
        }
    except Exception as e:
        logger.error(f"获取定时配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/scheduler-config", summary="更新定时任务配置")
async def update_scheduler_config(hour: int, minute: int):
    """
    更新定时任务配置（支持热加载，无需重启）
    """
    try:
        # 热加载定时任务配置
        reload_success = config_reload_manager.reload_scheduler_config(scheduler, hour, minute)

        return {
            "status": "success",
            "message": "定时任务配置已更新" + ("（已热加载，立即生效）" if reload_success else "（请重启服务使配置生效）"),
            "hot_reload": reload_success,
            "current_config": {
                "hour": hour,
                "minute": minute
            }
        }
    except Exception as e:
        logger.error(f"更新定时配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/llm-config", summary="更新模型配置")
async def update_llm_config(config_data: Dict[str, Any]):
    """
    更新模型配置（支持热加载，无需重启）
    """
    try:
        import os
        from dotenv import set_key, find_dotenv

        # 加载环境变量
        dotenv_path = find_dotenv()
        if not dotenv_path:
            dotenv_path = '.env'

        # 更新.env文件中的配置
        for key, value in config_data.items():
            env_key = key.upper()
            if value is not None and value != '':
                set_key(dotenv_path, env_key, str(value))
            else:
                # 如果值为空，删除该配置项
                if os.getenv(env_key):
                    # 读取文件并删除对应行
                    with open(dotenv_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    with open(dotenv_path, 'w', encoding='utf-8') as f:
                        for line in lines:
                            if not line.startswith(f'{env_key}='):
                                f.write(line)

        # 热加载配置
        reload_success = config_reload_manager.reload_llm_config()

        return {
            "status": "success",
            "message": "模型配置已更新" + ("（已热加载，立即生效）" if reload_success else "（请重启服务使配置生效）"),
            "hot_reload": reload_success,
            "config": config_data
        }
    except Exception as e:
        logger.error(f"更新模型配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Redis配置API已移除 - Redis运行在Docker容器内，使用固定的 redis://redis:6379
# 如需从宿主机访问，可在 .env 中修改 REDIS_PORT


@app.put("/api/email-config", summary="更新邮件配置")
async def update_email_config(config_data: Dict[str, Any]):
    """
    更新邮件配置（支持热加载，无需重启）
    """
    try:
        from dotenv import set_key, find_dotenv

        # 加载环境变量
        dotenv_path = find_dotenv()
        if not dotenv_path:
            dotenv_path = '.env'

        # 更新邮件配置
        email_mapping = {
            'smtp_server': 'SMTP_SERVER',
            'smtp_port': 'SMTP_PORT',
            'smtp_user': 'SMTP_USER',
            'smtp_password': 'SMTP_PASSWORD',
            'smtp_test_user': 'SMTP_TEST_USER'
        }

        for key, value in config_data.items():
            if key in email_mapping:
                env_key = email_mapping[key]
                if value is not None and value != '' and value != '********':
                    set_key(dotenv_path, env_key, str(value))

        # 热加载配置
        reload_success = config_reload_manager.reload_email_config()

        return {
            "status": "success",
            "message": "邮件配置已更新" + ("（已热加载，立即生效）" if reload_success else "（请重启服务使配置生效）"),
            "hot_reload": reload_success,
            "config": config_data
        }
    except Exception as e:
        logger.error(f"更新邮件配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-email", summary="测试邮件发送")
async def test_email():
    """
    测试邮件发送功能
    """
    try:
        import os
        from app.services.email_service import send_interview_email

        # 获取测试邮箱
        test_user = os.getenv("SMTP_TEST_USER")
        if not test_user:
            raise HTTPException(status_code=400, detail="未配置测试邮箱(SMTP_TEST_USER)")

        # 创建测试问题
        test_questions = [
            {
                "title": "测试问题 - 什么是Python装饰器？",
                "answer": "这是一个测试答案。装饰器是一种特殊的函数，可以用来修改其他函数的行为。",
                "difficulty": "easy",
                "category": "Python基础"
            }
        ]

        # 发送测试邮件
        result = send_interview_email(test_user, test_questions)

        if result == 250 or result == 200:
            return {
                "status": "success",
                "message": f"测试邮件已发送到 {test_user}"
            }
        else:
            return {
                "status": "warning",
                "message": f"邮件发送可能失败，状态码: {result}"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试邮件发送失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"邮件发送失败: {str(e)}")


@app.put("/api/rerank-config", summary="更新 Rerank 配置")
async def update_rerank_config(config_data: Dict[str, Any]):
    """
    更新 Rerank 配置（支持热加载）
    """
    try:
        from dotenv import set_key, find_dotenv

        # 加载环境变量
        dotenv_path = find_dotenv()
        if not dotenv_path:
            dotenv_path = '.env'

        # 更新 Rerank 配置
        rerank_mapping = {
            'enabled': 'RERANK_ENABLED',
            'model_name': 'RERANK_MODEL'
        }

        for key, value in config_data.items():
            if key in rerank_mapping:
                env_key = rerank_mapping[key]
                if value is not None and value != '':
                    set_key(dotenv_path, env_key, str(value))

        # 重新加载反馈服务中的 Rerank 配置
        feedback_service.reload_rerank_config()

        return {
            "status": "success",
            "message": "Rerank 配置已更新（立即生效）",
            "config": config_data
        }
    except Exception as e:
        logger.error(f"更新 Rerank 配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system-config", summary="获取系统配置")
async def get_system_config():
    """
    获取所有系统配置（按类别分组）
    """
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv()

        # 爬虫配置
        DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "crawler_config.json"
        if DEFAULT_CONFIG_PATH.exists():
            crawler_config = CrawlerConfig.from_json(str(DEFAULT_CONFIG_PATH))
        else:
            crawler_config = get_config_from_env()

        # 模型配置
        llm_config = {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "openai_api_base": os.getenv("OPENAI_API_BASE", ""),
            "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "openai_embedding_model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            "embedding_dimension": int(os.getenv("EMBEDDING_DIMENSION", "1536")),
            "model_max_input_tokens": os.getenv("MODEL_MAX_INPUT_TOKENS", ""),
            "model_max_output_tokens": os.getenv("MODEL_MAX_OUTPUT_TOKENS", ""),
        }

        # Rerank 配置
        rerank_config = {
            "enabled": os.getenv("RERANK_ENABLED", "false").lower() == "true",
            "model_name": os.getenv("RERANK_MODEL", "rerank-sf"),
            "description": "Rerank 模型复用 LLM 的 API Key 和 Base URL"
        }

        # Redis配置（固定值）
        redis_config = {
            "redis_url": "redis://redis:6379",
            "description": "Redis运行在Docker容器内，App自动连接"
        }

        # 邮件配置
        email_config = {
            "smtp_server": os.getenv("SMTP_SERVER", ""),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "smtp_user": os.getenv("SMTP_USER", ""),
            "smtp_password": os.getenv("SMTP_PASSWORD", ""),
            "smtp_test_user": os.getenv("SMTP_TEST_USER", ""),
        }

        # 定时任务配置
        scheduler_cfg = get_scheduler_config()

        return {
            "status": "success",
            "config": {
                "crawler": crawler_config.to_dict(),
                "llm": llm_config,
                "rerank": rerank_config,
                "redis": redis_config,
                "email": email_config,
                "scheduler": scheduler_cfg,
            }
        }
    except Exception as e:
        logger.error(f"获取系统配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 定时任务调度器
scheduler = BackgroundScheduler()

# 从环境变量获取定时配置
scheduler_config = get_scheduler_config()
SCHEDULER_HOUR = scheduler_config["hour"]
SCHEDULER_MINUTE = scheduler_config["minute"]

# 添加定时任务：每天指定时间执行


@scheduler.scheduled_job(CronTrigger(hour=SCHEDULER_HOUR, minute=SCHEDULER_MINUTE))
def scheduled_crawl():
    """
    定时爬虫任务（每天指定时间执行）
    """
    run_crawler()

# 添加定时任务：每天凌晨2点更新题目权重


@scheduler.scheduled_job(CronTrigger(hour=2, minute=0))
def scheduled_update_weights():
    """
    定时更新题目权重（基于艾宾浩斯遗忘曲线）
    """
    logger.info("开始执行定时权重更新任务...")
    try:
        updated_count = feedback_service.update_all_weights()
        logger.info(f"权重更新完成: 更新了 {updated_count} 个题目")
    except Exception as e:
        logger.error(f"定时权重更新任务失败: {str(e)}")


if __name__ == "__main__":
    # 启动定时任务调度器
    scheduler.start()
    logger.info(
        f"定时任务调度器已启动，每天 {SCHEDULER_HOUR}:{SCHEDULER_MINUTE:02d} 执行爬虫任务"
    )

    # 启动 FastAPI 服务
    uvicorn.run(app, host="0.0.0.0", port=8000)

    # 优雅关闭调度器
    scheduler.shutdown()
