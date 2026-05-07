"""
测试微信公众号文章标题提取
"""
import logging
from app.services.url_scanner import URLScanner
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


# 配置日志
logging.basicConfig(level=logging.DEBUG)


def test_wechat_title_extraction():
    """测试微信公众号文章标题提取"""

    # 示例微信公众号文章URL（可以替换为实际的公众号文章链接）
    test_urls = [
        # 这里填写您要测试的微信公众号文章URL
        # 例如: "https://mp.weixin.qq.com/s/xxxxx"
    ]

    if not test_urls:
        print("请在测试文件中添加要测试的微信公众号文章URL")
        return

    scanner = URLScanner()

    for url in test_urls:
        print(f"\n{'=' * 60}")
        print(f"测试URL: {url}")
        print('=' * 60)

        result = scanner.scan(url)

        if result.error:
            print(f"❌ 错误: {result.error}")
        else:
            print(f"✅ 状态码: {result.status_code}")
            print(f"📝 标题: {result.title or '(空)'}")
            print(f"📊 字数: {result.word_count}")
            print(f"⏱️ 加载时间: {result.load_time:.2f}秒")

            # 检查HTML中是否包含常见的微信公众号标题元素
            if result.html_content:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.html_content, 'html.parser')

                # 检查各种可能的标题来源
                checks = [
                    ('og:title', soup.find('meta', property='og:title')),
                    ('twitter:title', soup.find('meta', attrs={'name': 'twitter:title'})),
                    ('<title>', soup.find('title')),
                    ('#activity-name', soup.find(id='activity-name')),
                    ('.rich_media_title', soup.find(class_='rich_media_title')),
                    ('<h1>', soup.find('h1')),
                ]

                print("\n🔍 标题来源检查:")
                for name, element in checks:
                    if element:
                        content = element.get(
                            'content') or element.get_text(strip=True)
                        print(f"  ✓ {name}: {content[:50]}...")
                    else:
                        print(f"  ✗ {name}: 未找到")


if __name__ == "__main__":
    test_wechat_title_extraction()
