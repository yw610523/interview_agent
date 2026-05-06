"""
单页爬取接口使用示例
"""
import requests
import json


def crawl_single_page_example():
    """单页爬取示例"""
    
    # 示例URL列表 - 可以替换为任何包含技术内容的页面
    example_urls = [
        "https://www.runoob.com/python3/python3-tutorial.html",
        "https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Guide",
        "https://docs.python.org/3/tutorial/index.html"
    ]
    
    # API端点
    api_url = "http://localhost:8000/crawl/single-page"
    
    print("单页爬取接口使用示例")
    print("=" * 50)
    
    for i, url in enumerate(example_urls, 1):
        print(f"\n[{i}] 正在爬取: {url}")
        
        try:
            # 发送POST请求
            response = requests.post(api_url, params={"url": url})
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 成功! 识别到 {result['parsed_questions']} 个问题")
                print(f"   标题: {result.get('title', 'N/A')}")
                print(f"   字数: {result.get('word_count', 0)}")
                print(f"   耗时: {result.get('load_time', 0):.2f}秒")
            else:
                print(f"❌ 失败! 状态码: {response.status_code}")
                print(f"   错误: {response.text}")
                
        except Exception as e:
            print(f"❌ 异常: {str(e)}")
    
    print("\n" + "=" * 50)
    print("示例完成!")


def batch_crawl_example():
    """批量爬取示例"""
    
    # 批量URL列表
    urls_to_crawl = [
        "https://www.runoob.com/python3/python3-basic-syntax.html",
        "https://www.runoob.com/python3/python3-variable-types.html",
        "https://www.runoob.com/python3/python3-operator.html"
    ]
    
    api_url = "http://localhost:8000/crawl/single-page"
    
    print("\n批量爬取示例")
    print("=" * 50)
    
    total_questions = 0
    success_count = 0
    
    for url in urls_to_crawl:
        try:
            response = requests.post(api_url, params={"url": url})
            if response.status_code == 200:
                result = response.json()
                total_questions += result.get('parsed_questions', 0)
                success_count += 1
                print(f"✓ {url.split('/')[-1]}: {result.get('parsed_questions', 0)} 个问题")
            else:
                print(f"✗ {url.split('/')[-1]}: 失败")
        except Exception as e:
            print(f"✗ {url.split('/')[-1]}: {str(e)}")
    
    print(f"\n总计: {success_count}/{len(urls_to_crawl)} 成功, 共识别 {total_questions} 个问题")


if __name__ == "__main__":
    # 运行示例
    crawl_single_page_example()
    
    # 如果需要批量爬取，取消下面注释
    # batch_crawl_example()