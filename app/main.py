from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
import uvicorn
import logging
from pathlib import Path
import json

# 导入爬虫相关模块
from app.services.sitemap_crawler import SitemapCrawler
from app.config.crawler_config import (
    CrawlerConfig,
    get_config_from_env,
    get_scheduler_config,
)


# 导入大模型和向量服务
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService, VectorRecord

# 定时任务相关
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

app = FastAPI(title="Interview AI Agent")

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 全局变量存储最近一次爬取结果
last_crawl_result: Optional[Dict[str, Any]] = None

# 初始化服务
llm_service = LLMService()
vector_service = VectorService()


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


@app.post("/questions/ingest", summary="接收并存储面试题")
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
        count = vector_service.insert_questions(records)

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
            nonlocal inserted_count, total_parsed_questions
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

        # 保存结果
        if config.save_results:
            filepath = crawler.save_results()
            logger.info(f"结果已保存到: {filepath}")

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


@app.get("/crawl/run", summary="手动触发爬虫任务")
async def trigger_crawl():
    """
    手动触发爬虫任务
    """
    try:
        result = run_crawler()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/crawl/status", summary="获取爬虫状态")
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
                next_run = jobs[0].next_run_time
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


@app.get("/questions/search", summary="搜索面试题")
async def search_questions(
    query: str,
    limit: int = Query(10, ge=1, le=50),
    tags: Optional[List[str]] = Query(None),
    difficulty: Optional[List[str]] = Query(None),
    category: Optional[List[str]] = Query(None),
):
    """
    根据关键词搜索面试题

    参数:
        query: 搜索关键词
        limit: 返回数量限制
        tags: 标签过滤（如：Python,算法）
        difficulty: 难度过滤（easy/medium/hard）
        category: 分类过滤
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

        # 搜索
        results = vector_service.search(query, limit, filters if filters else None)

        return SearchResult(query=query, results=results, total=len(results))

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/questions/{question_id}", summary="获取单个面试题详情")
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


@app.delete("/questions/{question_id}", summary="删除面试题")
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


@app.get("/questions", summary="获取所有面试题")
async def get_all_questions(
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)
):
    """
    获取所有面试题列表（分页）
    """
    try:
        all_questions = vector_service.get_all()

        # 简单分页
        total = len(all_questions)
        paginated = all_questions[offset : offset + limit]

        return {
            "questions": paginated,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Get all questions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/questions/count", summary="获取面试题总数")
async def get_question_count():
    """
    获取向量数据库中面试题的总数
    """
    try:
        count = vector_service.count()
        return {"count": count}
    except Exception as e:
        logger.error(f"Count error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/vector-status", summary="调试：查看向量数据库状态")
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


@app.post("/debug/reset-index", summary="调试：重置向量索引")
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


@app.post("/questions/generate", summary="使用大模型生成答案")
async def generate_answer(question: str):
    """
    使用大模型为给定问题生成答案
    """
    try:
        answer = llm_service.generate_answer(question)
        return {"question": question, "answer": answer}
    except Exception as e:
        logger.error(f"Generate answer error: {str(e)}")
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