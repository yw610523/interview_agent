#!/usr/bin/env python3
"""
重建向量索引脚本

用于解决向量维度不匹配的问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.vector_service import vector_service
from app.config.config_manager import config_manager


def rebuild_index():
    """重建向量索引"""
    print("=" * 60)
    print("重建向量索引")
    print("=" * 60)
    
    # 获取当前配置的维度
    embedding_dim = config_manager.get('llm.embedding.dimension') or \
                   config_manager.get('llm.embedding_dimension') or \
                   int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    
    print(f"\n当前配置的向量维度: {embedding_dim}")
    print(f"索引名称: {vector_service.index_name}")
    
    # 检查 Redis 连接
    if not vector_service.redis_client:
        print("\n❌ Redis 客户端未初始化，请检查 Redis 配置")
        return False
    
    try:
        # 检查索引是否存在
        index_info = vector_service.redis_client.ft(vector_service.index_name).info()
        print(f"\n当前索引信息:")
        print(f"  - 索引名称: {index_info.get('index_name')}")
        print(f"  - 向量维度: {index_info.get('attributes', [{}])[0].get('dims', 'unknown')}")
        print(f"  - 文档数量: {index_info.get('num_docs', 0)}")
    except Exception as e:
        if "Unknown index name" in str(e):
            print("\n索引不存在，将创建新索引")
        else:
            print(f"\n❌ 获取索引信息失败: {e}")
            return False
    
    # 询问是否继续
    print("\n⚠️  重建索引将删除现有索引并重新创建")
    print("⚠️  已存储的问题不会被删除，但需要重新生成向量")
    
    response = input("\n是否继续？(yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("已取消")
        return False
    
    # 删除旧索引
    try:
        vector_service.redis_client.ft(vector_service.index_name).dropindex(delete_documents=False)
        print("✅ 旧索引已删除")
    except Exception as e:
        if "Unknown index name" not in str(e):
            print(f"❌ 删除索引失败: {e}")
            return False
    
    # 重新初始化索引
    vector_service.index_initialized = False
    success = vector_service._ensure_index()
    
    if success:
        print("\n✅ 新索引创建成功")
        print(f"   向量维度: {embedding_dim}")
        print("\n提示:")
        print("  - 现有问题需要重新爬取或手动重新生成向量")
        print("  - 可以通过前端触发重新爬取")
    else:
        print("\n❌ 创建索引失败")
    
    return success


if __name__ == "__main__":
    success = rebuild_index()
    sys.exit(0 if success else 1)
