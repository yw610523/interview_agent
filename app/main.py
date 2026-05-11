import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from queue import Queue, Empty
from threading import Thread
from typing import List, Optional, Dict, Any

import uvicorn
# 定时任务相关
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl

# 导入统一配置管理器
from app.config.config_manager import config_manager
from app.config.crawler_config import (
    get_scheduler_config,
    load_crawler_config,
)
# 导入爬虫相关模块
from app.services.async_batch_crawler import AsyncBatchCrawler
# 导入配置热加载管理器
from app.services.config_hot_reload import config_reload_manager
# 导入任务管理器
from app.services.crawl_task_manager import crawl_task_manager, TaskStatus
# 导入反馈服务
from app.services.feedback_service import FeedbackService
# 导入大模型和向量服务
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService, VectorRecord

app = FastAPI(title="Interview AI Agent")


def _mask_sensitive(key: str, value: str) -> str:
    """对敏感信息进行脱敏处理"""
    sensitive_keys = ['api_key', 'password', 'token', 'secret']
    if any(k in key.lower() for k in sensitive_keys):
        if not value or value == "" or value.startswith("$"):
            return "*** (未配置)"
        return value[:4] + "***" + value[-4:] if len(value) > 8 else "***"
    return str(value)


def _log_startup_config():
    """启动时打印配置信息（脱敏）"""
    logger.info("=" * 60)
    logger.info("📋 系统配置信息（启动自检）")
    logger.info("=" * 60)

    modules = ['llm', 'redis', 'smtp', 'content', 'crawler', 'rerank']
    for module in modules:
        try:
            cfg = config_manager.get_config(module)
            if not cfg:
                continue
            logger.info(f"\n--- {module.upper()} 配置 ---")
            for k, v in cfg.items():
                if isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        logger.info(f"  {module}.{sub_k}: {_mask_sensitive(sub_k, sub_v)}")
                else:
                    logger.info(f"  {k}: {_mask_sensitive(k, v)}")
        except Exception as e:
            logger.warning(f"读取 {module} 配置失败: {e}")
    logger.info("=" * 60)


@app.on_event("startup")
async def startup_event():
    _log_startup_config()


# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _mask_sensitive(key: str, value: Any) -> str:
    """对敏感信息进行脱敏处理"""
    sensitive_keys = ['api_key', 'password', 'token', 'secret', 'user']
    if any(k in key.lower() for k in sensitive_keys):
        val_str = str(value)
        if not val_str or val_str == "" or val_str.startswith("$"):
            return "*** (未配置)"
        return val_str[:4] + "***" + val_str[-4:] if len(val_str) > 8 else "***"
    return str(value)


def _mask_sensitive_value(value: str) -> str:
    """对敏感信息值进行脱敏处理（仅传入值）"""
    if not value or value == "" or value.startswith("$"):
        return "*** (未配置)"
    return value[:4] + "***" + value[-4:] if len(value) > 8 else "***"


def _is_masked_value(value: Any) -> bool:
    """
    检测值是否为脱敏后的假值
    
    Args:
        value: 要检测的值
        
    Returns:
        True 如果是脱敏值，False 如果是真实值
    """
    if value is None:
        return True
    val_str = str(value)
    # 检查常见的占位符模式
    if val_str == '' or val_str == '********' or val_str.startswith('***'):
        return True
    # 检查脱敏格式：包含 *** 的字符串
    if '***' in val_str:
        return True
    return False


@app.on_event("startup")
async def startup_event():
    """启动时打印配置信息（脱敏）"""
    logger.info("=" * 60)
    logger.info("📋 系统配置信息（启动自检）")
    logger.info("=" * 60)

    from app.config.config_manager import config_manager
    modules = ['llm', 'redis', 'smtp', 'content', 'crawler', 'rerank']
    for module in modules:
        try:
            cfg = config_manager.get_config(module)
            if not cfg:
                continue
            logger.info(f"\n--- {module.upper()} 配置 ---")
            for k, v in cfg.items():
                if isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        logger.info(f"  {module}.{sub_k}: {_mask_sensitive(sub_k, sub_v)}")
                else:
                    logger.info(f"  {k}: {_mask_sensitive(k, v)}")
        except Exception as e:
            logger.warning(f"读取 {module} 配置失败: {e}")
    logger.info("=" * 60)


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
        # 加载配置（优先 YAML，兼容 JSON）
        config = load_crawler_config()

        if not config.sitemap_url:
            logger.error("配置错误：未指定 Sitemap URL")
            return {"status": "error", "message": "未指定 Sitemap URL"}

        # 使用异步批量爬虫（即使是同步API也使用并发提升性能）
        async_crawler = AsyncBatchCrawler(
            config=config,
            max_workers=5,  # 默认5个并发线程
            timeout_per_url=config.timeout
        )

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

        # 如果需要从sitemap获取URLs，需要先解析sitemap
        from app.services.sitemap_parser import SitemapParser
        from app.services.url_scanner import URLScanner
        from app.config.firecrawl_config import get_firecrawl_config
        from app.config.config_manager import config_manager
        import json

        # 初始化扫描器以检查robots.txt
        firecrawl_cfg = get_firecrawl_config()
        scanner = URLScanner(
            timeout=config.timeout,
            follow_redirects=config.follow_redirects,
            verify_ssl=config.verify_ssl,
            max_content_length=config.max_content_length,
            use_firecrawl=config.use_firecrawl,
            firecrawl_api_url=firecrawl_cfg.api_url,
            firecrawl_api_key=firecrawl_cfg.api_key,
            firecrawl_timeout=firecrawl_cfg.timeout,
            firecrawl_api_version=firecrawl_cfg.api_version,
            firecrawl_only_main_content=firecrawl_cfg.only_main_content,
        )

        # 标准化sitemap URL
        sitemap_url = config.sitemap_url
        if not sitemap_url.startswith(('http://', 'https://')):
            sitemap_url = f"https://{sitemap_url}"

        # 如果只是域名（没有路径），自动添加 sitemap.xml 路径
        from urllib.parse import urlparse
        parsed = urlparse(sitemap_url)
        if not parsed.path or parsed.path == '/':
            # 构建完整路径：root_url + sitemap_path
            root_url = config.root_url.rstrip('/')
            sitemap_path = config.sitemap_path if config.sitemap_path else '/sitemap.xml'
            sitemap_url = f"{parsed.scheme}://{parsed.netloc}{root_url}{sitemap_path}"
            logger.info(f"自动补全 Sitemap URL: {sitemap_url}")

        # 检查robots.txt
        if config.check_robots_txt:
            robots_txt = scanner.check_robots_txt(sitemap_url, config.robots_path)
            if robots_txt:
                # 简单的robots.txt检查
                if 'Disallow: /' in robots_txt:
                    raise PermissionError("robots.txt 禁止爬取此网站")

        # 检查 Redis 缓存中的 URL 列表
        redis_client = config_manager.redis_client
        cache_key = f"{SITEMAP_CACHE_PREFIX}{sitemap_url}"
        urls = []
        from_cache = False
        
        if redis_client:
            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    logger.info(f"爬取任务使用 Redis 缓存的 Sitemap 数据: {cache_key}")
                    result = json.loads(cached_data)
                    if 'urls' in result and result['urls']:
                        urls = result['urls']
                        from_cache = True
                        logger.info(f"从缓存获取到 {len(urls)} 个 URL")
            except Exception as e:
                logger.warning(f"Redis 缓存读取失败: {str(e)}，将重新解析")

        # 如果缓存中没有 URL，则解析 sitemap
        if not urls:
            logger.info(f"开始解析 Sitemap: {sitemap_url}")
            parser = SitemapParser(sitemap_url)
            parser.fetch_sitemap()
            urls = parser.parse()
            logger.info(f"Sitemap 解析完成，共获取到 {len(urls)} 个 URL")
        else:
            logger.info(f"使用缓存的 Sitemap URL 列表，共 {len(urls)} 个 URL")

        # 应用URL过滤
        from app.services.url_filter import URLFilter
        url_filter = URLFilter.from_config(config)
        if config.url_include_patterns or config.url_exclude_patterns:
            original_count = len(urls)
            urls = url_filter.filter_urls(urls)
            filtered_count = original_count - len(urls)
            if filtered_count > 0:
                logger.info(f"URL过滤: 原始={original_count}, 过滤后={len(urls)}, 排除={filtered_count}")

        # 限制最大URL数量
        if config.max_urls and len(urls) > config.max_urls:
            urls = urls[:config.max_urls]

        # 执行异步批量爬取
        results = async_crawler.crawl_batch(
            urls=urls,
            progress_callback=None,
            page_processed_callback=on_page_processed,
            stop_flag=None
        )

        # 获取统计信息
        stats = async_crawler.get_stats()

        logger.info(
            f"解析出 {total_parsed_questions} 个面试问题，成功插入 {inserted_count} 个问题到向量数据库"
        )

        # 构建返回结果
        result = {
            "status": "success",
            "message": "爬取完成",
            "statistics": stats.to_dict(),
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

        # 关闭线程池
        async_crawler.shutdown()

        logger.info(f"爬虫任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"爬虫任务失败: {str(e)}")
        return {"status": "error", "message": str(e)}


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

                # 加载配置（优先 YAML，兼容 JSON）
                config = load_crawler_config()

                if not config.sitemap_url:
                    raise ValueError("未指定 Sitemap URL")

                # 使用新的异步批量爬虫
                async_crawler = AsyncBatchCrawler(
                    config=config,
                    max_workers=5,  # 默认5个并发线程
                    timeout_per_url=config.timeout
                )

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

                # 如果需要从sitemap获取URLs，需要先解析sitemap
                from app.services.sitemap_parser import SitemapParser
                from app.services.url_scanner import URLScanner
                from app.config.firecrawl_config import get_firecrawl_config
                from app.config.config_manager import config_manager
                import json

                # 初始化扫描器以检查robots.txt
                firecrawl_cfg = get_firecrawl_config()
                scanner = URLScanner(
                    timeout=config.timeout,
                    follow_redirects=config.follow_redirects,
                    verify_ssl=config.verify_ssl,
                    max_content_length=config.max_content_length,
                    use_firecrawl=config.use_firecrawl,
                    firecrawl_api_url=firecrawl_cfg.api_url,
                    firecrawl_api_key=firecrawl_cfg.api_key,
                    firecrawl_timeout=firecrawl_cfg.timeout,
                    firecrawl_api_version=firecrawl_cfg.api_version,
                    firecrawl_only_main_content=firecrawl_cfg.only_main_content,
                )

                # 标准化sitemap URL
                sitemap_url = config.sitemap_url
                if not sitemap_url.startswith(('http://', 'https://')):
                    sitemap_url = f"https://{sitemap_url}"

                # 如果只是域名（没有路径），自动添加 sitemap.xml 路径
                from urllib.parse import urlparse
                parsed = urlparse(sitemap_url)
                if not parsed.path or parsed.path == '/':
                    # 构建完整路径：root_url + sitemap_path
                    root_url = config.root_url.rstrip('/')
                    sitemap_path = config.sitemap_path if config.sitemap_path else '/sitemap.xml'
                    sitemap_url = f"{parsed.scheme}://{parsed.netloc}{root_url}{sitemap_path}"
                    logger.info(f"自动补全 Sitemap URL: {sitemap_url}")

                # 检查robots.txt
                if config.check_robots_txt:
                    robots_txt = scanner.check_robots_txt(sitemap_url, config.robots_path)
                    if robots_txt:
                        # 简单的robots.txt检查
                        if 'Disallow: /' in robots_txt:
                            raise PermissionError("robots.txt 禁止爬取此网站")

                # 检查 Redis 缓存中的 URL 列表
                try:
                    logger.info(f"[DEBUG] 即将检查 Redis 缓存, redis_client={config_manager.redis_client is not None}")
                    redis_client = config_manager.redis_client
                    cache_key = f"{SITEMAP_CACHE_PREFIX}{sitemap_url}"
                    logger.info(f"[DEBUG] cache_key={cache_key}")
                    urls = []
                    from_cache = False
                    
                    if redis_client:
                        logger.info(f"[DEBUG] 进入 if redis_client 分支")
                        cached_data = redis_client.get(cache_key)
                        logger.info(f"[DEBUG] Redis 查询完成, cached_data={'存在' if cached_data else '不存在'}")
                        if cached_data:
                            logger.info(f"异步爬取使用 Redis 缓存的 Sitemap 数据: {cache_key}")
                            result = json.loads(cached_data)
                            if 'urls' in result and result['urls']:
                                urls = result['urls']
                                from_cache = True
                                logger.info(f"从缓存获取到 {len(urls)} 个 URL")
                        else:
                            logger.info(f"[DEBUG] 缓存不存在, 将解析 sitemap")
                    else:
                        logger.warning("Redis 客户端不可用，将直接解析 Sitemap")
                except Exception as e:
                    import traceback
                    logger.error(f"[DEBUG] Redis 缓存检查阶段发生异常: {e}")
                    logger.error(traceback.format_exc())
                    urls = []
                    from_cache = False

                # 如果缓存中没有 URL，则解析 sitemap
                if not urls:
                    logger.info(f"开始解析 Sitemap: {sitemap_url}")
                    parser = SitemapParser(sitemap_url)

                    try:
                        parser.fetch_sitemap()
                        logger.info("Sitemap 获取成功")
                    except Exception as e:
                        logger.error(f"Sitemap 获取失败: {str(e)}")
                        raise ValueError(f"无法获取 Sitemap: {str(e)}")

                    urls = parser.parse()
                    logger.info(f"Sitemap 解析完成，共获取到 {len(urls)} 个 URL")
                else:
                    logger.info(f"使用缓存的 Sitemap URL 列表，共 {len(urls)} 个 URL")

                if len(urls) == 0:
                    logger.warning("Sitemap 中未找到任何 URL，请检查:")
                    logger.warning(f"1. Sitemap URL 是否正确: {sitemap_url}")
                    logger.warning(f"2. Sitemap 文件是否存在且可访问")
                    logger.warning(f"3. Sitemap 格式是否正确（XML）")
                    # 打印前几个URL样本用于调试
                    if hasattr(parser, '_xml_content') and parser._xml_content:
                        logger.warning(f"Sitemap 内容预览（前500字符）: {parser._xml_content[:500]}")

                # 应用URL过滤
                from app.services.url_filter import URLFilter
                url_filter = URLFilter.from_config(config)
                if config.url_include_patterns or config.url_exclude_patterns:
                    original_count = len(urls)
                    urls = url_filter.filter_urls(urls)
                    filtered_count = original_count - len(urls)
                    if filtered_count > 0:
                        logger.info(f"URL过滤: 原始={original_count}, 过滤后={len(urls)}, 排除={filtered_count}")

                # 限制最大URL数量
                if config.max_urls and len(urls) > config.max_urls:
                    urls = urls[:config.max_urls]

                # 执行异步批量爬取
                results = async_crawler.crawl_batch(
                    urls=urls,
                    progress_callback=None,
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
                            stats = async_crawler.get_stats()
                            result = {
                                "status": "stopped",
                                "message": "任务被用户中断",
                                "statistics": stats.to_dict(),
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

                    # 关闭线程池
                    async_crawler.shutdown()
                else:
                    # 任务正常完成
                    stats = async_crawler.get_stats()
                    task.total_urls = stats.total_urls
                    task.processed_urls = stats.successful_scans + stats.failed_scans
                    task.parsed_questions = total_parsed_questions
                    task.inserted_questions = inserted_count

                    result = {
                        "status": "success",
                        "message": "爬取完成",
                        "statistics": stats.to_dict(),
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

                    # 关闭线程池
                    async_crawler.shutdown()

            except Exception as e:
                logger.error(f"任务 {task_id} 执行失败: {str(e)}")
                crawl_task_manager.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    end_time=datetime.now().isoformat(),
                    error_message=str(e)
                )
                # 关闭线程池
                try:
                    async_crawler.shutdown()
                except:
                    pass

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
            logger.info(
                f"混合搜索: '{query}' -> {len(results)} 个结果 (语义:{len(semantic_results)}, 精确:{len(exact_results)})")

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

        # 如果启用 Rerank,先取更多候选,然后重排序
        rerank_success = False
        if use_rerank and feedback_service.rerank_enabled:
            try:
                # 扩大候选池到 limit * 10,增加多样性
                import random
                candidate_pool_size = min(limit * 10, len(scored_questions))
                candidate_pool = scored_questions[:candidate_pool_size]

                # 给优先级分数添加随机扰动(±15%),避免每次都是同样的题
                for q in candidate_pool:
                    noise = random.uniform(0.85, 1.15)
                    q['priority_score'] *= noise

                # 重新排序并随机抽样
                candidate_pool.sort(key=lambda x: x['priority_score'], reverse=True)
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
                logger.warning(f"Rerank 失败,降级为默认排序: {str(e)}")
                # Rerank 失败,降级为默认排序(带随机性)
                import random
                candidate_pool_size = min(limit * 10, len(scored_questions))
                candidate_pool = scored_questions[:candidate_pool_size]

                # 添加随机扰动
                for q in candidate_pool:
                    noise = random.uniform(0.85, 1.15)
                    q['priority_score'] *= noise

                candidate_pool.sort(key=lambda x: x['priority_score'], reverse=True)
                recommended = candidate_pool[:limit]
        else:
            # 直接返回前 limit 个(带随机性,从候选池中随机抽样)
            import random
            candidate_pool_size = min(limit * 10, len(scored_questions))
            candidate_pool = scored_questions[:candidate_pool_size]

            # 添加随机扰动后重新排序
            for q in candidate_pool:
                noise = random.uniform(0.85, 1.15)
                q['priority_score'] *= noise

            candidate_pool.sort(key=lambda x: x['priority_score'], reverse=True)
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
async def update_question_importance(question_id: str,
                                     importance_score: float = Query(..., ge=0, le=1, description="重要性评分 0-1")):
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


@app.post("/api/questions/{question_id}/hide", summary="隐藏题目（软删除）")
async def hide_question(question_id: str):
    """
    隐藏题目（软删除，保留30天）
    
    隐藏后的题目：
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


@app.delete("/api/questions/{question_id}/permanent", summary="直接从向量库永久删除题目")
async def direct_permanent_delete(question_id: str):
    """
    直接从向量数据库中永久删除题目（不经过反馈系统）
    用于标记“非问题”的场景
    """
    try:
        # 直接从向量数据库中删除
        success = await run_sync(vector_service.delete_by_id, question_id)

        if not success:
            raise HTTPException(status_code=404, detail="题目不存在")

        # 同时清理反馈数据（如果存在）
        try:
            key = feedback_service._get_feedback_key(question_id)
            if feedback_service.redis_client:
                feedback_service.redis_client.delete(key)
        except Exception:
            pass  # 反馈数据不存在不影响主流程

        logger.info(f"直接永久删除题目: {question_id}")
        return {
            "status": "success",
            "message": "题目已永久删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Direct permanent delete error: {str(e)}")
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


# 注意：/api/crawl/single-page 阻塞式接口已弃用
# 请使用 /api/crawl/single-page/stream SSE 流式接口
# 该接口使用后台线程执行，不会阻塞事件循环

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

            # 在后台线程中执行爬取任务（使用线程池避免阻塞）

            def run_crawl():
                try:
                    log_callback("正在扫描页面...", 10, "scanning")

                    # 1. 扫描页面
                    from app.config.config_manager import config_manager

                    crawler_config_dict = config_manager.get_config('crawler')
                    firecrawl_config_dict = config_manager.get_config('firecrawl')

                    scanner = URLScanner(
                        timeout=crawler_config_dict.get('timeout', 30),
                        follow_redirects=True,
                        verify_ssl=True,
                        max_content_length=5 * 1024 * 1024,
                        use_firecrawl=firecrawl_config_dict.get('enabled', False),
                        firecrawl_api_url=firecrawl_config_dict.get('api_url', ''),
                        firecrawl_api_key=firecrawl_config_dict.get('api_key', ''),
                        firecrawl_timeout=firecrawl_config_dict.get('timeout', 300),
                        firecrawl_api_version=firecrawl_config_dict.get('api_version', 'v2'),
                        firecrawl_only_main_content=firecrawl_config_dict.get('only_main_content', True),
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

            crawl_thread = Thread(target=run_crawl, daemon=True)
            crawl_thread.start()

            # 持续从队列读取并发送SSE事件
            while True:
                try:
                    # 在线程池中执行阻塞的队列读取操作
                    loop = asyncio.get_event_loop()
                    message = await loop.run_in_executor(
                        None,  # 使用默认线程池
                        lambda: log_queue.get(timeout=1)
                    )

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


@app.post("/api/crawl/batch-urls", summary="异步批量爬取指定URL列表")
async def crawl_batch_urls(urls: List[str], max_workers: int = Query(5, ge=1, le=20)):
    """
    异步批量爬取指定的URL列表
    
    参数:
        urls: 要爬取的URL列表
        max_workers: 最大并发线程数（1-20，默认5）
    """
    import uuid

    if not urls:
        raise HTTPException(status_code=400, detail="URL列表不能为空")

    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 创建任务
        task = crawl_task_manager.create_task(task_id)

        # 加载配置
        config = load_crawler_config()

        # 在后台线程中执行批量爬取
        def run_batch_crawl():
            try:
                # 更新任务状态为运行中
                crawl_task_manager.update_task_status(
                    task_id,
                    TaskStatus.RUNNING,
                    start_time=datetime.now().isoformat(),
                    total_urls=len(urls)
                )

                # 创建异步批量爬虫
                async_crawler = AsyncBatchCrawler(
                    config=config,
                    max_workers=max_workers,
                    timeout_per_url=config.timeout
                )

                # 统计变量
                inserted_count = 0
                total_parsed_questions = 0

                # 定义页面处理回调
                def on_page_processed(page_data):
                    nonlocal total_parsed_questions
                    try:
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

                            task.parsed_questions += len(questions)
                            task.inserted_questions = inserted_count

                        parsed_questions = llm_service.parse_crawl_results(
                            page_list, on_question_found=on_question_found
                        )
                        total_parsed_questions += len(parsed_questions)
                        task.processed_urls += 1

                    except Exception as e:
                        logger.error(f"页面处理失败: {str(e)}")

                # 执行批量爬取
                results = async_crawler.crawl_batch(
                    urls=urls,
                    progress_callback=None,
                    page_processed_callback=on_page_processed,
                    stop_flag=task.stop_flag
                )

                # 检查是否被中断
                if task.stop_flag.is_set():
                    stats = async_crawler.get_stats()
                    result = {
                        "status": "stopped",
                        "message": "任务被用户中断",
                        "statistics": stats.to_dict(),
                        "result_count": len(results),
                        "parsed_questions": total_parsed_questions,
                        "inserted_questions": inserted_count,
                    }

                    crawl_task_manager.update_task_status(
                        task_id,
                        TaskStatus.STOPPED,
                        end_time=datetime.now().isoformat(),
                        error_message="任务被用户中断"
                    )

                    # 更新Redis
                    try:
                        if vector_service.redis_client:
                            result_json = json.dumps(result)
                            vector_service.redis_client.setex(
                                "crawl:last_result", 86400, result_json
                            )
                    except Exception as e:
                        logger.warning(f"存储状态到 Redis 失败: {str(e)}")
                else:
                    # 正常完成
                    stats = async_crawler.get_stats()
                    task.total_urls = stats.total_urls
                    task.processed_urls = stats.successful_scans + stats.failed_scans
                    task.parsed_questions = total_parsed_questions
                    task.inserted_questions = inserted_count

                    result = {
                        "status": "success",
                        "message": "批量爬取完成",
                        "statistics": stats.to_dict(),
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

                    # 更新Redis
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
                    except Exception as e:
                        logger.warning(f"存储结果到 Redis 失败: {str(e)}")

                # 关闭线程池
                async_crawler.shutdown()

            except Exception as e:
                logger.error(f"批量爬取任务失败: {str(e)}")
                crawl_task_manager.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    end_time=datetime.now().isoformat(),
                    error_message=str(e)
                )
                try:
                    async_crawler.shutdown()
                except:
                    pass

        # 启动后台线程
        thread = Thread(target=run_batch_crawl, daemon=True)
        thread.start()

        return {
            "status": "accepted",
            "message": "批量爬取任务已启动",
            "task_id": task_id,
            "total_urls": len(urls),
            "max_workers": max_workers
        }

    except Exception as e:
        logger.error(f"启动批量爬取任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config", summary="获取爬虫配置")
async def get_crawler_config():
    """
    获取当前爬虫配置
    """
    try:
        # 加载配置（优先 YAML，兼容 JSON）
        config = load_crawler_config()

        return {
            "status": "success",
            "config": config.to_dict()
        }
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Sitemap 解析结果缓存键前缀
SITEMAP_CACHE_PREFIX = "sitemap_cache:"


@app.get("/api/config/test-url", summary="测试URL连通性")
async def test_url_connectivity(url: str):
    """
    测试指定URL的连通性
    
    参数:
        url: 要测试的URL地址
    """
    import urllib.request
    import ssl

    try:
        if not url:
            raise HTTPException(status_code=400, detail="URL不能为空")

        # 如果URL不包含协议，默认添加https://
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        # 创建SSL上下文（不验证证书以避免某些网站证书问题）
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # 发送请求
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )

        response = urllib.request.urlopen(req, timeout=10, context=ssl_context)
        status_code = response.getcode()
        is_accessible = status_code < 400

        return {
            "status": "success",
            "url": url,
            "accessible": is_accessible,
            "status_code": status_code,
            "message": "URL可访问" if is_accessible else f"URL返回状态码: {status_code}"
        }
    except urllib.error.HTTPError as e:
        return {
            "status": "success",
            "url": url,
            "accessible": False,
            "status_code": e.code,
            "message": f"URL返回状态码: {e.code}"
        }
    except urllib.error.URLError as e:
        raise HTTPException(status_code=400, detail=f"无法访问URL: {str(e.reason)}")
    except Exception as e:
        logger.error(f"测试URL连通性失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/sitemap-paths", summary="获取Sitemap路径树")
async def get_sitemap_paths(sitemap_url: Optional[str] = None, root_url: Optional[str] = ""):
    """
    解析sitemap，返回树状路径结构供用户选择
    
    参数:
        sitemap_url: 可选的sitemap URL（优先使用参数，否则从配置读取）
        root_url: 可选的根路径前缀
    
    返回格式:
    [
        {
            "title": "/backend_interview",
            "key": "/backend_interview",
            "children": [
                {"title": "/bank", "key": "/backend_interview/bank"},
                ...
            ]
        },
        ...
    ]
    """
    try:
        from app.config.crawler_config import load_crawler_config
        from app.services.sitemap_parser import SitemapParser
        from app.config.config_manager import config_manager
        from urllib.parse import urlparse
        import json
        
        # 加载配置
        config = load_crawler_config()
        
        # 优先使用参数传入的URL，其次使用配置中的URL
        if sitemap_url:
            effective_sitemap_url = sitemap_url
        else:
            effective_sitemap_url = config.sitemap_url
        
        if not effective_sitemap_url:
            raise HTTPException(status_code=400, detail="未配置Sitemap URL")
        
        # 优先使用参数传入的root_url，其次使用配置中的root_url
        effective_root_url = root_url if root_url is not None else config.root_url
        
        # 构建完整的sitemap URL
        sitemap_url_full = effective_sitemap_url
        if not sitemap_url_full.startswith(('http://', 'https://')):
            sitemap_url_full = f"https://{sitemap_url_full}"
        
        parsed = urlparse(sitemap_url_full)
        if not parsed.path or parsed.path == '/':
            root_url_clean = effective_root_url.rstrip('/')
            sitemap_path = config.sitemap_path if config.sitemap_path else '/sitemap.xml'
            sitemap_url_full = f"{parsed.scheme}://{parsed.netloc}{root_url_clean}{sitemap_path}"
        
        logger.info(f"请求解析 Sitemap: sitemap_url={effective_sitemap_url}, root_url={effective_root_url}, full_url={sitemap_url_full}")

        # 获取缓存过期时间（默认 7 天）
        cache_ttl = getattr(config, 'sitemap_cache_ttl', 604800)
        if not cache_ttl or cache_ttl <= 0:
            cache_ttl = 604800  # 默认 7 天
                
        # 检查 Redis 缓存
        redis_client = config_manager.redis_client
        cache_key = f"{SITEMAP_CACHE_PREFIX}{sitemap_url_full}"
                
        logger.info(f"检查 Sitemap 缓存: redis_client={redis_client is not None}, cache_key={cache_key}")

        if redis_client:
            try:
                cached_data = redis_client.get(cache_key)
                logger.info(f"Redis 查询结果: cached_data={'存在' if cached_data else '不存在'}")
                if cached_data:
                    logger.info(f"使用 Redis 缓存的 Sitemap 数据: {cache_key}")
                    result = json.loads(cached_data)
                    return {
                        "status": "success",
                        "paths": result['paths'],
                        "total_urls": result['total_urls'],
                        "from_cache": True,
                        "cache_type": "redis"
                    }
            except Exception as e:
                logger.warning(f"Redis 缓存读取失败: {str(e)}，将重新解析")

        # 解析sitemap
        parser = SitemapParser(sitemap_url_full)
        parser.fetch_sitemap()
        urls = parser.parse()
                
        logger.info(f"成功解析sitemap，共 {len(urls)} 个URL")
        if urls:
            logger.info(f"示例URL: {urls[:5]}")

        if not urls:
            return {
                "status": "success",
                "paths": []
            }

        # 构建树状结构
        path_tree = {}
        for url in urls:
            parsed_url = urlparse(url)
            path = parsed_url.path

            # 跳过根路径
            if path == '/' or not path:
                continue

            # 分割路径为层级
            parts = [p for p in path.split('/') if p]

            # 逐层构建树
            current = path_tree
            for i, part in enumerate(parts):
                full_path = '/' + '/'.join(parts[:i + 1])
                if full_path not in current:
                    # title 使用解码后的中文（便于用户阅读），key 保持编码格式（用于配置匹配）
                    from urllib.parse import unquote
                    decoded_part = unquote(part)
                    current[full_path] = {
                        'title': '/' + decoded_part,
                        'key': full_path,
                        'children': {}
                    }
                current = current[full_path]['children']

        # 转换为列表格式
        def tree_to_list(tree_dict):
            result = []
            for key, node in tree_dict.items():
                item = {
                    'title': node['title'],
                    'key': node['key']
                }
                children = tree_to_list(node['children'])
                if children:
                    item['children'] = children
                result.append(item)
            return result

        paths = tree_to_list(path_tree)

        # 保存到 Redis 缓存
        if redis_client:
            try:
                cache_data = json.dumps({
                    'paths': paths,
                    'urls': urls,  # 保存原始 URL 列表供爬取使用
                    'total_urls': len(urls)
                }, ensure_ascii=False)
                redis_client.setex(cache_key, cache_ttl, cache_data)
                logger.info(f"Sitemap 数据已缓存到 Redis，TTL={cache_ttl}秒, cache_key={cache_key}")
            except Exception as e:
                logger.warning(f"Redis 缓存保存失败: {str(e)}")

        return {
            "status": "success",
            "paths": paths,
            "total_urls": len(urls),
            "from_cache": False,
            "cache_type": "fresh"
        }

    except Exception as e:
        logger.error(f"解析Sitemap路径失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/config", summary="更新爬虫配置")
async def update_crawler_config(config_data: Dict[str, Any]):
    """
    更新爬虫配置并保存到独立配置文件
    """
    try:
        from app.config.config_manager import config_manager
        from app.config.crawler_config import load_crawler_config
        from urllib.parse import urlparse

        # 获取当前配置（用于对比是否有sitemap相关变更）
        old_config = load_crawler_config()

        # 使用 ConfigManager 保存到运行时配置（不写入文件）
        success = config_manager.save_config('crawler', config_data, persist_to_file=False)
        if not success:
            raise HTTPException(status_code=500, detail="保存配置文件失败")

        # 检查 sitemap_url 或 root_url 是否发生变化
        new_sitemap_url = config_data.get('sitemap_url')
        new_root_url = config_data.get('root_url', '')

        sitemap_changed = False
        if new_sitemap_url and new_sitemap_url != old_config.sitemap_url:
            sitemap_changed = True
        elif new_root_url and new_root_url != old_config.root_url:
            sitemap_changed = True

        # 如果sitemap配置发生变化，清除旧的缓存
        if sitemap_changed and old_config.sitemap_url:
            try:
                redis_client = config_manager.redis_client
                if redis_client:
                    # 构建旧的sitemap URL（用于删除缓存）
                    old_sitemap_url = old_config.sitemap_url
                    if not old_sitemap_url.startswith(('http://', 'https://')):
                        old_sitemap_url = f"https://{old_sitemap_url}"

                    old_parsed = urlparse(old_sitemap_url)
                    if not old_parsed.path or old_parsed.path == '/':
                        old_root = old_config.root_url.rstrip('/')
                        old_sitemap_path = old_config.sitemap_path if old_config.sitemap_path else '/sitemap.xml'
                        old_sitemap_url = f"{old_parsed.scheme}://{old_parsed.netloc}{old_root}{old_sitemap_path}"

                    # 删除旧缓存
                    old_cache_key = f"{SITEMAP_CACHE_PREFIX}{old_sitemap_url}"
                    redis_client.delete(old_cache_key)
                    logger.info(f"已清除旧网站的sitemap缓存: {old_cache_key}")

                    # 同时清除所有 sitemap_cache 前缀的缓存（保守策略）
                    try:
                        pattern = f"{SITEMAP_CACHE_PREFIX}*"
                        keys = redis_client.keys(pattern)
                        if keys:
                            redis_client.delete(*keys)
                            logger.info(f"已清除 {len(keys)} 个 sitemap 缓存键")
                    except Exception as e:
                        logger.warning(f"批量清除缓存失败: {str(e)}")
            except Exception as e:
                logger.warning(f"清除旧sitemap缓存失败: {str(e)}")

        # 热加载配置
        reload_success = config_reload_manager.reload_crawler_config()

        return {
            "status": "success",
            "message": "爬虫配置已更新（运行时生效，重启后恢复为配置文件默认值）" +
                       ("，已清除旧的sitemap缓存" if sitemap_changed else ""),
            "hot_reload": reload_success,
            "config": config_data,
            "sitemap_cache_cleared": sitemap_changed
        }
    except Exception as e:
        logger.error(f"更新爬虫配置失败: {str(e)}")
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
        from app.config.config_manager import config_manager

        # 转换前端字段名到配置文件字段名
        config_mapping = {
            'openai_api_key': 'openai_api_key',
            'openai_api_base': 'openai_api_base',
            'openai_model': 'model',
            'openai_embedding_model': 'embedding_model',
            'embedding_dimension': 'embedding_dimension',
            'model_max_input_tokens': 'max_input_tokens',
            'model_max_output_tokens': 'max_output_tokens',
            'rerank_enabled': 'rerank_enabled',
            'rerank_model_name': 'rerank_model_name',
            'rerank_api_key': 'rerank_api_key',
            'rerank_api_base': 'rerank_api_base'
        }

        # 构建新的 LLM 配置
        new_llm_config = {}
        for key, value in config_data.items():
            if key in config_mapping:
                yaml_key = config_mapping[key]
                if value is not None and value != '':
                    # 转换数字类型
                    if key in ['embedding_dimension', 'model_max_input_tokens', 'model_max_output_tokens']:
                        new_llm_config[yaml_key] = int(value)
                    else:
                        new_llm_config[yaml_key] = value

        # 使用 ConfigManager 保存到运行时配置（不写入文件）
        success = config_manager.save_config('llm', new_llm_config, persist_to_file=False)
        if not success:
            raise HTTPException(status_code=500, detail="保存配置文件失败")

        # 热加载配置
        reload_success = config_reload_manager.reload_llm_config()

        return {
            "status": "success",
            "message": "模型配置已更新（运行时生效，重启后恢复为配置文件默认值）",
            "hot_reload": reload_success,
            "config": config_data
        }
    except Exception as e:
        logger.error(f"更新模型配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Redis配置API
@app.get("/api/redis-config", summary="获取Redis配置")
async def get_redis_config_api():
    """
    获取 Redis 配置
    """
    try:
        from app.config.config_manager import config_manager
        redis_data = config_manager.get_config('redis')

        return {
            "status": "success",
            "config": {
                "host": redis_data.get('host', 'localhost'),
                "port": redis_data.get('port', 6379),
                "password": _mask_sensitive_value(redis_data.get('password', ''))
            }
        }
    except Exception as e:
        logger.error(f"获取Redis配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/redis-config", summary="更新Redis配置")
async def update_redis_config(config_data: Dict[str, Any]):
    """
    更新 Redis 配置（支持热加载，无需重启）
    """
    try:
        from app.config.config_manager import config_manager

        # 构建新的 Redis 配置
        new_redis_config = {}
        for key in ['host', 'port', 'password']:
            if key in config_data:
                value = config_data[key]
                # 转换端口为整数
                if key == 'port':
                    new_redis_config[key] = int(value)
                else:
                    new_redis_config[key] = value

        # 使用 ConfigManager 保存到运行时配置（不写入文件）
        success = config_manager.save_config('redis', new_redis_config, persist_to_file=False)
        if not success:
            raise HTTPException(status_code=500, detail="保存配置文件失败")

        # 热加载配置
        reload_success = config_reload_manager.reload_redis_config()

        return {
            "status": "success",
            "message": "Redis配置已更新（运行时生效，重启后恢复为配置文件默认值）",
            "hot_reload": reload_success,
            "config": config_data
        }
    except Exception as e:
        logger.error(f"更新Redis配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/email-config", summary="更新邮件配置")
async def update_email_config(config_data: Dict[str, Any]):
    """
    更新邮件配置（支持热加载，无需重启）
    """
    try:
        from app.config.config_manager import config_manager

        # 转换前端字段名到配置文件字段名
        email_mapping = {
            'smtp_server': 'server',
            'smtp_port': 'port',
            'smtp_user': 'user',
            'smtp_password': 'password',
            'smtp_test_user': 'test_user'
        }

        # 构建新的 SMTP 配置
        new_smtp_config = {}
        for key, value in config_data.items():
            if key in email_mapping:
                yaml_key = email_mapping[key]
                if value is not None and value != '':
                    # 转换端口为整数
                    if key == 'smtp_port':
                        new_smtp_config[yaml_key] = int(value)
                    else:
                        new_smtp_config[yaml_key] = value

        # 使用 ConfigManager 保存到运行时配置（不写入文件）
        success = config_manager.save_config('smtp', new_smtp_config, persist_to_file=False)
        if not success:
            raise HTTPException(status_code=500, detail="保存配置文件失败")

        # 热加载配置
        reload_success = config_reload_manager.reload_email_config()

        return {
            "status": "success",
            "message": "邮件配置已更新（运行时生效，重启后恢复为配置文件默认值）",
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
        from app.services.email_service import send_interview_email
        from app.config.config_manager import config_manager

        # 获取测试邮箱
        smtp_config = config_manager.get_config('smtp')
        test_user = smtp_config.get('test_user')
        if not test_user:
            raise HTTPException(status_code=400, detail="未配置测试邮箱(smtp.test_user)")

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
        import yaml
        from pathlib import Path

        # 读取当前配置文件
        config_path = Path(__file__).parent.parent / "config.yaml"
        if not config_path.exists():
            raise HTTPException(status_code=500, detail="配置文件不存在")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 确保 rerank 部分存在
        if 'rerank' not in config:
            config['rerank'] = {}

        # 更新 Rerank 配置
        rerank_mapping = {
            'enabled': 'enabled',
            'model_name': 'model'
        }

        for key, value in config_data.items():
            if key in rerank_mapping:
                yaml_key = rerank_mapping[key]
                if value is not None and value != '':
                    config['rerank'][yaml_key] = value

        # 保存配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

        logger.info("Rerank 配置已保存到 config.yaml")

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


@app.get("/api/content-config", summary="获取内容处理配置")
async def get_content_config_api():
    """
    获取内容处理配置（滑动窗口切分策略）
    """
    try:
        from app.config.config_manager import config_manager
        content_data = config_manager.get_config('content')

        return {
            "status": "success",
            "config": {
                "chunk_size": content_data.get('chunk_size', 512),
                "chunk_overlap": content_data.get('chunk_overlap', 128),
                "separators": content_data.get('separators', ['\n\n', '\n', '。', '！', '？', '.', '!', '?', ' ']),
                "chunking_mode": content_data.get('chunking_mode', 'semantic'),
                "max_chunks_per_page": content_data.get('max_chunks_per_page', 100),
                "min_chunk_length": content_data.get('min_chunk_length', 100),
            }
        }
    except Exception as e:
        logger.error(f"获取内容处理配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/content-config", summary="更新内容处理配置")
async def update_content_config(config_data: Dict[str, Any]):
    """
    更新内容处理配置（支持热加载，无需重启）
    """
    try:
        from app.config.config_manager import config_manager

        # 构建新的内容处理配置
        new_content_config = {}
        for key in ['chunk_size', 'chunk_overlap', 'chunking_mode', 'max_chunks_per_page', 'min_chunk_length']:
            if key in config_data:
                value = config_data[key]
                # 转换数值类型为整数
                if key in ['chunk_size', 'chunk_overlap', 'max_chunks_per_page', 'min_chunk_length']:
                    new_content_config[key] = int(value)
                else:
                    new_content_config[key] = value

        # 处理分隔符列表
        if 'separators' in config_data and isinstance(config_data['separators'], list):
            new_content_config['separators'] = config_data['separators']

        # 使用 ConfigManager 保存到运行时配置（不写入文件）
        success = config_manager.save_config('content', new_content_config, persist_to_file=False)
        if not success:
            raise HTTPException(status_code=500, detail="保存配置文件失败")

        return {
            "status": "success",
            "message": "内容处理配置已更新（运行时生效，重启后恢复为配置文件默认值）",
            "hot_reload": True
        }
    except Exception as e:
        logger.error(f"更新内容处理配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system-config", summary="获取系统配置")
async def get_system_config():
    """
    获取所有系统配置（按类别分组）
    """
    try:
        # 导入统一配置管理器
        from app.config.config_manager import config_manager

        # 爬虫配置
        crawler_config = load_crawler_config()

        # 模型配置：从 llm.yaml 读取（包含 Rerank 配置）
        llm_config_data = config_manager.get_config('llm')

        # 从嵌套结构中读取配置
        openai_config = llm_config_data.get('openai', {})
        embedding_config = llm_config_data.get('embedding', {})
        rerank_config_nested = llm_config_data.get('rerank', {})

        llm_config = {
            "openai_api_key": _mask_sensitive_value(openai_config.get('api_key', '')),
            "openai_api_base": openai_config.get('api_base', ''),
            "openai_model": openai_config.get('model', 'gpt-4o-mini'),
            "openai_embedding_model": embedding_config.get('model', 'BAAI/bge-m3'),
            "embedding_dimension": embedding_config.get('dimension', 1024),
            "model_max_input_tokens": str(openai_config.get('max_input_tokens', '')),
            "model_max_output_tokens": str(openai_config.get('max_output_tokens', '')),
            "rerank_enabled": rerank_config_nested.get('enabled', False),
            "rerank_model_name": rerank_config_nested.get('model', 'BAAI/bge-reranker-v2-m3'),
            "rerank_api_key": _mask_sensitive_value(rerank_config_nested.get('api_key', '')),
            "rerank_api_base": rerank_config_nested.get('api_base', ''),
        }

        # Rerank 配置：兼容旧版本，从 rerank.yaml 读取（如果存在）
        rerank_config_data = config_manager.get_config('rerank')
        rerank_enabled = rerank_config_data.get('enabled', False)
        if isinstance(rerank_enabled, str):
            rerank_enabled = rerank_enabled.lower() in ('true', '1', 'yes')

        # 如果 rerank.yaml 中有配置，优先使用（向后兼容）
        if rerank_config_data.get('enabled') is not None:
            llm_config['rerank_enabled'] = rerank_enabled
            llm_config['rerank_model_name'] = rerank_config_data.get('model', llm_config['rerank_model_name'])

        rerank_config = {
            "enabled": llm_config['rerank_enabled'],
            "model_name": llm_config['rerank_model_name'],
            "description": "Rerank 模型复用 LLM 的 API Key 和 Base URL"
        }

        # Redis配置：从 redis.yaml 读取
        redis_config_data = config_manager.get_config('redis')
        redis_config = {
            "host": redis_config_data.get('host', 'localhost'),
            "port": redis_config_data.get('port', 6379),
            "password": _mask_sensitive_value(redis_config_data.get('password', '')),
            "description": "Redis运行在Docker容器内，App自动连接"
        }

        # 邮件配置：从 smtp.yaml 读取
        smtp_config_data = config_manager.get_config('smtp')
        email_config = {
            "smtp_server": smtp_config_data.get('server', ''),
            "smtp_port": smtp_config_data.get('port', 587),
            "smtp_user": smtp_config_data.get('user', ''),
            "smtp_password": _mask_sensitive_value(smtp_config_data.get('password', '')),
            "smtp_test_user": smtp_config_data.get('test_user', ''),
        }

        # 定时任务配置
        scheduler_cfg = get_scheduler_config()

        # 内容处理配置：从 content.yaml 读取
        content_config_data = config_manager.get_config('content')
        content_config = {
            "chunk_size": content_config_data.get('chunk_size', 512),
            "chunk_overlap": content_config_data.get('chunk_overlap', 128),
            "separators": content_config_data.get('separators', ['\n\n', '\n', '。', '！', '？', '.', '!', '?', ' ']),
            "chunking_mode": content_config_data.get('chunking_mode', 'semantic'),
            "max_chunks_per_page": content_config_data.get('max_chunks_per_page', 100),
            "min_chunk_length": content_config_data.get('min_chunk_length', 100),
        }

        return {
            "status": "success",
            "config": {
                "crawler": crawler_config.to_dict(),
                "llm": llm_config,
                "rerank": rerank_config,
                "redis": redis_config,
                "email": email_config,
                "scheduler": scheduler_cfg,
                "content": content_config,
            }
        }
    except Exception as e:
        logger.error(f"获取系统配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prompts", summary="获取提示词配置")
async def get_prompts_config():
    """
    获取所有 LLM 提示词配置
    """
    try:
        from app.config.config_manager import config_manager

        # 获取提示词配置
        question_extraction = config_manager.get('prompts.question_extraction_system', '')
        answer_generation = config_manager.get('prompts.answer_generation_system', '')

        # 确保返回的是字符串类型（处理 None 的情况）
        prompts = {
            "question_extraction_system": str(question_extraction) if question_extraction else '',
            "answer_generation_system": str(answer_generation) if answer_generation else '',
        }

        return {
            "status": "success",
            "prompts": prompts
        }
    except Exception as e:
        logger.error(f"获取提示词配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/prompts", summary="更新提示词配置")
async def update_prompts_config(request: dict):
    """
    更新 LLM 提示词配置并保存到 prompts.yaml
    """
    try:
        from app.config.config_manager import config_manager

        # 验证请求数据
        if not isinstance(request, dict):
            raise HTTPException(status_code=400, detail="请求数据格式错误")

        # 获取要更新的提示词
        question_extraction = request.get('question_extraction_system')
        answer_generation = request.get('answer_generation_system')

        if not question_extraction and not answer_generation:
            raise HTTPException(status_code=400, detail="至少需要提供一个提示词")

        # 获取当前 prompts 配置并更新
        current_prompts = config_manager.get('prompts', {})
        if not isinstance(current_prompts, dict):
            current_prompts = {}

        if question_extraction is not None:
            current_prompts['question_extraction_system'] = question_extraction
            logger.info("已更新面试题提取提示词")

        if answer_generation is not None:
            current_prompts['answer_generation_system'] = answer_generation
            logger.info("已更新答案生成提示词")

        # 使用 ConfigManager 保存到运行时配置（不写入文件）
        success = config_manager.save_config('prompts', current_prompts, persist_to_file=False)
        if not success:
            raise HTTPException(status_code=500, detail="保存配置文件失败")

        logger.info("提示词配置已保存到 prompts.yaml")

        return {
            "status": "success",
            "message": "提示词配置已更新（运行时生效，重启后恢复为配置文件默认值）"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新提示词配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


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
    import uuid
    from datetime import datetime

    logger.info(f"开始执行定时爬取任务...")

    # 生成任务ID
    task_id = str(uuid.uuid4())
    task = crawl_task_manager.create_task(task_id)

    # 在后台线程中执行（与手动触发相同逻辑）
    def run_scheduled_crawl():
        try:
            crawl_task_manager.update_task_status(
                task_id,
                TaskStatus.RUNNING,
                start_time=datetime.now().isoformat()
            )

            # 加载配置
            config = load_crawler_config()

            if not config.sitemap_url:
                raise ValueError("未指定 Sitemap URL")

            # 使用异步批量爬虫
            async_crawler = AsyncBatchCrawler(
                config=config,
                max_workers=5,
                timeout_per_url=config.timeout
            )

            # 统计变量
            inserted_count = 0
            total_parsed_questions = 0

            # 定义页面处理回调
            def on_page_processed(page_data):
                nonlocal total_parsed_questions
                try:
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
                        task.parsed_questions += len(questions)
                        task.inserted_questions = inserted_count

                    parsed_questions = llm_service.parse_crawl_results(
                        page_list, on_question_found=on_question_found
                    )
                    total_parsed_questions += len(parsed_questions)
                    task.processed_urls += 1

                except Exception as e:
                    logger.error(f"页面处理失败: {str(e)}")

            # 如果需要从sitemap获取URLs，需要先解析sitemap
            from app.services.sitemap_parser import SitemapParser
            from app.services.url_scanner import URLScanner
            from app.config.firecrawl_config import get_firecrawl_config
            from app.config.config_manager import config_manager
            import json

            firecrawl_cfg = get_firecrawl_config()
            scanner = URLScanner(
                timeout=config.timeout,
                follow_redirects=config.follow_redirects,
                verify_ssl=config.verify_ssl,
                max_content_length=config.max_content_length,
                use_firecrawl=config.use_firecrawl,
                firecrawl_api_url=firecrawl_cfg.api_url,
                firecrawl_api_key=firecrawl_cfg.api_key,
                firecrawl_timeout=firecrawl_cfg.timeout,
                firecrawl_api_version=firecrawl_cfg.api_version,
                firecrawl_only_main_content=firecrawl_cfg.only_main_content,
            )

            sitemap_url = config.sitemap_url
            if not sitemap_url.startswith(('http://', 'https://')):
                sitemap_url = f"https://{sitemap_url}"

            # 如果只是域名（没有路径），自动添加 sitemap.xml 路径
            from urllib.parse import urlparse
            parsed = urlparse(sitemap_url)
            if not parsed.path or parsed.path == '/':
                root_url = config.root_url.rstrip('/')
                sitemap_path = config.sitemap_path if config.sitemap_path else '/sitemap.xml'
                sitemap_url = f"{parsed.scheme}://{parsed.netloc}{root_url}{sitemap_path}"
                logger.info(f"自动补全 Sitemap URL: {sitemap_url}")

            if config.check_robots_txt:
                robots_txt = scanner.check_robots_txt(sitemap_url, config.robots_path)
                if robots_txt and 'Disallow: /' in robots_txt:
                    raise PermissionError("robots.txt 禁止爬取此网站")

            # 检查 Redis 缓存中的 URL 列表
            redis_client = config_manager.redis_client
            cache_key = f"{SITEMAP_CACHE_PREFIX}{sitemap_url}"
            urls = []
            from_cache = False
            
            if redis_client:
                try:
                    cached_data = redis_client.get(cache_key)
                    if cached_data:
                        logger.info(f"定时爬取使用 Redis 缓存的 Sitemap 数据: {cache_key}")
                        result = json.loads(cached_data)
                        if 'urls' in result and result['urls']:
                            urls = result['urls']
                            from_cache = True
                            logger.info(f"从缓存获取到 {len(urls)} 个 URL")
                except Exception as e:
                    logger.warning(f"Redis 缓存读取失败: {str(e)}，将重新解析")

            # 如果缓存中没有 URL，则解析 sitemap
            if not urls:
                logger.info(f"开始解析 Sitemap: {sitemap_url}")
                parser = SitemapParser(sitemap_url)
                parser.fetch_sitemap()
                urls = parser.parse()
                logger.info(f"Sitemap 解析完成，共获取到 {len(urls)} 个 URL")
            else:
                logger.info(f"使用缓存的 Sitemap URL 列表，共 {len(urls)} 个 URL")

            from app.services.url_filter import URLFilter
            url_filter = URLFilter.from_config(config)
            if config.url_include_patterns or config.url_exclude_patterns:
                urls = url_filter.filter_urls(urls)

            if config.max_urls and len(urls) > config.max_urls:
                urls = urls[:config.max_urls]

            # 执行批量爬取
            results = async_crawler.crawl_batch(
                urls=urls,
                page_processed_callback=on_page_processed,
                stop_flag=task.stop_flag
            )

            stats = async_crawler.get_stats()

            result = {
                "status": "success",
                "message": "定时爬取完成",
                "statistics": stats.to_dict(),
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

            # 更新Redis
            try:
                if vector_service.redis_client:
                    result_json = json.dumps(result)
                    vector_service.redis_client.setex("crawl:last_result", 86400, result_json)
                    crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    vector_service.redis_client.setex("crawl:last_time", 86400, crawl_time)
            except Exception as e:
                logger.warning(f"存储结果到 Redis 失败: {str(e)}")

            async_crawler.shutdown()
            logger.info(f"定时爬取任务完成: {total_parsed_questions} 个问题")

        except Exception as e:
            logger.error(f"定时爬取任务失败: {str(e)}")
            crawl_task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                end_time=datetime.now().isoformat(),
                error_message=str(e)
            )
            try:
                async_crawler.shutdown()
            except:
                pass

    # 启动后台线程
    from threading import Thread
    thread = Thread(target=run_scheduled_crawl, daemon=True)
    thread.start()


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


@app.get("/api/crawl/test-sitemap", summary="测试 Sitemap 解析")
async def test_sitemap(sitemap_url: str = Query(..., description="要测试的 Sitemap URL")):
    """
    测试 Sitemap 解析，返回解析结果和URL列表
    
    参数:
        sitemap_url: 要测试的 Sitemap URL
    """
    try:
        from app.services.sitemap_parser import SitemapParser

        logger.info(f"测试 Sitemap: {sitemap_url}")

        # 解析sitemap
        parser = SitemapParser(full_sitemap_url)
        parser.fetch_sitemap()
        urls = parser.parse()

        return {
            "status": "success",
            "sitemap_url": sitemap_url,
            "total_urls": len(urls),
            "sample_urls": urls[:10],  # 只返回前10个作为样本
            "urls": urls if len(urls) <= 100 else urls[:100]  # 最多返回100个
        }
    except Exception as e:
        logger.error(f"Sitemap 测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sitemap 测试失败: {str(e)}")


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
