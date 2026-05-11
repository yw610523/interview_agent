#!/usr/bin/env python3
"""
强制重建向量索引脚本

用于解决向量维度不匹配问题。
会删除所有现有索引和数据，使用当前配置重新创建。
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_service import VectorService
from app.config.config_manager import config_manager


def force_rebuild_index():
    """强制重建索引"""
    print("=" * 60)
    print("强制重建向量索引")
    print("=" * 60)
    
    # 创建 VectorService 实例
    vector_service = VectorService()
    
    # 1. 获取当前配置的维度
    embedding_dim = config_manager.get('llm.embedding.dimension') or \
                   config_manager.get('llm.embedding_dimension') or \
                   int(os.getenv("EMBEDDING_DIMENSION", "1024"))
    
    print(f"\n📊 当前配置的向量维度: {embedding_dim}")
    
    # 2. 删除旧索引
    try:
        index_name = vector_service.index_name
        print(f"🗑️  正在删除旧索引: {index_name}")
        vector_service.redis_client.ft(index_name).dropindex(delete_documents=True)
        print(f"✅ 旧索引已删除")
    except Exception as e:
        print(f"⚠️  删除索引失败（可能不存在）: {str(e)}")
    
    # 3. 重建索引
    print(f"\n🔨 正在创建新索引（维度: {embedding_dim}）...")
    success = vector_service._ensure_index()
    
    if success:
        print(f"✅ 索引重建成功！")
        print(f"\n📝 索引信息:")
        print(f"   - 名称: {vector_service.index_name}")
        print(f"   - 维度: {embedding_dim}")
        print(f"   - 距离度量: COSINE")
    else:
        print(f"❌ 索引重建失败")
        return False
    
    # 4. 验证索引
    print(f"\n🔍 验证索引...")
    try:
        info = vector_service.redis_client.ft(vector_service.index_name).info()
        if isinstance(info, dict):
            num_docs = info.get('num_docs', 0)
            attributes = info.get('attributes', [])
        else:
            num_docs = getattr(info, 'num_docs', 0)
            attributes = getattr(info, 'attributes', [])
        
        print(f"✅ 索引验证通过")
        print(f"   - 文档数: {num_docs}")
        print(f"   - 字段数: {len(attributes)}")
        
        # 检查 embedding 字段的维度
        for attr in attributes:
            if isinstance(attr, dict) and attr.get('identifier') == 'embedding':
                dim = attr.get('dims', 'N/A')
                print(f"   - Embedding 维度: {dim}")
                if str(dim) != str(embedding_dim):
                    print(f"⚠️  警告: 索引维度 ({dim}) 与配置 ({embedding_dim}) 不匹配！")
                break
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
        return False
    
    print("\n" + "=" * 60)
    print("索引重建完成！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = force_rebuild_index()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 重建失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
