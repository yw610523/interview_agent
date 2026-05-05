# app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
import uvicorn
import logging
from pathlib import Path

# 导入爬虫相关模块
from app.services.sitemap_crawler import SitemapCrawler, CrawlStats
from app.config.crawler_config import CrawlerConfig, get_config_from_env, get_scheduler_config
from app.services.url_scanner import ScanResult

# 定时任务相关
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

app = FastAPI(title="Interview AI Agent")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量存储最近一次爬取结果
last_crawl_result: Optional[Dict[str, Any]] = None

# 定义面试题数据模型
class InterviewQuestion(BaseModel):
    title: str
    answer: str
    source_url: HttpUrl
    tags: List[str]
    importance_score: Optional[float] = 0.0

# 爬取结果模型
class CrawlResult(BaseModel):
    status: str
    message: str
    statistics: Optional[Dict[str, Any]] = None
    result_count: Optional[int] = 0

@app.post("/questions/ingest", summary="接收并存储面试题")
async def ingest_question(questions: List[InterviewQuestion]):
    """
    接收来自爬虫或大模型分析后的面试题列表，并存入向量数据库
    """
    try:
        # TODO: 1. 调用向量生成服务 (Embedding)
        # TODO: 2. 存入 Redis Stack / Vector Store
        # TODO: 3. 进行去重校验
        return {"status": "success", "count": len(questions), "message": "数据已入库"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_crawler() -> Dict[str, Any]:
    """
    执行爬虫任务
    """
    global last_crawl_result
    
    logger.info("开始执行定时爬虫任务...")
    
    try:
        # 加载配置
        DEFAULT_CONFIG_PATH = Path(__file__).parent / 'config' / 'crawler_config.json'
        
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
        results = crawler.crawl()
        
        # 打印报告
        crawler.print_report()
        
        # 保存结果
        if config.save_results:
            filepath = crawler.save_results()
            logger.info(f"结果已保存到: {filepath}")
        
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
                "end_time": stats.end_time
            },
            "result_count": len(results)
        }
        
        # 更新全局变量
        last_crawl_result = result
        
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


@app.get("/crawl/status", summary="获取最近一次爬取状态")
async def get_crawl_status():
    """
    获取最近一次爬取任务的状态和结果
    """
    if last_crawl_result is None:
        return {"status": "info", "message": "尚未执行过爬取任务"}
    return last_crawl_result


# 定时任务调度器
scheduler = BackgroundScheduler()

# 从环境变量获取定时配置
scheduler_config = get_scheduler_config()
SCHEDULER_HOUR = scheduler_config['hour']
SCHEDULER_MINUTE = scheduler_config['minute']

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
    logger.info(f"定时任务调度器已启动，每天 {SCHEDULER_HOUR}:{SCHEDULER_MINUTE:02d} 执行爬虫任务")
    
    # 启动 FastAPI 服务
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    # 优雅关闭调度器
    scheduler.shutdown()