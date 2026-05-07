"""
URL过滤器测试脚本
"""

import logging
from app.services.url_filter import URLFilter, URLFilterConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def test_url_filter():
    """测试URL过滤器功能"""

    print("=" * 60)
    print("URL过滤器功能测试")
    print("=" * 60)

    # 测试1: 只使用exclude规则
    print("\n【测试1】只使用exclude规则")
    config1 = URLFilterConfig(
        exclude_patterns=["/admin/", "/private/", "\\.pdf$"]
    )
    filter1 = URLFilter(config1)

    test_urls_1 = [
        "https://example.com/docs/intro.html",
        "https://example.com/admin/dashboard.html",
        "https://example.com/api/users.html",
        "https://example.com/private/data.html",
        "https://example.com/files/report.pdf",
        "https://example.com/blog/post1.html"
    ]

    print(f"\n原始URL列表 ({len(test_urls_1)}个):")
    for url in test_urls_1:
        print(f"  - {url}")

    filtered_1 = filter1.filter_urls(test_urls_1)
    print(f"\n过滤后URL列表 ({len(filtered_1)}个):")
    for url in filtered_1:
        print(f"  ✓ {url}")

    # 测试2: 只使用include规则
    print("\n\n【测试2】只使用include规则")
    config2 = URLFilterConfig(
        include_patterns=["/docs/", "/api/"]
    )
    filter2 = URLFilter(config2)

    test_urls_2 = [
        "https://example.com/docs/intro.html",
        "https://example.com/admin/dashboard.html",
        "https://example.com/api/users.html",
        "https://example.com/blog/post1.html",
        "https://example.com/about.html"
    ]

    print(f"\n原始URL列表 ({len(test_urls_2)}个):")
    for url in test_urls_2:
        print(f"  - {url}")

    filtered_2 = filter2.filter_urls(test_urls_2)
    print(f"\n过滤后URL列表 ({len(filtered_2)}个):")
    for url in filtered_2:
        print(f"  ✓ {url}")

    # 测试3: 同时使用include和exclude规则
    print("\n\n【测试3】同时使用include和exclude规则")
    config3 = URLFilterConfig(
        include_patterns=["/docs/", "/api/"],
        exclude_patterns=["/admin/", "\\.pdf$"]
    )
    filter3 = URLFilter(config3)

    test_urls_3 = [
        "https://example.com/docs/intro.html",
        "https://example.com/docs/guide.pdf",
        "https://example.com/api/users.html",
        "https://example.com/admin/api/test.html",
        "https://example.com/blog/post1.html"
    ]

    print(f"\n原始URL列表 ({len(test_urls_3)}个):")
    for url in test_urls_3:
        print(f"  - {url}")

    filtered_3 = filter3.filter_urls(test_urls_3)
    print(f"\n过滤后URL列表 ({len(filtered_3)}个):")
    for url in filtered_3:
        print(f"  ✓ {url}")

    # 测试4: 没有过滤规则（允许所有）
    print("\n\n【测试4】没有过滤规则（允许所有）")
    config4 = URLFilterConfig()
    filter4 = URLFilter(config4)

    test_urls_4 = [
        "https://example.com/page1.html",
        "https://example.com/page2.html",
        "https://example.com/page3.html"
    ]

    print(f"\n原始URL列表 ({len(test_urls_4)}个):")
    for url in test_urls_4:
        print(f"  - {url}")

    filtered_4 = filter4.filter_urls(test_urls_4)
    print(f"\n过滤后URL列表 ({len(filtered_4)}个):")
    for url in filtered_4:
        print(f"  ✓ {url}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_url_filter()
