# 单页爬取接口使用说明

## 概述

`/crawl/single-page` 接口允许您快速爬取和分析单个技术页面，自动识别其中的面试问题并存入向量数据库。

## 接口信息

- **URL**: `POST /crawl/single-page`
- **参数**: 
  - `url` (string): 要爬取的页面URL
- **返回**: JSON格式的爬取结果

## 使用示例

### cURL示例

```bash
curl -X POST "http://localhost:8000/crawl/single-page?url=https://www.runoob.com/python3/python3-tutorial.html"
```

### Python示例

```python
import requests

url = "https://www.runoob.com/python3/python3-tutorial.html"
response = requests.post("http://localhost:8000/crawl/single-page", params={"url": url})

if response.status_code == 200:
    result = response.json()
    print(f"识别到 {result['parsed_questions']} 个问题")
else:
    print(f"错误: {response.text}")
```

## 响应格式

成功响应示例：

```json
{
  "status": "success",
  "message": "页面爬取完成",
  "url": "https://www.runoob.com/python3/python3-tutorial.html",
  "title": "Python3 教程",
  "parsed_questions": 5,
  "inserted_questions": 5,
  "word_count": 1234,
  "load_time": 1.23
}
```

字段说明：
- `status`: 状态 ("success" 或 "error")
- `message`: 描述信息
- `url`: 爬取的URL
- `title`: 页面标题
- `parsed_questions`: 识别到的问题数量
- `inserted_questions`: 成功插入向量数据库的问题数量
- `word_count`: 页面字数
- `load_time`: 页面加载时间(秒)

## 适用场景

1. **临时分析特定技术文章**: 快速分析某篇技术博客或文档
2. **验证内容质量**: 检查某个页面是否包含有价值的面试问题
3. **增量更新**: 当发现新的优质技术内容时，单独爬取
4. **调试和测试**: 测试AI识别效果

## 注意事项

1. 确保目标URL可访问且包含技术相关内容
2. 页面内容应足够丰富以提取有意义的面试问题
3. 大模型API调用可能需要几秒钟时间
4. 如果页面内容过长，会自动进行分块处理

## 与完整爬虫的区别

| 特性 | 单页爬取 | 完整爬虫 |
|------|----------|----------|
| 范围 | 单个URL | 整个网站(Sitemap) |
| 速度 | 快速 | 较慢(取决于页面数量) |
| 用途 | 临时分析 | 批量处理 |
| 配置 | 无需配置 | 需要配置文件 |
| URL过滤 | 不适用 | 支持 |

## 错误处理

常见错误：
- `400`: 页面扫描失败(网络错误、SSL错误等)
- `500`: 服务器内部错误(大模型API失败等)

错误响应示例：
```json
{
  "detail": "页面扫描失败: Request timed out after 30 seconds"
}
```