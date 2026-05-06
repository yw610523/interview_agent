# 前端安装和运行说明

## 前置要求

在启动前端之前，请确保已安装：

- **Node.js** >= 16.0.0
- **npm** >= 8.0.0

检查版本：
```bash
node -v
npm -v
```

如果未安装Node.js，请访问 [https://nodejs.org/](https://nodejs.org/) 下载并安装。

## 安装步骤

### 1. 进入前端目录

```bash
cd frontend
```

### 2. 安装依赖

```bash
npm install
```

这将安装以下主要依赖：
- vue@^3.3.11
- vue-router@^4.2.5
- ant-design-vue@^4.0.0
- axios@^1.6.2
- pinia@^2.1.7
- dayjs@^1.11.10

安装过程可能需要几分钟，请耐心等待。

### 3. 确认后端服务运行

前端需要连接到后端API，请确保后端服务正在运行：

```bash
# 在项目根目录
python -m app.main
```

后端默认运行在 `http://localhost:8000`

## 运行前端

### 开发模式

```bash
npm run dev
```

启动成功后会显示：
```
  VITE v5.0.8  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

访问 http://localhost:3000 即可使用应用。

### 生产构建

```bash
npm run build
```

构建产物将输出到 `dist` 目录。

### 预览生产构建

```bash
npm run preview
```

## 常见问题

### Q1: npm install 失败

**可能原因**: 
- 网络连接问题
- Node.js版本过低

**解决方案**:
```bash
# 清理缓存
npm cache clean --force

# 删除node_modules重新安装
rm -rf node_modules package-lock.json
npm install

# 或使用国内镜像
npm install --registry=https://registry.npmmirror.com
```

### Q2: 前端无法连接后端

**检查清单**:
1. ✅ 后端服务是否运行（http://localhost:8000）
2. ✅ 访问 http://localhost:8000/docs 确认API可访问
3. ✅ 检查浏览器控制台是否有CORS错误
4. ✅ 确认vite.config.js中的代理配置正确

**解决方案**:
编辑 `vite.config.js`，确保proxy配置正确：
```javascript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
    '/questions': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
    '/crawl': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    }
  }
}
```

### Q3: 页面空白或报错

**排查步骤**:
1. 打开浏览器开发者工具（F12）
2. 查看Console标签页的错误信息
3. 查看Network标签页的API请求状态

**常见错误**:
- `404 Not Found`: 后端API路径错误或后端未启动
- `500 Internal Server Error`: 后端处理出错，查看后端日志
- `CORS Error`: 跨域问题，检查代理配置

### Q4: 样式显示异常

**解决方案**:
```bash
# 清除浏览器缓存
# 或强制刷新
Ctrl + Shift + R (Windows/Linux)
Cmd + Shift + R (Mac)

# 重新安装依赖
rm -rf node_modules
npm install
```

## 端口修改

如果需要修改前端端口，编辑 `vite.config.js`:

```javascript
server: {
  port: 3000,  // 修改为你想要的端口
  // ...
}
```

## 环境变量

如需配置不同的后端地址，可以创建 `.env` 文件：

```env
VITE_API_BASE_URL=http://localhost:8000
```

然后在代码中使用：
```javascript
const apiBase = import.meta.env.VITE_API_BASE_URL
```

## 浏览器支持

推荐使用以下浏览器：
- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## 开发建议

### 热更新
开发模式下，修改代码会自动刷新浏览器，无需手动重启。

### 调试技巧
1. 使用Vue DevTools浏览器扩展
2. 在组件中使用console.log调试
3. 利用浏览器的Source Map功能

### 代码规范
- 使用Composition API
- 组件名使用PascalCase
- 文件结构保持一致性

## 下一步

安装完成后，请参考：
- [QUICKSTART.md](../QUICKSTART.md) - 快速启动指南
- [frontend/README.md](README.md) - 前端详细说明
- [FRONTEND_SUMMARY.md](../FRONTEND_SUMMARY.md) - 功能总结

## 技术支持

如遇到问题，请检查：
1. 项目文档
2. 浏览器控制台错误
3. 后端服务日志
4. Network请求状态

祝使用愉快！🎉
