"""
测试单页爬取接口
"""
import requests
import json


def test_single_page_crawl():
    """测试单页爬取接口"""
    
    # 测试URL - 可以替换为任何包含技术内容的页面
    test_url = "https://www.runoob.com/python3/python3-tutorial.html"
    
    # API端点
    api_url = "http://localhost:8000/crawl/single-page"
    
    print(f"正在测试单页爬取接口...")
    print(f"目标URL: {test_url}")
    
    try:
        # 发送POST请求
        response = requests.post(api_url, params={"url": test_url})
        
        # 检查响应状态码
        if response.status_code == 200:
            result = response.json()
            print("✅ 接口调用成功!")
            print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 验证返回的数据结构
            assert "status" in result
            assert "message" in result
            assert "url" in result
            assert "parsed_questions" in result
            assert "inserted_questions" in result
            
            print("\n✅ 数据结构验证通过!")
            return True
        else:
            print(f"❌ 接口调用失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出现异常: {str(e)}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("单页爬取接口测试")
    print("=" * 50)
    
    success = test_single_page_crawl()
    
    if success:
        print("\n🎉 所有测试通过!")
    else:
        print("\n💥 测试失败!")
