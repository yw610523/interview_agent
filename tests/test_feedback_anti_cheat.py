#!/usr/bin/env python3
"""
测试反馈服务的防刷分机制
测试场景：交替点击 mastery_level=1 和 mastery_level=5
预期结果：复习次数不应该无端增加
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.feedback_service import FeedbackService

def test_alternating_mastery():
    """测试交替评分情况"""
    print("=" * 60)
    print("测试：交替点击 mastery_level=1 和 mastery_level=5")
    print("=" * 60)
    
    service = FeedbackService()
    test_question_id = "test-alternating-001"
    
    # 清理测试数据
    key = service._get_feedback_key(test_question_id)
    if service.redis_client:
        service.redis_client.delete(key)
    
    print("\n【初始状态】")
    feedback = service.get_feedback(test_question_id)
    if feedback:
        print(f"  掌握程度: {feedback.mastery_level}")
        print(f"  复习次数: {feedback.review_count}")
        print(f"  历史最高: {feedback.historical_max_mastery}")
    else:
        print("  无反馈记录")
    
    # 模拟交替点击
    test_sequence = [
        (1, "首次评分为1"),
        (5, "从1提升到5（应该增加）"),
        (1, "从5降到1（不应该增加）"),
        (5, "从1升到5但未突破历史（不应该增加）"),
        (1, "从5降到1（不应该增加）"),
        (5, "再次从1升到5但未突破历史（不应该增加）"),
        (3, "从5降到3（不应该增加）"),
        (5, "从3升到5但未突破历史（不应该增加）"),
    ]
    
    print("\n【测试过程】")
    for level, description in test_sequence:
        print(f"\n操作: {description}")
        print(f"  设置 mastery_level={level}")
        
        success = service.submit_feedback(test_question_id, {'mastery_level': level})
        
        feedback = service.get_feedback(test_question_id)
        if feedback:
            print(f"  ✓ 掌握程度: {feedback.mastery_level}")
            print(f"  ✓ 复习次数: {feedback.review_count}")
            print(f"  ✓ 历史最高: {feedback.historical_max_mastery}")
        else:
            print("  ✗ 获取反馈失败")
    
    # 最终验证
    print("\n" + "=" * 60)
    print("【最终结果】")
    feedback = service.get_feedback(test_question_id)
    if feedback:
        print(f"  掌握程度: {feedback.mastery_level}")
        print(f"  复习次数: {feedback.review_count}")
        print(f"  历史最高: {feedback.historical_max_mastery}")
        
        # 验证：复习次数应该是1（只有第一次从1→5时增加）
        if feedback.review_count == 1:
            print("\n✅ 测试通过！复习次数正确（只在首次突破历史时增加）")
            return True
        else:
            print(f"\n❌ 测试失败！复习次数为 {feedback.review_count}，预期为 1")
            return False
    else:
        print("\n❌ 测试失败！无法获取反馈")
        return False

def test_progressive_improvement():
    """测试渐进式提升"""
    print("\n" + "=" * 60)
    print("测试：渐进式提升 0→2→4→5")
    print("=" * 60)
    
    service = FeedbackService()
    test_question_id = "test-progressive-002"
    
    # 清理测试数据
    key = service._get_feedback_key(test_question_id)
    if service.redis_client:
        service.redis_client.delete(key)
    
    test_sequence = [
        (0, "初始状态"),
        (2, "从0提升到2（应该增加）"),
        (4, "从2提升到4（应该增加）"),
        (5, "从4提升到5（应该增加）"),
    ]
    
    print("\n【测试过程】")
    for level, description in test_sequence:
        print(f"\n操作: {description}")
        print(f"  设置 mastery_level={level}")
        
        success = service.submit_feedback(test_question_id, {'mastery_level': level})
        
        feedback = service.get_feedback(test_question_id)
        if feedback:
            print(f"  ✓ 掌握程度: {feedback.mastery_level}")
            print(f"  ✓ 复习次数: {feedback.review_count}")
            print(f"  ✓ 历史最高: {feedback.historical_max_mastery}")
    
    # 最终验证
    print("\n" + "=" * 60)
    print("【最终结果】")
    feedback = service.get_feedback(test_question_id)
    if feedback:
        print(f"  掌握程度: {feedback.mastery_level}")
        print(f"  复习次数: {feedback.review_count}")
        print(f"  历史最高: {feedback.historical_max_mastery}")
        
        # 验证：复习次数应该是2（0→2, 2→4，但4→5是微调不增加）
        if feedback.review_count == 2:
            print("\n✅ 测试通过！复习次数正确（实质性提升才增加，微调不增加）")
            return True
        else:
            print(f"\n❌ 测试失败！复习次数为 {feedback.review_count}，预期为 2")
            return False
    else:
        print("\n❌ 测试失败！无法获取反馈")
        return False

if __name__ == "__main__":
    print("开始测试反馈服务防刷分机制...\n")
    
    result1 = test_alternating_mastery()
    result2 = test_progressive_improvement()
    
    print("\n" + "=" * 60)
    print("【测试总结】")
    print(f"  交替评分测试: {'✅ 通过' if result1 else '❌ 失败'}")
    print(f"  渐进提升测试: {'✅ 通过' if result2 else '❌ 失败'}")
    print("=" * 60)
    
    sys.exit(0 if (result1 and result2) else 1)
