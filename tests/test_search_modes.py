"""
搜索模式对比测试：语义检索 vs 混合检索
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_search_modes():
    """测试不同搜索模式的效果"""
    
    # 测试查询
    test_queries = [
        "Java 多线程",
        "Redis 缓存",
        "Spring Bean",
        "消息队列",
        "数据库索引"
    ]
    
    print("=" * 80)
    print("搜索模式对比测试：语义检索 vs 混合检索")
    print("=" * 80)
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"查询: {query}")
        print(f"{'='*80}")
        
        # 测试语义检索
        print("\n[1] 语义检索 (semantic):")
        try:
            response = requests.get(
                f"{BASE_URL}/api/questions/search",
                params={
                    "query": query,
                    "limit": 5,
                    "search_mode": "semantic"
                }
            )
            semantic_results = response.json()
            
            if semantic_results.get('results'):
                for i, item in enumerate(semantic_results['results'][:3], 1):
                    score = item.get('score', 0)
                    title = item.get('title', '')[:60]
                    print(f"  {i}. [Score: {score:.4f}] {title}...")
            else:
                print("  无结果")
        except Exception as e:
            print(f"  错误: {e}")
        
        # 测试混合检索
        print("\n[2] 混合检索 (hybrid):")
        try:
            response = requests.get(
                f"{BASE_URL}/api/questions/search",
                params={
                    "query": query,
                    "limit": 5,
                    "search_mode": "hybrid"
                }
            )
            hybrid_results = response.json()
            
            if hybrid_results.get('results'):
                for i, item in enumerate(hybrid_results['results'][:3], 1):
                    score = item.get('score', 0)
                    title = item.get('title', '')[:60]
                    print(f"  {i}. [Score: {score:.4f}] {title}...")
            else:
                print("  无结果")
        except Exception as e:
            print(f"  错误: {e}")
        
        # 对比分析
        if semantic_results.get('results') and hybrid_results.get('results'):
            semantic_ids = [r['id'] for r in semantic_results['results']]
            hybrid_ids = [r['id'] for r in hybrid_results['results']]
            
            # 计算重合度
            common = set(semantic_ids) & set(hybrid_ids)
            overlap = len(common) / min(len(semantic_ids), len(hybrid_ids)) * 100
            
            print(f"\n[对比分析]")
            print(f"  - 前5名重合度: {len(common)}/5 ({overlap:.0f}%)")
            
            if overlap < 100:
                print(f"  - 差异题目:")
                only_semantic = set(semantic_ids) - set(hybrid_ids)
                only_hybrid = set(hybrid_ids) - set(semantic_ids)
                
                if only_semantic:
                    print(f"    * 仅语义检索返回: {len(only_semantic)} 个")
                if only_hybrid:
                    print(f"    * 仅混合检索返回: {len(only_hybrid)} 个")
    
    print(f"\n{'='*80}")
    print("测试完成!")
    print(f"{'='*80}")
    print("\n说明:")
    print("  - 语义检索: 基于向量相似度，理解查询的语义含义")
    print("  - 混合检索: 结合关键词匹配 + 向量相似度，兼顾精确性和语义理解")
    print("  - 如果重合度低，说明两种检索方式返回的结果有明显差异")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    test_search_modes()
