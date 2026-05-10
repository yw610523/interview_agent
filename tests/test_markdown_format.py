#!/usr/bin/env python3
"""
测试 Markdown 格式优化效果

验证 LLM 生成的答案是否包含 Markdown 格式标记
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.llm_service import LLMService


def test_markdown_format():
    """测试系统提示词是否要求 Markdown 格式"""
    print("=" * 60)
    print("Markdown 格式优化测试")
    print("=" * 60)
    
    llm_service = LLMService()
    system_prompt = llm_service._get_system_prompt()
    
    # 检查关键要求
    checks = {
        "包含 'Markdown' 关键词": "Markdown" in system_prompt or "markdown" in system_prompt,
        "包含代码块示例": "```" in system_prompt,
        "包含标题示例": "##" in system_prompt,
        "包含列表示例": "- " in system_prompt or "1." in system_prompt,
        "明确要求使用 Markdown": "必须使用 Markdown" in system_prompt or "must use markdown" in system_prompt.lower(),
    }
    
    print("\n📋 系统提示词检查:")
    all_passed = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
        if not result:
            all_passed = False
    
    # 显示相关片段
    print("\n📝 相关提示词片段:")
    lines = system_prompt.split('\n')
    for i, line in enumerate(lines):
        if 'markdown' in line.lower() or '格式' in line:
            # 显示该行及其前后各一行
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            print(f"\n  第 {i+1} 行附近:")
            for j in range(start, end):
                prefix = ">>> " if j == i else "    "
                print(f"{prefix}{lines[j]}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有检查通过！系统提示词已正确配置 Markdown 格式要求")
    else:
        print("❌ 部分检查未通过，请检查系统提示词")
    print("=" * 60)
    
    return all_passed


def test_sample_answer():
    """测试示例答案的格式（如果有）"""
    print("\n" + "=" * 60)
    print("示例答案格式测试")
    print("=" * 60)
    
    # 这里可以添加实际的 LLM 调用测试
    # 但由于需要 API Key，我们只做模拟测试
    
    sample_answers = [
        {
            "name": "理想格式（带 Markdown）",
            "content": """## 核心概念

Python的**反射机制**是指在运行时动态获取对象信息的能力。

## 应用场景

1. **框架开发**：如Spring框架
2. **插件系统**：动态加载模块

```python
import inspect
obj = MyClass()
```

> 注意性能问题
""",
        },
        {
            "name": "纯文本格式（无 Markdown）",
            "content": "Python的反射机制是指在运行时动态获取对象信息并调用其方法的能力。主要有以下几个应用场景：1. 框架开发 2. 插件系统 3. 测试工具。",
        },
    ]
    
    for sample in sample_answers:
        print(f"\n📄 {sample['name']}:")
        content = sample['content']
        
        # 检测 Markdown 标记
        has_headers = '#' in content
        has_bold = '**' in content or '__' in content
        has_code = '```' in content or '`' in content
        has_list = '- ' in content or '1.' in content or '* ' in content
        
        print(f"  - 标题标记 (#): {'✅' if has_headers else '❌'}")
        print(f"  - 粗体标记 (**): {'✅' if has_bold else '❌'}")
        print(f"  - 代码标记 (```): {'✅' if has_code else '❌'}")
        print(f"  - 列表标记 (-/1.): {'✅' if has_list else '❌'}")
        
        markdown_score = sum([has_headers, has_bold, has_code, has_list])
        print(f"  📊 Markdown 评分: {markdown_score}/4")
        
        if markdown_score >= 3:
            print(f"  ✅ 格式良好")
        elif markdown_score >= 1:
            print(f"  ⚠️  格式一般，建议改进")
        else:
            print(f"  ❌ 纯文本，需要格式化")


if __name__ == "__main__":
    result1 = test_markdown_format()
    test_sample_answer()
    
    print("\n" + "=" * 60)
    print("💡 建议:")
    print("  1. 新爬取的题目会自动使用 Markdown 格式")
    print("  2. 旧题目会在前端进行基本优化")
    print("  3. 如需完全格式化旧题目，需重新生成答案")
    print("=" * 60)
    
    sys.exit(0 if result1 else 1)
