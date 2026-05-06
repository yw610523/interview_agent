# 单页爬取实时日志功能说明

## 功能概述

本次更新为单页爬取功能添加了**真实的实时进度反馈和日志显示**，用户可以在前端界面实时查看爬取过程的详细日志，而不是之前虚假的固定进度条。

## 主要改进

### 1. 后端改进

#### SSE流式接口 (`/api/crawl/single-page/stream`)
- 使用 **Server-Sent Events (SSE)** 技术实现实时日志推送
- 在处理过程中实时发送日志消息和进度信息
- 自动捕获LLM服务的日志输出并推送到前端

#### 实时日志内容
- **页面扫描阶段**: 显示URL扫描状态和内容长度
- **AI分析阶段**: 显示每个chunk的处理进度和识别结果
- **问题入库阶段**: 显示识别到的问题数量和入库状态
- **完成阶段**: 显示总耗时和最终统计信息

### 2. 前端改进

#### 实时日志显示组件
- 新增黑色终端风格的日志显示区域
- 根据日志类型显示不同颜色边框（扫描、分析、处理、完成、错误）
- 自动滚动到最新日志
- 显示每条日志的时间戳

#### SSE客户端连接
- 使用原生 `EventSource` API 建立SSE连接
- 实时接收并解析后端推送的日志消息
- 动态更新进度条和处理消息
- 自动处理连接错误和断开

## 使用方法

### 启动服务

1. **启动后端服务**:
```bash
cd D:\dev\interview_agent
python -m app.main
```

2. **启动前端服务**:
```bash
cd D:\dev\interview_agent\frontend
npm run dev
```

### 测试步骤

1. 打开浏览器访问前端应用
2. 进入"爬虫管理"页面
3. 切换到"单页爬取"标签
4. 输入要爬取的URL（例如: `https://www.runoob.com/python3/python3-tutorial.html`）
5. 点击"开始爬取"按钮
6. 观察实时日志显示区域，您将看到：
   - 实时的处理日志（带时间戳）
   - 动态更新的进度条
   - 不同阶段的彩色标识
   - 最终的处理结果

## 日志类型说明

| 日志类型 | 颜色 | 说明 |
|---------|------|------|
| scanning | 蓝色 | 正在扫描页面 |
| scanned | 绿色 | 页面扫描完成 |
| analyzing | 黄色 | 正在分析页面内容 |
| processing | 黄色 | 正在处理chunk |
| inserting | 紫色 | 正在插入向量数据库 |
| completed | 绿色 | 问题识别完成 |
| finished | 绿色加粗 | 全部处理完成 |
| error | 红色 | 发生错误 |
| info | 灰色 | 一般信息 |

## 技术实现细节

### 后端架构

```python
# SSE流式接口
@app.get("/api/crawl/single-page/stream")
async def crawl_single_page_stream(url: str):
    # 1. 创建日志队列
    log_queue = Queue()
    
    # 2. 定义日志回调函数
    def log_callback(message, progress, step):
        log_queue.put(json.dumps({...}))
    
    # 3. 在后台线程执行爬取
    Thread(target=run_crawl).start()
    
    # 4. 持续从队列读取并发送SSE事件
    while True:
        message = log_queue.get(timeout=1)
        yield f"data: {message}\n\n"
```

### 前端架构

```javascript
// 创建SSE连接
const eventSource = new EventSource(`/api/crawl/single-page/stream?url=${url}`)

// 接收消息
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  if (data.type === 'log') {
    // 添加日志到显示区域
    realtimeLogs.value.push(data)
    // 更新进度
    processingProgress.value = data.progress
  } else if (data.type === 'complete') {
    // 处理完成
    singlePageResult.value = data.result
  }
}
```

## 优势对比

### 之前的实现（虚假进度）
- ❌ 硬编码的固定进度值（20%, 40%, 80%, 90%）
- ❌ 使用定时器模拟进度增长
- ❌ 无法反映实际处理状态
- ❌ 用户看不到详细的处理过程

### 现在的实现（真实进度）
- ✅ 基于实际处理步骤的动态进度
- ✅ 实时推送后端日志到前端
- ✅ 准确反映当前处理状态
- ✅ 用户可以清楚看到每个处理环节
- ✅ 支持错误实时反馈
- ✅ 终端风格的日志显示更专业

## 注意事项

1. **浏览器兼容性**: SSE在现代浏览器中广泛支持，但IE不支持
2. **连接管理**: 当用户开始新的爬取时，会自动关闭之前的SSE连接
3. **内存管理**: 完成后会自动清理日志队列和SSE连接
4. **Nginx配置**: 已添加 `X-Accel-Buffering: no` 头部禁用缓冲，确保实时性

## 故障排查

### 问题1: 日志不显示
- 检查浏览器控制台是否有SSE连接错误
- 确认后端服务正常运行
- 检查网络请求是否被防火墙拦截

### 问题2: 进度不更新
- 确认SSE连接状态（浏览器开发者工具 -> Network）
- 检查后端日志是否有异常
- 尝试刷新页面重新连接

### 问题3: 连接中断
- SSE会自动重连，但如果频繁断开，检查网络连接
- 确认后端没有抛出未处理的异常
- 检查服务器超时设置

## 后续优化建议

1. **日志过滤**: 添加日志级别过滤（只显示重要日志）
2. **日志导出**: 支持将日志导出为文本文件
3. **历史记录**: 保存历史爬取的日志记录
4. **暂停/恢复**: 支持暂停和恢复爬取任务
5. **并发控制**: 限制同时进行的爬取任务数量
