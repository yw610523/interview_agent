#!/usr/bin/env python3
"""
重置所有题目的学习次数（review_count）和复习时间

用于清空用户的学习进度，重新开始学习。
通常在测试或数据迁移时使用。
"""
import redis
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 连接 Redis
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(redis_url)

print(f"连接到 Redis: {redis_url}")

# 获取所有反馈记录
pattern = "feedback:*"
keys = redis_client.keys(pattern)

print(f"找到 {len(keys)} 个反馈记录")

reset_count = 0
for key in keys:
    # 检查是否有 review_count 字段
    if redis_client.hexists(key, 'review_count'):
        # 重置 review_count 为 0
        redis_client.hset(key, 'review_count', '0')
        # 清空 last_reviewed_at
        redis_client.hset(key, 'last_reviewed_at', '')
        # 清空 next_review_at
        redis_client.hset(key, 'next_review_at', '')
        
        question_id = redis_client.hget(key, 'question_id').decode()
        print(f"已重置: {question_id}")
        reset_count += 1

print(f"\n✅ 完成！共重置 {reset_count} 个题目的学习记录")
