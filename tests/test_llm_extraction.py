"""
大模型面试题提取测试用例

用于测试大模型对技术内容的理解和提取能力，详细打印所有参数和输出。

使用方法:
    python -m tests.test_llm_extraction
"""
from app.services.llm_service import LLMService
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


# 测试用的技术内容（来自附件：反射的应用场景）
TEST_CONTENT = """反射的应用场景了解么?

像咱们平时大部分时候都是在写业务代码，很少会接触到直接使用反射机制的场景。

但是，这并不代表反射没有用。相反，正是因为反射，你才能这么轻松地使用各种框架。像 Spring/Spring Boot、MyBatis 等等框架中都大量使用了反射机制。

这些框架中也大量使用了动态代理，而动态代理的实现也依赖反射。

比如下面是通过 JDK 实现动态代理的示例代码，其中就使用了反射类 Method 来调用指定的方法。

public class DebugInvocationHandler implements InvocationHandler {
    /**
     * 代理类中的真实对象
     */
    private final Object target;

    public DebugInvocationHandler(Object target) {
        this.target = target;
    }

    public Object invoke(Object proxy, Method method, Object[] args) throws InvocationTargetException, IllegalAccessException {
        System.out.println("before method " + method.getName());
        Object result = method.invoke(target, args);
        System.out.println("after method " + method.getName());
        return result;
    }
}

另外，像 Java 中的一大利器 注解 的实现也用到了反射。

为什么你使用 Spring 的时候，一个 @Component 注解就声明了一个类为 Spring Bean 呢？为什么你通过一个 @Value 注解就读取到配置文件中的值呢？究竟是怎么起作用的呢?

这些都是因为你可以基于反射分析类，然后获取到类/属性/方法/方法的参数上的注解。你获取到注解之后，就可以做进一步的处理。"""


def test_llm_extraction():
    """
    测试大模型对技术内容的提取能力
    详细打印所有参数、prompt和输出
    """
    print("=" * 80)
    print("大模型面试题提取测试")
    print("=" * 80)

    # 1. 初始化LLM服务
    print("\n【步骤1】初始化LLM服务")
    print("-" * 80)
    llm_service = LLMService()

    if not llm_service.client:
        print("❌ 错误: 大模型客户端未初始化，请检查.env配置")
        return

    print("✅ LLM服务初始化成功")

    # 2. 打印大模型配置参数
    print("\n【步骤2】大模型配置参数")
    print("-" * 80)

    # 先检测模型限制
    llm_service._detect_model_limits()

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_base = os.getenv("OPENAI_API_BASE", "未配置(使用默认)")
    api_key = os.getenv("OPENAI_API_KEY", "")
    api_key_display = api_key[:10] + "..." if api_key else "未配置"
    max_input_tokens = llm_service.max_input_tokens
    max_output_tokens = llm_service.max_output_tokens

    print(f"模型名称: {model_name}")
    print(f"API Base: {api_base}")
    print(f"API Key: {api_key_display}")
    print(f"最大输入Token: {max_input_tokens}")
    print(f"最大输出Token: {max_output_tokens}")
    print("Temperature: 0.3")

    # 3. 打印系统提示词
    print("\n【步骤3】系统提示词 (System Prompt)")
    print("-" * 80)
    system_prompt = llm_service._get_system_prompt()
    print(system_prompt)
    print(f"\n系统提示词长度: {len(system_prompt)} 字符")

    # 4. 准备测试内容
    print("\n【步骤4】测试内容")
    print("-" * 80)
    print(f"内容长度: {len(TEST_CONTENT)} 字符")
    print(f"内容预览(前200字符): {TEST_CONTENT[:200]}...")

    # 5. 构建用户提示词
    print("\n【步骤5】用户提示词 (User Prompt)")
    print("-" * 80)

    # 模拟 _process_page_with_chunks 中的prompt构建
    test_url = "https://javaguide.cn/java/basis/reflection.html"
    test_title = "反射的应用场景"

    # 检查是否需要分chunk
    max_content_length = int(os.getenv("MAX_CONTENT_LENGTH_PER_PAGE", 2000))
    print(f"单页最大内容长度配置: {max_content_length}")

    if len(TEST_CONTENT) <= max_content_length:
        chunks = [TEST_CONTENT]
        print(f"✅ 内容未超限，不需要分chunk (实际: {len(TEST_CONTENT)} <= 配置: {max_content_length})")
    else:
        print(f"⚠️  内容超限，需要分chunk (实际: {len(TEST_CONTENT)} > 配置: {max_content_length})")
        chunks = llm_service._split_content_by_semantics(
            TEST_CONTENT, max_length=max_content_length, overlap=200)
        print(f"分chunk后数量: {len(chunks)}")
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i + 1}: {len(chunk)} 字符")

    # 6. 调用大模型并详细记录
    print("\n【步骤6】调用大模型")
    print("-" * 80)

    all_questions = []

    for chunk_idx, chunk_content in enumerate(chunks):
        print(f"\n{'=' * 40}")
        print(f"处理 Chunk {chunk_idx + 1}/{len(chunks)}")
        print(f"{'=' * 40}")

        # 构建prompt
        prompt = f"""### 网页信息
URL: {test_url}
标题: {test_title}
内容片段 {chunk_idx + 1}/{len(chunks)}:
{chunk_content}
"""

        print("\n用户提示词内容:")
        print(prompt)
        print(f"\n用户提示词长度: {len(prompt)} 字符")
        print(f"估计Token数: {int(len(prompt) / 3.5)}")

        # 检查token限制
        estimated_tokens = int(len(prompt) / 3.5)
        if estimated_tokens > llm_service.min_token_limit:
            print(f" 警告: Token数({estimated_tokens})超过限制({llm_service.min_token_limit})")
            continue

        # 打印调用参数
        print("\n调用参数:")
        print(f"  - model: {model_name}")
        print(f"  - max_tokens: {max_output_tokens}")
        print("  - temperature: 0.3")
        print("  - messages[0].role: system")
        print("  - messages[0].content: (见步骤3)")
        print("  - messages[1].role: user")
        print("  - messages[1].content: (见上方)")

        # 调用大模型
        try:
            print("\n正在调用大模型...")
            response = llm_service.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=max_output_tokens,
            )

            # 打印原始响应
            print("\n✅ 大模型调用成功!")
            print(f"响应对象类型: {type(response)}")
            print(f"choices数量: {len(response.choices)}")

            raw_content = response.choices[0].message.content or ""
            print("\n【步骤7】大模型原始输出")
            print("-" * 80)
            print(raw_content)
            print(f"\n原始输出长度: {len(raw_content)} 字符")

            # 解析响应
            print("\n【步骤8】解析大模型输出")
            print("-" * 80)

            questions = llm_service._parse_response(raw_content)

            print("\n解析结果:")
            print(f"识别到问题数量: {len(questions)}")

            if questions:
                for i, q in enumerate(questions, 1):
                    print(f"\n{'=' * 60}")
                    print(f"问题 {i}:")
                    print(f"{'=' * 60}")
                    print(f"标题: {q.title}")
                    print("\n答案(前300字符):")
                    print(q.answer[:300] if len(q.answer) > 300 else q.answer)
                    if len(q.answer) > 300:
                        print(f"... (完整答案长度: {len(q.answer)} 字符)")
                    print(f"\n难度: {q.difficulty}")
                    print(f"重要性评分: {q.importance_score}")
                    print(f"分类: {q.category}")
                    print(f"标签: {q.tags}")
                    print(f"来源URL: {q.source_url}")

                all_questions.extend(questions)
            else:
                print("❌ 未识别到任何问题!")
                print("可能的原因:")
                print("  1. 大模型没有理解内容")
                print("  2. 大模型在做简化处理")
                print("  3. JSON格式解析失败")
                print("  4. 内容质量不够")

        except Exception as e:
            print(f"\n❌ 调用大模型失败: {str(e)}")
            import traceback
            traceback.print_exc()

    # 9. 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"总识别问题数: {len(all_questions)}")

    if all_questions:
        print("\n✅ 成功提取问题!")
        for i, q in enumerate(all_questions, 1):
            print(f"  {i}. {q.title} (难度: {q.difficulty})")

        # 分析答案质量
        print("\n答案质量分析:")
        total_answer_length = sum(len(q.answer) for q in all_questions)
        avg_answer_length = total_answer_length / \
            len(all_questions) if all_questions else 0
        print(f"  平均答案长度: {avg_answer_length:.0f} 字符")

        if avg_answer_length < 100:
            print("  ⚠️  警告: 答案过短，可能存在简化处理!")
        elif avg_answer_length < 300:
            print("  ️  答案长度适中，但可能还可以更详细")
        else:
            print("  ✅ 答案长度充足")
    else:
        print("\n❌ 未能提取问题")
        print("\n建议:")
        print("  1. 检查系统提示词是否过于严格")
        print("  2. 检查温度参数(temperature)是否过低")
        print("  3. 检查max_tokens是否限制了输出")
        print("  4. 尝试使用更强的模型(如gpt-4o)")
        print("  5. 优化内容格式，使其更结构化")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


def test_different_prompts():
    """
    测试不同的系统提示词对提取效果的影响
    """
    print("\n" + "=" * 80)
    print("测试不同提示词的效果")
    print("=" * 80)

    llm_service = LLMService()

    if not llm_service.client:
        print("❌ 错误: 大模型客户端未初始化")
        return

    # 测试提示词1: 要求详细答案
    prompt_detailed = """
你是一位资深技术面试官。请从提供的技术内容中提取面试问题。

## 关键要求:
1. 问题必须基于原文内容
2. **答案必须非常详细，包含原文中的所有技术细节**
3. 不要简化或摘要，保持答案的完整性和深度
4. 每个答案至少300字以上

## 输出格式:
[
  {
    "title": "问题",
    "answer": "详细答案(至少300字)",
    "tags": ["标签"],
    "difficulty": "medium",
    "importance_score": 0.8,
    "category": "分类"
  }
]
"""

    # 测试提示词2: 简化版
    prompt_simple = """
从技术内容中提取面试问题，生成JSON格式:
[{"title": "问题", "answer": "答案"}]
"""

    prompts = [
        ("详细提示词", prompt_detailed),
        ("简化提示词", prompt_simple)
    ]

    for name, prompt in prompts:
        print(f"\n{'=' * 80}")
        print(f"测试提示词: {name}")
        print(f"{'=' * 80}")
        print(f"提示词内容:\n{prompt}")

        # 这里可以添加实际调用代码
        # ...

        print("\n(实际调用代码可以根据需要添加)")


if __name__ == "__main__":
    # 运行主测试
    test_llm_extraction()

    # 可选: 测试不同提示词
    # test_different_prompts()
