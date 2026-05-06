# 快速启动指南

## 完整启动流程

### 1. 启动后端服务

```bash
# 确保已安装Python依赖
pip install -r requirements.txt

# 配置环境变量（如需要）
cp .env.template .env
# 编辑 .env 文件，配置API密钥等

# 启动后端服务
python -m app.main
```

后端服务将在 http://localhost:8000 启动

### 2. 启动前端服务

打开新的终端窗口：

```bash
# 进入前端目录
cd frontend

# 安装依赖（首次运行）
npm install

# 启动开发服务器
npm run dev
```

前端服务将在 http://localhost:3000 启动

### 3. 访问应用

浏览器访问: http://localhost:3000

## 功能使用

### 爬虫管理

1. **批量爬取**
   - 进入"爬虫管理"页面
   - 在"批量爬取"标签页配置参数
   - 点击"保存配置"
   - 点击"立即执行批量爬取"

2. **单页爬取**
   - 进入"爬虫管理"页面
   - 切换到"单页爬取"标签页
   - 输入页面URL
   - 点击"开始爬取"

### 生成面试题

1. 进入"面试题生成"页面
2. 设置筛选条件：
   - 题目数量（1-50）
   - 难度（简单/中等/困难）
   - 分类（如：Python、Java等）
   - 标签（如：算法、数据结构等）
3. 点击"生成题目"
4. 查看生成的题目列表
5. 点击问题展开查看答案

## 常见问题

### Q: 前端无法连接后端？

A: 确保：
1. 后端服务正在运行（http://localhost:8000）
2. 前端代理配置正确（vite.config.js）
3. 没有防火墙阻止连接

### Q: 如何修改后端地址？

A: 编辑 `frontend/vite.config.js` 中的 proxy 配置：

```javascript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://your-backend-url',
      changeOrigin: true,
    },
    // ... 其他配置
  }
}
```

### Q: 生产环境如何部署？

A: 
1. 构建前端：
```bash
cd frontend
npm run build
```

2. 将 `frontend/dist` 目录的内容部署到静态文件服务器

3. 配置反向代理（如Nginx）将API请求转发到后端

### Q: 面试题数量为0？

A: 需要先执行爬取任务，让系统收集面试题数据：
1. 进入"爬虫管理"
2. 执行批量爬取或单页爬取
3. 等待AI识别完成
4. 再去生成面试题

## API测试

也可以使用curl直接测试API：

```bash
# 获取配置
curl http://localhost:8000/api/config

# 生成面试题
curl -X POST "http://localhost:8000/questions/generate-batch?count=5&difficulty=medium"

# 触发爬取
curl http://localhost:8000/crawl/run
```

更多API文档请访问：http://localhost:8000/docs
