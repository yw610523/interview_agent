#!/usr/bin/env python3
"""
测试提示词配置管理功能

验证：
1. config.yaml 中的提示词配置是否正确加载
2. API 端点是否正常工作
3. LLM 服务是否从配置文件读取提示词
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_config_yaml():
    """测试 config.yaml 中的提示词配置"""
    print("=" * 60)
    print("测试 1: config.yaml 提示词配置")
    print("=" * 60)
    
    import yaml
    
    config_path = project_root / "config.yaml"
    if not config_path.exists():
        print("❌ config.yaml 文件不存在")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 检查 prompts 部分
    if 'prompts' not in config:
        print("❌ config.yaml 中缺少 prompts 配置段")
        return False
    
    prompts = config['prompts']
    
    checks = {
        "包含 question_extraction_system": 'question_extraction_system' in prompts,
        "包含 answer_generation_system": 'answer_generation_system' in prompts,
        "question_extraction_system 非空": bool(prompts.get('question_extraction_system', '').strip()),
        "answer_generation_system 非空": bool(prompts.get('answer_generation_system', '').strip()),
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
        if not result:
            all_passed = False
    
    # 显示提示词长度
    if prompts.get('question_extraction_system'):
        length = len(prompts['question_extraction_system'])
        print(f"\n📊 question_extraction_system 长度: {length} 字符")
    
    if prompts.get('answer_generation_system'):
        length = len(prompts['answer_generation_system'])
        print(f"📊 answer_generation_system 长度: {length} 字符")
    
    return all_passed


def test_config_manager():
    """测试配置管理器读取提示词"""
    print("\n" + "=" * 60)
    print("测试 2: 配置管理器读取提示词")
    print("=" * 60)
    
    from app.config.config_manager import config_manager
    
    try:
        question_prompt = config_manager.get('prompts.question_extraction_system')
        answer_prompt = config_manager.get('prompts.answer_generation_system')
        
        checks = {
            "成功读取 question_extraction_system": question_prompt is not None and len(question_prompt) > 0,
            "成功读取 answer_generation_system": answer_prompt is not None and len(answer_prompt) > 0,
        }
        
        all_passed = True
        for check_name, result in checks.items():
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}")
            if not result:
                all_passed = False
        
        if question_prompt:
            print(f"\n📝 question_extraction_system 前100字符:")
            print(f"   {question_prompt[:100]}...")
        
        return all_passed
    except Exception as e:
        print(f"❌ 配置管理器测试失败: {str(e)}")
        return False


def test_llm_service():
    """测试 LLM 服务使用配置文件的提示词"""
    print("\n" + "=" * 60)
    print("测试 3: LLM 服务提示词加载")
    print("=" * 60)
    
    from app.services.llm_service import LLMService
    
    try:
        llm_service = LLMService()
        system_prompt = llm_service._get_system_prompt()
        
        checks = {
            "成功获取系统提示词": system_prompt is not None and len(system_prompt) > 0,
            "提示词包含 Markdown 要求": "Markdown" in system_prompt or "markdown" in system_prompt,
            "提示词包含格式示例": "```" in system_prompt or "##" in system_prompt,
        }
        
        all_passed = True
        for check_name, result in checks.items():
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}")
            if not result:
                all_passed = False
        
        print(f"\n📊 系统提示词长度: {len(system_prompt)} 字符")
        print(f"📝 前150字符预览:")
        print(f"   {system_prompt[:150]}...")
        
        return all_passed
    except Exception as e:
        print(f"❌ LLM 服务测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints():
    """测试 API 端点（需要运行服务器）"""
    print("\n" + "=" * 60)
    print("测试 4: API 端点可用性")
    print("=" * 60)
    
    print("⚠️  此测试需要服务器运行在 http://localhost:9023")
    print("💡 跳过实际请求测试，仅检查代码结构")
    
    # 检查 main.py 中是否有相关路由
    main_py = project_root / "app" / "main.py"
    if not main_py.exists():
        print("❌ main.py 文件不存在")
        return False
    
    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "存在 GET /api/prompts 路由": '@app.get("/api/prompts"' in content,
        "存在 POST /api/prompts 路由": '@app.post("/api/prompts"' in content,
        "包含 get_prompts_config 函数": 'async def get_prompts_config()' in content,
        "包含 update_prompts_config 函数": 'async def update_prompts_config(' in content,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
        if not result:
            all_passed = False
    
    return all_passed


def main():
    """运行所有测试"""
    print("\n" + "🧪" * 30)
    print("提示词配置管理功能测试")
    print("🧪" * 30 + "\n")
    
    results = []
    
    # 运行测试
    results.append(("config.yaml 配置", test_config_yaml()))
    results.append(("配置管理器", test_config_manager()))
    results.append(("LLM 服务", test_llm_service()))
    results.append(("API 端点", test_api_endpoints()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 60)
    if passed == total:
        print(f"🎉 所有测试通过！({passed}/{total})")
    else:
        print(f"⚠️  部分测试失败 ({passed}/{total} 通过)")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
