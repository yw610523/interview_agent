"""
大模型服务模块

用于解析爬虫结果，识别和提取面试问题。
"""

import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Any

from app.config.config_manager import get_config

# 尝试导入不同的大模型库
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# 导入json-repair用于修复损坏的JSON
try:
    from json_repair import repair_json

    JSON_REPAIR_AVAILABLE = True
except ImportError:
    JSON_REPAIR_AVAILABLE = False


@dataclass
class ParsedQuestion:
    """
    解析后的面试问题数据结构
    """

    title: str
    answer: str
    source_url: str
    tags: List[str]
    importance_score: float = 0.0
    difficulty: str = "medium"  # easy, medium, hard
    category: str = ""


class LLMService:
    """
    大模型服务类
    """

    def __init__(self):
        self.client = self._init_client()
        self.max_input_tokens = None
        self.max_output_tokens = None
        self.min_token_limit = None

    def _detect_model_limits(self):
        """
        获取模型的Token限制
        - min_token_limit: 用于检测输入是否超限（模型支持的最大输入token）
        - max_input_tokens: 模型支持的最大输入token数
        - max_output_tokens: 模型支持的最大输出token数
        """
        config_max_input = os.getenv("MODEL_MAX_INPUT_TOKENS")
        config_max_output = os.getenv("MODEL_MAX_OUTPUT_TOKENS")

        if config_max_input and config_max_output:
            # 从环境变量读取配置
            self.max_input_tokens = int(config_max_input)
            self.max_output_tokens = int(config_max_output)
            logger.info(
                f"从配置读取Token限制: 输入={self.max_input_tokens}, 输出={self.max_output_tokens}"
            )
        else:
            # 使用默认值（根据常见模型）
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            model_limits = {
                "gpt-3.5-turbo": (16384, 4096),
                "gpt-4": (8192, 4096),
                "gpt-4-turbo": (128000, 4096),
                "gpt-4o-mini": (128000, 16384),
                "qwen": (8192, 8192),
                "qwen3.5-flash": (8192, 8192),
                "deepseek": (128000, 16384),  # deepseek支持更大的输出
                "deepseek-chat": (128000, 16384),
                "deepseek-coder": (128000, 16384),
            }

            default_input, default_output = model_limits.get(model_name, (128000, 16384))
            self.max_input_tokens = default_input
            self.max_output_tokens = default_output
            logger.info(
                f"使用模型默认Token限制: 输入={self.max_input_tokens}, 输出={self.max_output_tokens}"
            )

        # min_token_limit 用于检测输入是否超限（与max_input_tokens相同）
        self.min_token_limit = self.max_input_tokens

        logger.info(
            f"Token限制配置完成: 输入上限={self.max_input_tokens}, 输出上限={self.max_output_tokens}"
        )
        return self.max_input_tokens, self.max_output_tokens

    def parse_crawl_results(
            self, crawl_results: List[Dict[str, Any]], on_question_found=None
    ) -> List[ParsedQuestion]:
        """
        解析爬虫结果，提取面试问题

        参数:
            crawl_results: 爬虫结果列表
            on_question_found: 回调函数，当识别到问题时立即调用（用于即时入库）
                              回调函数签名: callback(questions: List[ParsedQuestion])
        """
        if not self.client:
            logger.warning("大模型客户端未初始化")
            return []

        processed_results = self._preprocess_results(crawl_results)

        try:
            if self.max_input_tokens is None:
                self._detect_model_limits()

            # 确保 min_token_limit 已设置
            if self.min_token_limit is None:
                self.min_token_limit = self.max_input_tokens or 4096

            # 使用探测到的限制
            max_prompt_tokens = self.max_input_tokens or 4096
            max_response_tokens = self.max_output_tokens or 16384

            logger.info(
                f"使用探测到的Token限制: 输入={max_prompt_tokens}, 输出={max_response_tokens}"
            )

            logger.info(f"开始解析 {len(processed_results)} 个页面")
            all_questions = []

            for page_idx, result in enumerate(processed_results):
                url = result.get("url", "")
                title = result.get("title", "")
                content = result.get("content", "")

                # 验证内容有效性
                if not content or len(content) < 100:
                    logger.warning("页面 %d 内容过短(%d字符)，跳过处理", page_idx + 1, len(content) if content else 0)
                    logger.warning("URL: %s", url)
                    logger.warning("标题: %s", title)
                    logger.warning("可能原因: 1) JavaScript动态渲染页面 2) 反爬虫限制 3) 页面为空")
                    continue

                logger.info("=" * 60)
                logger.info(f"=== 处理页面 {page_idx + 1}/{len(processed_results)} ===")
                logger.info(f"URL: {url}")
                logger.info(f"标题: {title}")
                logger.info(f"内容长度: {len(content)} 字符")

                # 使用chunk处理单页内容
                questions = self._process_page_with_chunks(url, title, content)
                all_questions.extend(questions)

                # 立即入库：识别到问题就立即回调（如果提供了回调函数）
                if questions and on_question_found:
                    try:
                        on_question_found(questions)
                        logger.info(f"页面 {page_idx + 1} 的 {len(questions)} 个问题已即时入库")
                    except Exception as e:
                        logger.error(f"即时入库失败: {str(e)}")

                logger.info(f"页面 {page_idx + 1} 识别出 {len(questions)} 个问题")
                logger.info(f"累计识别: {len(all_questions)} 个问题")
                logger.info("=" * 60)

            return all_questions
        except Exception as e:
            logger.error(f"大模型调用失败: {str(e)}")
            return []

    def _init_client(self):
        """
        初始化大模型客户端
        """
        api_key = os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE")

        if api_key and OPENAI_AVAILABLE:
            try:
                if api_base:
                    client = OpenAI(api_key=api_key, base_url=api_base)
                else:
                    client = OpenAI(api_key=api_key)
                logger.info("OpenAI 客户端初始化成功")
                return client
            except Exception as e:
                logger.error(f"OpenAI 客户端初始化失败: {str(e)}")

        return None

    def _preprocess_results(
            self, crawl_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        智能预处理爬虫结果，保留完整内容让大模型自主识别
        """
        processed = []

        for result in crawl_results:
            url = result.get("url", "")
            title = result.get("title", "")
            text_content = result.get("text_content", "") or result.get(
                "html_content", ""
            )

            if not text_content:
                continue

            # 智能内容优化策略
            optimized_content = self._optimize_content_for_llm(text_content, title, url)

            processed.append(
                {
                    "url": url,
                    "title": title,
                    "content": optimized_content,
                    "original_length": len(text_content),
                }
            )

        return processed

    def _optimize_content_for_llm(self, text: str, title: str, url: str) -> str:
        """
        为LLM优化内容格式，提高面试题识别准确率
        """
        # 1. 清理和标准化文本
        text = self._clean_text(text)

        # 2. 智能分段和结构提取（不添加额外指令，避免干扰）
        structured_content = self._extract_intelligent_structure(text, title)

        return structured_content

    def _clean_text(self, text: str) -> str:
        """清理文本，去除噪音"""
        import re

        # 去除多余的空格和换行
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)

        # 去除常见的网页噪音
        noise_patterns = [
            r"版权.*?\d{4}",
            r"版权所有.*",
            r"联系我们.*",
            r"备案号.*",
            r"©.*",
        ]

        for pattern in noise_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        return text.strip()

    def _extract_intelligent_structure(self, text: str, title: str) -> str:
        """智能提取内容结构"""
        # 直接返回清理后的文本，不进行截断
        # 如果需要分块处理，会在 _process_page_with_chunks 中进行语义分割
        if title:
            return f"# {title}\n\n{text}"
        return text

    def _is_technical_sentence(self, sentence: str) -> bool:
        """判断句子是否可能包含技术内容"""
        technical_keywords = [
            "实现",
            "原理",
            "机制",
            "流程",
            "架构",
            "设计",
            "优化",
            "性能",
            "算法",
            "数据结构",
            "数据库",
            "网络",
            "协议",
            "安全",
            "并发",
            "分布式",
            "微服务",
            "容器",
            "云原生",
            "人工智能",
            "机器学习",
            "深度学习",
            "自然语言",
            "计算机视觉",
            "大数据",
            "区块链",
        ]

        sentence_lower = sentence.lower()
        return any(keyword in sentence_lower for keyword in technical_keywords)

    def _get_system_prompt(self) -> str:
        """
        获取优化的系统提示词
        """
        return """
你是一位资深技术面试官和技术内容专家。请仔细阅读提供的网页内容，提取高质量的技术面试问题。

## 核心任务：
1. **完整理解**：将网页内容视为一个完整的技术主题，不要过度拆分
2. **问题识别**：识别内容中的核心技术问题（可能是1个主要问题，或2-3个相关问题）
3. **详细解答**：为每个问题生成完整、详细的答案，包含所有技术细节
4. **智能分类**：根据问题类型和难度进行分类

## 重要原则：
- 如果内容是围绕一个主要技术点展开的（如"反射的应用场景"），请将其作为一个整体问题处理
- 不要将文章中的每个小知识点都拆分成独立的问题
- 答案应该详尽，包含原文中的所有技术细节和代码示例
- 答案长度至少300字以上，确保内容充实

## 问题类型：
- **概念定义**：技术术语的定义、核心概念解释
- **原理机制**：技术底层工作原理、实现机制
- **实现方法**：具体实现步骤、代码示例分析
- **对比分析**：不同技术方案的优缺点比较
- **应用场景**：技术适用场景、最佳实践
- **性能优化**：性能问题分析、优化策略

## 难度评估标准：
- **easy**：基础概念、定义类问题
- **medium**：需要一定理解和分析能力
- **hard**：深入原理、复杂设计或综合分析

## 重要性评估：
根据问题在面试中的出现频率和技术深度评分（0-1）

## 输出格式（必须是纯JSON数组）：
[
  {
    "title": "问题标题，必须是一个完整的疑问句",
    "answer": "基于原文的详细技术答案（至少300字，包含所有技术细节和代码示例）",
    "source_url": "来源网页URL",
    "tags": ["相关技术标签", "如Python", "算法"],
    "importance_score": 0.8,
    "difficulty": "medium",
    "category": "问题分类"
  }
]

## 注意事项：
1. 只从网页内容中提取问题，不要凭空捏造
2. 问题标题必须是清晰的疑问句
3. 答案必须基于原文内容，保持准确和完整
4. 如果内容是单一主题，返回1个详细问题；如果有多个独立主题，可返回2-3个问题
5. 确保输出是有效的JSON格式
"""

    def _split_content_by_semantics(self, content: str, max_length: int = 1500, overlap: int = 300) -> list:
        """
        使用滑动窗口和语义边界分割内容

        参数:
            content: 要分割的内容
            max_length: 每个chunk的最大长度
            overlap: 相邻chunk之间的重叠长度

        返回:
            分割后的内容chunk列表
        """
        chunks = []
        content_length = len(content)

        if content_length <= max_length:
            return [content]

        start = 0
        while start < content_length:
            end = min(start + max_length, content_length)

            # 在语义边界处分割（优先找段落、句子结束位置）
            # 从end位置向前查找合适的分割点
            split_pos = end

            # 优先在段落分隔处分割
            for sep in ['\n\n', '\n', '。', '！', '？', '.', '!', '?']:
                pos = content.rfind(sep, start + max_length // 2, end)
                if pos != -1:
                    split_pos = pos + len(sep)
                    break

            chunk = content[start:split_pos]
            chunks.append(chunk.strip())

            # 计算下一个起始位置（考虑重叠）
            start = split_pos - overlap
            if start < 0:
                start = 0

            # 避免无限循环
            if start >= content_length or (len(chunks) > 0 and start >= len(chunks[-1])):
                break

        return chunks

    def _build_prompt(self, crawl_results: List[Dict[str, Any]]) -> str:
        """
        构建用户提示词
        """
        content = []
        for idx, result in enumerate(crawl_results[:3]):  # 减少每批处理数量
            url = result.get("url", "")
            title = result.get("title", "")
            text = result.get("content", "")

            content.append(f"### 网页 {idx + 1}")
            content.append(f"URL: {url}")
            content.append(f"标题: {title}")
            content.append(f"内容:\n{text}")
            content.append("---")

        return "\n".join(content)

    def _process_page_with_chunks(self, url: str, title: str, content: str) -> List[ParsedQuestion]:
        """
        处理单个页面，支持内容chunk分割和JSON解析失败重试

        参数:
            url: 网页URL
            title: 网页标题
            content: 网页内容

        返回:
            从该页面提取的所有面试问题
        """
        all_questions = []

        # 如果内容过长，进行chunk分割
        # 从环境变量读取单页最大内容长度，默认2000字符
        max_content_length = int(os.getenv("MAX_CONTENT_LENGTH_PER_PAGE", 2000))
        if len(content) <= max_content_length:
            chunks = [content]
        else:
            chunks = self._split_content_by_semantics(content, max_length=max_content_length, overlap=200)
            logger.info(f"页面 {url} 内容过长，分割为 {len(chunks)} 个chunk")

        if self.client is None:
            logger.error("大模型客户端未初始化，无法处理页面")
            return []

        client = self.client
        max_retries = int(os.getenv("LLM_RETRY_COUNT", 3))

        for chunk_idx, chunk_content in enumerate(chunks):
            # 构建单chunk的提示词
            prompt = f"""### 网页信息
URL: {url}
标题: {title}
内容片段 {chunk_idx + 1}/{len(chunks)}:
{chunk_content}
"""

            questions = []
            retry_count = 0
            parse_success = False

            while retry_count < max_retries and not parse_success:
                try:
                    # 检查token数量
                    estimated_tokens = int(len(prompt) / 3.5)
                    if estimated_tokens > self.min_token_limit:
                        logger.warning(f"chunk {chunk_idx + 1} token超限，跳过")
                        break

                    # 记录调用参数
                    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                    system_prompt = self._get_system_prompt()
                    logger.info(
                        f"调用大模型参数: model={model_name}, "
                        f"max_tokens={self.max_output_tokens}, "
                        f"temperature=0.3, "
                        f"system_prompt长度={len(system_prompt)}字符, "
                        f"prompt长度={len(prompt)}字符(约{estimated_tokens} tokens), "
                        f"输入上限={self.min_token_limit} tokens"
                    )

                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": self._get_system_prompt()},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.3,
                        max_tokens=self.max_output_tokens,
                    )

                    result = response.choices[0].message.content or ""
                    logger.info(f"LLM返回内容长度: {len(result)} 字符")

                    questions = self._parse_response(result)

                    # 检查是否成功解析到问题
                    if questions:
                        parse_success = True
                    elif retry_count < max_retries - 1:
                        # 解析返回了空数组，可能是没有找到问题，也可能是解析失败
                        # 如果是解析错误，重试；否则认为确实没有问题
                        parse_success = True
                        logger.debug(f"chunk {chunk_idx + 1} 未识别到问题")

                except json.JSONDecodeError as e:
                    retry_count += 1
                    logger.warning(f"chunk {chunk_idx + 1} JSON解析失败（第{retry_count}/{max_retries}次重试）: {str(e)}")
                    import time
                    time.sleep(1.5 ** retry_count)  # 指数退避
                except Exception as e:
                    logger.error(f"处理chunk {chunk_idx + 1} 失败: {str(e)}")
                    break

            # 设置source_url
            for q in questions:
                q.source_url = url

            all_questions.extend(questions)
            if retry_count > 0:
                logger.info(f"chunk {chunk_idx + 1} 识别出 {len(questions)} 个问题（经过 {retry_count} 次重试）")
            else:
                logger.info(f"chunk {chunk_idx + 1} 识别出 {len(questions)} 个问题")

        return all_questions

    def _parse_response(self, response: str | None) -> List[ParsedQuestion]:
        """
        解析大模型响应，增强了JSON解析的健壮性
        """
        if response is None:
            logger.warning("LLM返回内容为空")
            return []

        try:
            # 清理响应文本，去除可能的代码块标记
            cleaned_response = response.strip()
            if cleaned_response.startswith("``json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            # 提取 JSON 部分（处理可能的前后文本）
            start = cleaned_response.find("[")
            end = cleaned_response.rfind("]") + 1

            if start != -1 and end != -1:
                json_str = cleaned_response[start:end]
                logging.debug(f"LLM返回JSON内容长度: {len(json_str)} 字符")

                # 尝试直接解析JSON（大多数情况下JSON是有效的）
                try:
                    data = json.loads(json_str)
                    logger.debug("JSON解析成功（无需修复）")
                except json.JSONDecodeError:
                    # JSON格式有问题，尝试修复
                    logger.debug("JSON格式异常，尝试修复...")

                    # 优先使用 json-repair 修复
                    if JSON_REPAIR_AVAILABLE:
                        try:
                            repaired_json = repair_json(json_str)
                            data = json.loads(repaired_json)
                            logger.info("使用 json-repair 成功修复JSON格式问题")
                        except Exception as e:
                            logger.warning(f"json-repair 修复失败: {str(e)}，尝试内置修复方法")
                            # 如果 json-repair 失败，使用内置修复
                            json_str = self._fix_json_format(json_str)
                            data = json.loads(json_str)
                            logger.info("使用内置方法成功修复JSON格式问题")
                    else:
                        # json-repair 不可用，直接使用内置修复
                        json_str = self._fix_json_format(json_str)
                        data = json.loads(json_str)
                        logger.info("使用内置方法修复JSON格式问题")

                questions = []
                for item in data:
                    question = ParsedQuestion(
                        title=item.get("title", ""),
                        answer=item.get("answer", ""),
                        source_url=item.get("source_url", ""),
                        tags=item.get("tags", []),
                        importance_score=item.get("importance_score", 0.0),
                        difficulty=item.get("difficulty", "medium"),
                        category=item.get("category", ""),
                    )
                    if question.title and question.answer:
                        questions.append(question)

                return questions
            else:
                logger.warning("未找到有效的JSON数组格式")
                logger.debug("完整响应内容:\n%s", response)
                # 尝试从截断的JSON中恢复数据（针对JSON被截断的情况）
                return self._try_recover_from_truncated_json(response)
        except json.JSONDecodeError as e:
            logger.error("JSON解析失败: %s", str(e))
            logger.debug("完整响应内容:\n%s", response)
            # 尝试从截断的JSON中恢复数据
            return self._try_recover_from_truncated_json(response)
        except Exception as e:
            logger.error("解析响应失败: %s", str(e))
            logger.debug("完整响应内容:\n%s", response)
            import traceback
            logger.error(traceback.format_exc())

        return []

    def _fix_json_format(self, json_str: str) -> str:
        """
        尝试修复常见的JSON格式问题

        主要处理：
        1. 字符串内部未转义的引号
        2. 多行字符串中的引号
        """
        import re

        # 方法1：使用状态机遍历整个字符串，正确处理转义字符
        result = []
        in_string = False
        escape_next = False

        for i, char in enumerate(json_str):
            if escape_next:
                result.append(char)
                escape_next = False
                continue

            if char == '\\' and in_string:
                result.append(char)
                escape_next = True
                continue

            if char == '"':
                if in_string:
                    # 检查这是否是字符串结束引号
                    # 向后查找下一个非空白字符
                    remaining = json_str[i + 1:]
                    next_non_whitespace = remaining.lstrip()

                    # 如果后面不是逗号、右括号、右方括号、换行符或字符串结束，
                    # 则认为这是字符串内部的引号，需要转义
                    if next_non_whitespace:
                        next_char = next_non_whitespace[0]
                        if next_char not in (',', ']', '}', '\n', '\r'):
                            # 这是字符串内部的引号，需要转义
                            result.append('\\')
                in_string = not in_string

            result.append(char)

        fixed_str = ''.join(result)

        # 方法2：额外修复常见的中文引号问题
        # 将中文引号替换为英文引号（如果它们在字符串内部）
        fixed_str = re.sub(r'("[^"]*?)"([^"]*?)([^"]*?")', r'\1"\2"\3', fixed_str)

        return fixed_str

    def _try_recover_from_truncated_json(self, response: str) -> List[ParsedQuestion]:
        """
        尝试从截断的JSON中恢复数据

        当LLM输出被截断时（例如max_tokens限制），尝试提取已生成的有效问题
        """
        questions = []

        try:
            logger.info("开始尝试从截断的JSON中恢复数据...")
            # 清理响应文本
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            # 查找JSON数组开始位置
            start = cleaned_response.find("[")
            if start == -1:
                logger.warning("无法找到JSON数组起始位置")
                logger.debug(f"完整响应内容:\n{response}")
                return []

            # 提取从 [ 开始的内容
            json_content = cleaned_response[start:]
            logger.info(f"提取到JSON内容长度: {len(json_content)} 字符")

            # 优先使用 json-repair 修复
            if JSON_REPAIR_AVAILABLE:
                try:
                    repaired_json = repair_json(json_content)
                    data = json.loads(repaired_json)
                    if len(data) > 0:
                        logger.info(f"使用 json-repair 从截断JSON中成功恢复 {len(data)} 个问题")
                    else:
                        logger.debug("使用 json-repair 解析成功但未提取到问题")

                    for item in data:
                        question = ParsedQuestion(
                            title=item.get("title", ""),
                            answer=item.get("answer", ""),
                            source_url=item.get("source_url", ""),
                            tags=item.get("tags", []),
                            importance_score=item.get("importance_score", 0.0),
                            difficulty=item.get("difficulty", "medium"),
                            category=item.get("category", ""),
                        )
                        if question.title and question.answer:
                            questions.append(question)

                    return questions
                except Exception as e:
                    logger.debug(f"json-repair 恢复失败: {str(e)}，尝试内置方法")

            # 如果 json-repair 不可用或失败，使用原有逻辑
            # 尝试找到最后一个完整的对象结束位置 }
            last_complete_pos = -1
            brace_count = 0
            in_string = False
            escape_next = False

            for i, char in enumerate(json_content):
                if escape_next:
                    escape_next = False
                    continue

                if char == '\\' and in_string:
                    escape_next = True
                    continue

                if char == '"':
                    in_string = not in_string
                    continue

                if in_string:
                    continue

                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        last_complete_pos = i

            # 如果找到了完整的对象，尝试构建有效的JSON数组
            if last_complete_pos > 0:
                # 截取到最后一个完整对象的位置，并添加 ]
                truncated_json = json_content[:last_complete_pos + 1] + "]"

                # 尝试修复并解析
                truncated_json = self._fix_json_format(truncated_json)

                try:
                    data = json.loads(truncated_json)
                    if len(data) > 0:
                        logger.info(f"从截断JSON中成功恢复 {len(data)} 个问题")
                    else:
                        logger.debug("截断JSON恢复成功但未提取到问题")

                    for item in data:
                        question = ParsedQuestion(
                            title=item.get("title", ""),
                            answer=item.get("answer", ""),
                            source_url=item.get("source_url", ""),
                            tags=item.get("tags", []),
                            importance_score=item.get("importance_score", 0.0),
                            difficulty=item.get("difficulty", "medium"),
                            category=item.get("category", ""),
                        )
                        if question.title and question.answer:
                            questions.append(question)

                    return questions
                except json.JSONDecodeError as e:
                    logger.debug(f"截断JSON恢复失败: {str(e)}")
            else:
                logger.warning("未找到完整的JSON对象")

        except Exception as e:
            logger.error(f"截断JSON恢复过程出错: {str(e)}")
            logger.error(f"完整响应内容:\n{response}")
            import traceback
            logger.error(traceback.format_exc())

        return questions

    def _extract_tags(self, text: str) -> List[str]:
        """
        从文本中提取标签
        """
        tag_keywords = {
            "Python": ["python", "python3", "py"],
            "Java": ["java", "jdk", "jvm"],
            "算法": ["算法", "排序", "查找", "复杂度"],
            "数据库": ["数据库", "mysql", "sql", "redis"],
            "网络": ["tcp", "http", "网络", "协议"],
            "操作系统": ["操作系统", "进程", "线程", "内存"],
            "设计模式": ["设计模式", "模式", "架构"],
            "前端": ["前端", "javascript", "vue", "react"],
            "后端": ["后端", "api", "服务端"],
            "面试": ["面试", "面经"],
        }

        tags = []
        text_lower = text.lower()

        for tag, keywords in tag_keywords.items():
            if any(keyword.lower() in text_lower for keyword in keywords):
                tags.append(tag)

        return tags if tags else ["其他"]

    def generate_answer(self, question: str) -> str | None:
        """
        使用大模型生成答案

        参数:
            question: 问题文本

        返回:
            生成的答案
        """
        if not self.client:
            return "大模型服务未配置"

        try:
            response = self.client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的技术面试官和解答者。请详细解答以下技术问题。",
                    },
                    {"role": "user", "content": question},
                ],
                temperature=0.5,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"生成答案失败: {str(e)}")
            return f"生成答案失败: {str(e)}"

    def _call_llm(self, prompt: str, max_retries: int = 3) -> str:
        """
        调用大模型，带重试机制
        """
        if not self.client:
            raise Exception("大模型客户端未初始化")

        # 确保token限制已初始化
        if self.max_output_tokens is None:
            self._detect_model_limits()

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=self.max_output_tokens,  # 使用配置的max_output_tokens
                )
                content = response.choices[0].message.content
                if content is None:
                    raise Exception("大模型未返回内容")
                return content
            except Exception as e:
                logger.warning(f"大模型调用失败（第{attempt + 1}次）: {str(e)}")
                if attempt < max_retries - 1:
                    import time

                    time.sleep(2 ** attempt)  # 指数退避

        raise Exception(f"大模型调用失败，已重试{max_retries}次")
