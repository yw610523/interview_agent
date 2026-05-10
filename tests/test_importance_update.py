"""
测试 importance_score 更新功能
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_update_importance():
    """测试更新题目重要性"""
    
    # 首先获取一个题目ID
    print("1. 获取题目列表...")
    response = requests.get(f"{BASE_URL}/api/questions?limit=1")
    if response.status_code != 200:
        print(f"❌ 获取题目列表失败: {response.status_code}")
        return
    
    questions = response.json().get('questions', [])
    if not questions:
        print("❌ 没有可用的题目")
        return
    
    question_id = questions[0]['id']
    original_importance = questions[0].get('importance_score', 0)
    
    print(f"✓ 找到题目: {questions[0]['title'][:50]}...")
    print(f"  ID: {question_id}")
    print(f"  原始重要性: {original_importance}")
    
    # 测试更新重要性
    new_importance = 0.9
    print(f"\n2. 更新重要性为 {new_importance}...")
    response = requests.put(
        f"{BASE_URL}/api/questions/{question_id}/importance",
        params={'importance_score': new_importance}
    )
    
    if response.status_code != 200:
        print(f"❌ 更新失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return
    
    result = response.json()
    print(f"✓ 更新成功: {result}")
    
    # 验证更新是否生效
    print(f"\n3. 验证更新是否生效...")
    response = requests.get(f"{BASE_URL}/api/questions?limit=1&offset=0")
    if response.status_code == 200:
        updated_question = response.json().get('questions', [{}])[0]
        updated_importance = updated_question.get('importance_score')
        
        if abs(updated_importance - new_importance) < 0.01:
            print(f"✓ 验证成功！重要性已更新为: {updated_importance}")
        else:
            print(f"❌ 验证失败！期望 {new_importance}, 实际 {updated_importance}")
    
    # 恢复原始值
    print(f"\n4. 恢复原始重要性 {original_importance}...")
    response = requests.put(
        f"{BASE_URL}/api/questions/{question_id}/importance",
        params={'importance_score': original_importance}
    )
    
    if response.status_code == 200:
        print(f"✓ 恢复成功")
    else:
        print(f"⚠️  恢复失败: {response.status_code}")

if __name__ == "__main__":
    try:
        test_update_importance()
    except Exception as e:
        print(f"❌ 测试出错: {str(e)}")
        import traceback
        traceback.print_exc()
