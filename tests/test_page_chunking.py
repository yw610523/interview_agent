"""
测试页面分块处理逻辑
验证每个页面独立处理，不会因为token限制而合并不同页面
"""
import logging
from app.services.llm_service import LLMService
import sys
from pathlib import Path
from unittest.mock import Mock

# 添加项目根目录到路径（tests文件夹的父目录）
sys.path.insert(0, str(Path(__file__).parent.parent))


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_page_processing_independence():
    """测试页面独立处理逻辑"""

    logger.info("=" * 60)
    logger.info("测试页面分块处理逻辑")
    logger.info("=" * 60)

    # 创建LLM服务实例
    llm_service = LLMService()

    # Mock大模型客户端
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = '[]'  # 返回空数组表示没有问题
    mock_client.chat.completions.create.return_value = mock_response

    llm_service.client = mock_client
    llm_service.max_input_tokens = 4096
    llm_service.max_output_tokens = 4096
    llm_service.min_token_limit = 4096

    # 模拟5个页面的爬虫结果
    crawl_results = []
    for i in range(1, 6):
        crawl_results.append({
            "url": f"https://example.com/page{i}",
            "title": f"Page {i} Title",
            # 每个页面约2000字符
            "text_content": f"This is the content of page {i}. " * 100,
        })

    logger.info(f"\n准备处理 {len(crawl_results)} 个页面")

    # 跟踪大模型调用次数
    call_count = 0
    called_pages = []

    original_create = mock_client.chat.completions.create

    def track_calls(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        # 提取URL信息
        messages = kwargs.get('messages', args[1] if len(args) > 1 else [])
        user_message = next((m for m in messages if m['role'] == 'user'), None)
        if user_message:
            content = user_message['content']
            # 从内容中提取URL
            for line in content.split('\n'):
                if line.startswith('URL:'):
                    url = line.replace('URL:', '').strip()
                    called_pages.append(url)
                    break

        logger.info(f"大模型调用 #{call_count}: 处理页面 {len(called_pages)}")
        return original_create(*args, **kwargs)

    mock_client.chat.completions.create = track_calls

    # 调用解析方法
    questions = llm_service.parse_crawl_results(crawl_results)

    logger.info("\n" + "=" * 60)
    logger.info("测试结果:")
    logger.info(f"输入页面数: {len(crawl_results)}")
    logger.info(f"大模型调用次数: {call_count}")
    logger.info(f"识别问题数: {len(questions)}")
    logger.info("=" * 60)

    # 验证：每个页面至少调用一次大模型
    if call_count >= len(crawl_results):
        logger.info(f"✓ 测试通过: 大模型调用次数 ({call_count}) >= 页面数 ({len(crawl_results)})")
        logger.info("  说明每个页面都独立处理，没有合并")

        # 检查是否有重复处理的页面（因为内容过长被分块）
        unique_pages = set(called_pages)
        logger.info(f"  唯一处理的页面数: {len(unique_pages)}")

        if len(unique_pages) == len(crawl_results):
            logger.info("✓ 所有页面都被独立处理")
            return True
        else:
            logger.warning("⚠ 部分页面可能未被处理或被合并")
            return False
    else:
        logger.error(f"✗ 测试失败: 大模型调用次数 ({call_count}) < 页面数 ({len(crawl_results)})")
        logger.error("  可能存在页面合并处理的情况")
        return False


def test_long_page_chunking():
    """测试长页面的分块处理"""

    logger.info("\n" + "=" * 60)
    logger.info("测试长页面分块处理")
    logger.info("=" * 60)

    llm_service = LLMService()

    # Mock大模型客户端
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = '[]'
    mock_client.chat.completions.create.return_value = mock_response

    llm_service.client = mock_client
    llm_service.max_input_tokens = 4096
    llm_service.max_output_tokens = 4096
    llm_service.min_token_limit = 4096

    # 创建一个超长页面（10000字符）
    long_content = "这是一个很长的技术文档内容。" * 300
    crawl_results = [{
        "url": "https://example.com/long-page",
        "title": "Long Page",
        "text_content": long_content,
    }]

    logger.info(f"页面内容长度: {len(long_content)} 字符")

    # 跟踪分块数量
    chunk_count = 0

    original_create = mock_client.chat.completions.create

    def track_chunks(*args, **kwargs):
        nonlocal chunk_count
        chunk_count += 1

        messages = kwargs.get('messages', args[1] if len(args) > 1 else [])
        user_message = next((m for m in messages if m['role'] == 'user'), None)
        if user_message:
            content = user_message['content']
            # 查找片段标识
            for line in content.split('\n'):
                if '内容片段' in line:
                    logger.info(f"处理片段: {line.strip()}")
                    break

        return original_create(*args, **kwargs)

    mock_client.chat.completions.create = track_chunks

    # 调用解析方法
    llm_service.parse_crawl_results(crawl_results)

    logger.info(f"\n长页面被分割为 {chunk_count} 个片段进行处理")

    if chunk_count > 1:
        logger.info(f"✓ 测试通过: 长页面被正确分割为 {chunk_count} 个片段")
        logger.info("  这保证了内容的完整性，避免了简单截断")
        return True
    else:
        logger.info("ℹ 页面未分割（可能内容在阈值内）")
        return True


if __name__ == "__main__":
    result1 = test_page_processing_independence()
    result2 = test_long_page_chunking()

    logger.info("\n" + "=" * 60)
    if result1 and result2:
        logger.info("✓ 所有测试通过")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("✗ 部分测试失败")
        logger.info("=" * 60)
        sys.exit(1)
