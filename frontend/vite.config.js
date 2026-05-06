import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
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
})
