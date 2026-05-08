"""
Firecrawl MCP 集成测试

此脚本演示如何使用 Firecrawl MCP 服务解析动态网页。
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.firecrawl_mcp import FirecrawlMCPService  # noqa: E402


async def test_firecrawl_scrape():
    """测试 Firecrawl 爬取功能"""

    # 配置 Firecrawl 服务（使用自托管）
    firecrawl = FirecrawlMCPService(
        api_url="http://localhost:3002",  # Docker 部署后的地址
        timeout=60,
        use_official_api=False,
    )

    # 检查服务是否可用
    if not firecrawl.is_available():
        print("❌ Firecrawl 服务不可用，请确保已启动 Docker 服务")
        print("运行: docker-compose up -d firecrawl")
        return

    print("✅ Firecrawl 服务已连接")

    # 测试爬取一个动态网页
    test_urls = [
        "https://example.com",
        "https://news.ycombinator.com",
    ]

    for url in test_urls:
        print(f"\n🔍 正在爬取: {url}")
        result = await firecrawl.scrape_url(
            url=url,
            formats=["markdown", "html"],
            only_main_content=True,
        )

        if result.success:
            print(f"✅ 成功!")
            print(f"   标题: {result.title}")
            print(f"   Markdown 长度: {len(result.markdown) if result.markdown else 0} 字符")
            print(f"   元数据: {result.metadata}")

            # 显示前 500 个字符的 markdown 内容
            if result.markdown:
                preview = result.markdown[:500].replace('\n', ' ')
                print(f"   预览: {preview}...")
        else:
            print(f"❌ 失败: {result.error}")


async def test_firecrawl_map():
    """测试 Firecrawl Map 功能"""

    firecrawl = FirecrawlMCPService(
        api_url="http://localhost:3002",
        timeout=60,
    )

    if not firecrawl.is_available():
        print("❌ Firecrawl 服务不可用")
        return

    print("\n🗺️  测试 URL Map 功能")
    result = await firecrawl.map_url(
        url="https://example.com",
        limit=10,
    )

    if result.get("success"):
        urls = result.get("links", [])
        print(f"✅ 发现 {len(urls)} 个 URL:")
        for url in urls[:5]:  # 只显示前 5 个
            print(f"   - {url}")
    else:
        print(f"❌ Map 失败: {result.get('error')}")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("Firecrawl MCP 集成测试")
    print("=" * 60)

    # 测试爬取功能
    await test_firecrawl_scrape()

    # 测试 Map 功能
    await test_firecrawl_map()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
