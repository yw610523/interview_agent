import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    host: '0.0.0.0',  // 明确指定监听所有接口
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',  // 使用 127.0.0.1 而不是 localhost
        changeOrigin: true,
      }
    }
  },
  optimizeDeps: {
    include: ['ant-design-vue']
  }
})
