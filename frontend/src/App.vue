<template>
  <a-config-provider :locale="zhCN">
    <div id="app">
      <a-layout style="min-height: 100vh">
        <a-layout-header class="header">
          <div class="logo">
            <h1 style="color: white; margin: 0;">🎯 Interview AI Agent</h1>
          </div>
          <a-menu
            v-model:selectedKeys="selectedKeys"
            theme="dark"
            mode="horizontal"
            :style="{ lineHeight: '64px' }"
          >
            <a-menu-item key="/">
              <router-link to="/">首页</router-link>
            </a-menu-item>
            <a-menu-item key="/crawler">
              <router-link to="/crawler">爬虫管理</router-link>
            </a-menu-item>
            <a-menu-item key="/questions">
              <router-link to="/questions">面试题生成</router-link>
            </a-menu-item>
          </a-menu>
        </a-layout-header>
        
        <a-layout-content style="padding: 24px; background: #f0f2f5;">
          <router-view />
        </a-layout-content>
        
        <a-layout-footer style="text-align: center; background: #f0f2f5;">
          Interview AI Agent ©2024 - 智能面试题管理系统
        </a-layout-footer>
      </a-layout>
    </div>
  </a-config-provider>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import zhCN from 'ant-design-vue/es/locale/zh_CN'

const route = useRoute()
const selectedKeys = ref([route.path])
</script>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.header {
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.logo {
  margin-right: 48px;
}

#app {
  min-height: 100vh;
}
</style>
