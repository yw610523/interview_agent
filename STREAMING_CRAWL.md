# 边扫描边解析功能说明

## 概述

本次修改实现了"边扫描边解析"的流式处理模式，改变了原来"先扫描所有页面再统一处理"的批处理方式。

## 修改内容

### 1. SitemapCrawler 修改 (`app/services/sitemap_crawler.py`)

在 `crawl()` 方法中添加了新的参数 `page_processed_callback`：

```python
def crawl(
    self,
    sitemap_url: Optional[str] = None,
    progress_callback: Optional[Callable[[ScanResult, int, int], None]] = None,
    page_processed_callback: Optional[Callable[[Dict[str, Any]], None]] = None,  # 新增
) -> List[ScanResult]:
```

**工作原理：**
- 每扫描完一个URL，如果扫描成功（无错误），立即调用 `page_processed_callback`
- 回调函数接收页面的字典格式数据（通过 `result.to_dict()` 转换）
- 失败的页面不会触发回调

**关键代码：**
```python
# 如果提供了页面处理回调，立即调用
if page_processed_callback and not result.error:
    try:
        page_data = result.to_dict()
        page_processed_callback(page_data)
        logger.info(f"页面 {url} 已触发实时处理回调")
    except Exception as e:
        logger.error(f"页面处理回调失败: {str(e)}")
```

### 2. main.py 修改 (`app/main.py`)

在 `run_crawler()` 函数中实现了逐页处理逻辑：

**主要变化：**
1. 定义了 `on_page_processed` 回调函数，用于处理每个扫描完成的页面
2. 在回调内部调用大模型服务处理单个页面
3. 使用嵌套的 `on_question_found` 回调实现即时入库
4. 将回调传递给 `crawler.crawl()` 方法

**处理流程：**
```
扫描页面1 → 触发回调 → 调用大模型 → 识别问题 → 立即入库
扫描页面2 → 触发回调 → 调用大模型 → 识别问题 → 立即入库
扫描页面3 → 触发回调 → 调用大模型 → 识别问题 → 立即入库
...
```

## 优势

### 原来的批处理方式
- ❌ 需要等待所有页面扫描完成才能开始处理
- ❌ 内存占用高（需要存储所有页面数据）
- ❌ 如果中途失败，之前扫描的结果无法利用
- ❌ 用户需要长时间等待才能看到结果

### 现在的流式处理方式
- ✅ 扫描一个页面立即处理一个，无需等待
- ✅ 内存占用低（只需处理当前页面）
- ✅ 即使中途失败，已处理的页面已经入库
- ✅ 用户可以实时看到处理进度和结果
- ✅ 更适合大规模爬取任务

## 测试验证

运行测试脚本验证回调机制：

```bash
python test_callback.py
```

测试结果显示：
- ✓ 只有成功的页面触发了回调
- ✓ 失败的页面不会触发回调
- ✓ 回调触发次数与成功扫描数一致

## 使用示例

### 基本用法

```python
from app.services.sitemap_crawler import SitemapCrawler
from app.config.crawler_config import CrawlerConfig

# 创建配置
config = CrawlerConfig(
    sitemap_url="https://example.com/sitemap.xml",
    max_urls=100,
)

# 创建爬虫
crawler = SitemapCrawler(config=config)

# 定义页面处理回调
def on_page_processed(page_data):
    url = page_data.get('url', '')
    title = page_data.get('title', '')
    content = page_data.get('text_content', '')
    
    print(f"处理页面: {url}")
    # 在这里进行页面处理，如调用大模型、保存到数据库等
    
# 启动爬虫，传入回调
results = crawler.crawl(page_processed_callback=on_page_processed)
```

### 与大模型集成

```python
def on_page_processed(page_data):
    # 将单个页面转换为列表格式
    page_list = [page_data]
    
    # 定义问题发现回调
    def on_question_found(questions):
        for q in questions:
            # 保存问题到数据库
            save_question(q)
    
    # 调用大模型处理
    parsed_questions = llm_service.parse_crawl_results(
        page_list, 
        on_question_found=on_question_found
    )
```

## 注意事项

1. **错误处理**：回调函数中的异常不会影响爬虫继续运行，但会记录错误日志
2. **性能考虑**：如果页面处理耗时较长，可能会影响整体爬取速度
3. **并发控制**：当前是串行处理，如需并发可考虑异步方案
4. **资源管理**：确保回调函数正确释放资源（如数据库连接）

## 兼容性

- ✅ 向后兼容：如果不传 `page_processed_callback` 参数，行为与原来一致
- ✅ 可选功能：该功能是可选的，不影响现有代码
- ✅ 灵活扩展：可以轻松添加其他回调逻辑

## 相关文件

- `app/services/sitemap_crawler.py` - 爬虫核心逻辑
- `app/main.py` - 主应用入口
- `app/services/llm_service.py` - 大模型服务
- `test_callback.py` - 回调机制测试脚本
