#!/usr/bin/env python3
"""
API 端点测试脚本
测试所有主要的 API 端点是否正常工作
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

# 颜色输出
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def test_endpoint(method, path, expected_status=200, data=None, params=None, description=""):
    """测试单个端点"""
    url = f"{BASE_URL}{path}"
    
    try:
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, json=data, params=params)
        elif method == "PUT":
            response = requests.put(url, json=data, params=params)
        elif method == "DELETE":
            response = requests.delete(url, params=params)
        
        status_ok = response.status_code == expected_status
        status_color = GREEN if status_ok else RED
        
        print(f"{status_color}[{method}] {path:60s} -> {response.status_code} (期望: {expected_status}){RESET}")
        
        if not status_ok:
            print(f"  {RED}错误响应: {response.text[:200]}{RESET}")
            return False
        
        if description:
            print(f"  {YELLOW}✓ {description}{RESET}")
        
        return True
        
    except Exception as e:
        print(f"{RED}[{method}] {path:60s} -> 异常: {str(e)}{RESET}")
        return False

def main():
    print("=" * 80)
    print("开始测试 API 端点")
    print("=" * 80)
    print()
    
    # 获取一个题目ID用于测试
    print(f"{YELLOW}步骤 1: 获取测试题目ID{RESET}")
    response = requests.get(f"{BASE_URL}/api/questions", params={"limit": 1})
    if response.status_code != 200:
        print(f"{RED}无法获取题目列表{RESET}")
        return
    
    questions = response.json().get("questions", [])
    if not questions:
        print(f"{RED}没有可用的题目{RESET}")
        return
    
    test_question_id = questions[0]["id"]
    print(f"{GREEN}✓ 使用题目ID: {test_question_id}{RESET}\n")
    
    passed = 0
    failed = 0
    
    # ========== 基础端点 ==========
    print(f"{YELLOW}========== 基础端点 =========={RESET}")
    
    if test_endpoint("GET", "/api/questions/count", description="获取题目总数"):
        passed += 1
    else:
        failed += 1
    
    if test_endpoint("GET", "/api/questions", params={"limit": 5, "offset": 0}, description="获取题目列表（分页）"):
        passed += 1
    else:
        failed += 1
    
    if test_endpoint("GET", f"/api/questions/{test_question_id}", description="获取单个题目详情"):
        passed += 1
    else:
        failed += 1
    
    print()
    
    # ========== 推荐端点 ==========
    print(f"{YELLOW}========== 推荐端点 =========={RESET}")
    
    if test_endpoint("GET", "/api/questions/recommended", 
                     params={"limit": 5, "exclude_mastered": True, "use_rerank": True},
                     description="获取推荐题目（带 Rerank）"):
        passed += 1
    else:
        failed += 1
    
    if test_endpoint("GET", "/api/questions/recommended", 
                     params={"limit": 5, "exclude_mastered": False, "use_rerank": False},
                     description="获取推荐题目（不带 Rerank）"):
        passed += 1
    else:
        failed += 1
    
    print()
    
    # ========== 搜索端点 ==========
    print(f"{YELLOW}========== 搜索端点 =========={RESET}")
    
    if test_endpoint("GET", "/api/questions/search", 
                     params={"query": "面试", "limit": 5},
                     description="搜索题目"):
        passed += 1
    else:
        failed += 1
    
    print()
    
    # ========== 反馈端点 ==========
    print(f"{YELLOW}========== 反馈端点 =========={RESET}")
    
    if test_endpoint("POST", f"/api/questions/{test_question_id}/feedback", 
                     params={"mastery_level": 2},
                     description="提交掌握程度反馈"):
        passed += 1
    else:
        failed += 1
    
    if test_endpoint("GET", f"/api/questions/{test_question_id}/feedback", 
                     description="获取题目反馈"):
        passed += 1
    else:
        failed += 1
    
    if test_endpoint("POST", f"/api/questions/{test_question_id}/feedback", 
                     params={"is_favorite": True},
                     description="收藏题目"):
        passed += 1
    else:
        failed += 1
    
    if test_endpoint("POST", f"/api/questions/{test_question_id}/feedback", 
                     params={"is_wrong_book": True},
                     description="加入错题本"):
        passed += 1
    else:
        failed += 1
    
    print()
    
    # ========== 用户数据端点 ==========
    print(f"{YELLOW}========== 用户数据端点 =========={RESET}")
    
    if test_endpoint("GET", "/api/users/me/favorites", description="获取收藏列表"):
        passed += 1
    else:
        failed += 1
    
    if test_endpoint("GET", "/api/users/me/wrong-books", description="获取错题本"):
        passed += 1
    else:
        failed += 1
    
    if test_endpoint("GET", "/api/users/me/hidden-questions", description="获取隐藏题目列表"):
        passed += 1
    else:
        failed += 1
    
    print()
    
    # ========== 重要性更新端点 ==========
    print(f"{YELLOW}========== 重要性更新端点 =========={RESET}")
    
    if test_endpoint("PUT", f"/api/questions/{test_question_id}/importance", 
                     params={"importance_score": 0.8},
                     description="更新题目重要性"):
        passed += 1
    else:
        failed += 1
    
    # 恢复原值
    test_endpoint("PUT", f"/api/questions/{test_question_id}/importance", 
                  params={"importance_score": 0.5})
    
    print()
    
    # ========== 隐藏/删除端点 ==========
    print(f"{YELLOW}========== 隐藏/删除端点 =========={RESET}")
    
    if test_endpoint("POST", f"/api/questions/{test_question_id}/hide", 
                     description="隐藏题目（软删除）"):
        passed += 1
    else:
        failed += 1
    
    # 取消隐藏
    test_endpoint("POST", f"/api/questions/{test_question_id}/feedback", 
                  params={"hide_from_recommendation": False})
    
    if test_endpoint("DELETE", f"/api/users/me/hidden-questions/{test_question_id}", 
                     description="永久删除题目（从隐藏列表）"):
        passed += 1
    else:
        failed += 1
    
    print()
    
    # ========== 系统端点 ==========
    print(f"{YELLOW}========== 系统端点 =========={RESET}")
    
    if test_endpoint("GET", "/api/crawl/status", description="获取爬取状态"):
        passed += 1
    else:
        failed += 1
    
    if test_endpoint("POST", "/api/system/weights/update", description="手动更新权重"):
        passed += 1
    else:
        failed += 1
    
    print()
    
    # ========== 调试端点 ==========
    print(f"{YELLOW}========== 调试端点 =========={RESET}")
    
    if test_endpoint("GET", "/api/debug/vector-status", description="查看向量数据库状态"):
        passed += 1
    else:
        failed += 1
    
    print()
    
    # ========== 总结 ==========
    print("=" * 80)
    total = passed + failed
    print(f"{GREEN}通过: {passed}/{total}{RESET}")
    if failed > 0:
        print(f"{RED}失败: {failed}/{total}{RESET}")
    print("=" * 80)
    
    if failed == 0:
        print(f"\n{GREEN}🎉 所有端点测试通过！{RESET}\n")
        return 0
    else:
        print(f"\n{RED}⚠️  有 {failed} 个端点测试失败{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
