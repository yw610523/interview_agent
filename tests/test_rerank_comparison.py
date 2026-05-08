#!/usr/bin/env python3
"""
对比测试 Rerank 开启/关闭的效果
"""
import requests
import json

def test_rerank_comparison():
    print("=" * 80)
    print("Rerank 效果对比测试")
    print("=" * 80)
    
    # 测试参数
    limit = 10
    exclude_mastered = True
    
    print(f"\n[TEST] 测试配置:")
    print(f"  - 返回数量: {limit}")
    print(f"  - 排除已掌握: {exclude_mastered}")
    print()
    
    # 1. 关闭 Rerank
    print("1. 关闭 Rerank (use_rerank=false)")
    print("-" * 80)
    r1 = requests.get(
        'http://localhost:8000/api/questions/recommended',
        params={
            'limit': limit,
            'exclude_mastered': exclude_mastered,
            'use_rerank': False
        }
    )
    
    if r1.status_code != 200:
        print(f"[FAIL] 请求失败: {r1.status_code}")
        return
    
    data1 = r1.json()
    questions_without_rerank = data1.get('questions', [])
    
    print(f"[OK] 返回 {len(questions_without_rerank)} 道题目\n")
    print("前 5 道题目:")
    for i, q in enumerate(questions_without_rerank[:5], 1):
        priority = q.get('priority_score', 0)
        title = q.get('title', '')[:50]
        mastery = q.get('mastery_level', 0)
        print(f"  {i}. [优先级:{priority:.2f}] [掌握:{mastery}] {title}...")
    
    # 2. 开启 Rerank
    print("\n\n2. 开启 Rerank (use_rerank=true)")
    print("-" * 80)
    r2 = requests.get(
        'http://localhost:8000/api/questions/recommended',
        params={
            'limit': limit,
            'exclude_mastered': exclude_mastered,
            'use_rerank': True
        }
    )
    
    if r2.status_code != 200:
        print(f"[FAIL] 请求失败: {r2.status_code}")
        print(f"错误信息: {r2.json()}")
        return
    
    data2 = r2.json()
    questions_with_rerank = data2.get('questions', [])
    
    print(f"[OK] 返回 {len(questions_with_rerank)} 道题目\n")
    print("前 5 道题目:")
    for i, q in enumerate(questions_with_rerank[:5], 1):
        priority = q.get('priority_score', 0)
        rerank_score = q.get('rerank_score', 0)
        title = q.get('title', '')[:50]
        mastery = q.get('mastery_level', 0)
        print(f"  {i}. [优先级:{priority:.2f}] [Rerank:{rerank_score:.3f}] [掌握:{mastery}] {title}...")
    
    # 3️⃣ 对比差异
    print("\n\n" + "=" * 80)
    print("[ANALYSIS] 排序差异分析")
    print("=" * 80)
    
    # 提取题目 ID
    ids_without = [q['id'] for q in questions_without_rerank]
    ids_with = [q['id'] for q in questions_with_rerank]
    
    # 找出排名变化的题目
    changes = []
    for idx, qid in enumerate(ids_with):
        if qid in ids_without:
            old_rank = ids_without.index(qid) + 1
            new_rank = idx + 1
            if old_rank != new_rank:
                change = old_rank - new_rank
                direction = "UP" if change > 0 else "DOWN"
                title = next(q['title'] for q in questions_with_rerank if q['id'] == qid)[:40]
                changes.append({
                    'title': title,
                    'old_rank': old_rank,
                    'new_rank': new_rank,
                    'change': change,
                    'direction': direction
                })
    
    if changes:
        print(f"\n发现 {len(changes)} 道题目排名发生变化:\n")
        # 按变化幅度排序
        changes.sort(key=lambda x: abs(x['change']), reverse=True)
        for c in changes[:10]:  # 只显示前10个变化
            print(f"  {c['direction']} {c['title']}...")
            print(f"     排名: {c['old_rank']} → {c['new_rank']} (变化: {c['change']:+d})")
    else:
        print("\n[INFO] 排名没有变化（可能原因：）")
        print("  1. 候选题目太少")
        print("  2. 用户反馈数据不足（收藏/错题本）")
        print("  3. Rerank API 未正确配置")
    
    # 4️⃣ 统计信息
    print("\n\n" + "=" * 80)
    print("[STATS] 统计信息")
    print("=" * 80)
    
    # 计算排名相关度
    same_top3 = len(set(ids_without[:3]) & set(ids_with[:3]))
    same_top5 = len(set(ids_without[:5]) & set(ids_with[:5]))
    
    print(f"\n前 3 名重合度: {same_top3}/3 ({same_top3/3*100:.0f}%)")
    print(f"前 5 名重合度: {same_top5}/5 ({same_top5/5*100:.0f}%)")
    
    if same_top3 < 3 or same_top5 < 5:
        print("\n[SUCCESS] Rerank 生效了！排序有明显变化")
    else:
        print("\n[WARNING] Rerank 可能未生效或效果不明显")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    test_rerank_comparison()
