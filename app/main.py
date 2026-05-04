# app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import uvicorn

app = FastAPI(title="Interview AI Agent")

# 定义面试题数据模型
class InterviewQuestion(BaseModel):
    title: str
    answer: str
    source_url: HttpUrl
    tags: List[str]
    importance_score: Optional[float] = 0.0

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)