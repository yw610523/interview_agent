<template>
  <a-config-provider :locale="zhCN">
    <div id="app">
      <a-layout style="height: 100vh">
        <a-layout-header class="header">
          <div class="logo">
            <h1 style="color: white; margin: 0; font-size: 1.2rem;">🎯 Interview AI</h1>
          </div>
          <a-menu
            v-model:selectedKeys="selectedKeys"
            theme="dark"
            mode="horizontal"
            :style="{ lineHeight: '64px' }"
            class="desktop-menu"
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
            <a-menu-item key="/settings">
              <router-link to="/settings">系统设置</router-link>
            </a-menu-item>
          </a-menu>
          <div class="mobile-menu-toggle" @click="toggleMobileMenu">
            <MenuOutlined />
          </div>
        </a-layout-header>
        
        <!-- Mobile Menu Drawer -->
        <a-drawer
          v-model:open="mobileMenuVisible"
          title="菜单"
          placement="right"
          :width="250"
          class="mobile-drawer"
        >
          <a-menu
            v-model:selectedKeys="selectedKeys"
            theme="light"
            mode="inline"
            @click="handleMobileMenuClick"
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
            <a-menu-item key="/settings">
              <router-link to="/settings">系统设置</router-link>
            </a-menu-item>
          </a-menu>
        </a-drawer>
        
        <a-layout-content style="padding: 0; background: #ffffff; overflow: hidden;">
          <router-view />
        </a-layout-content>
        
        <a-layout-footer style="text-align: center; background: #ffffff; padding: 12px 24px; height: 48px; line-height: 24px; color: #8c8c8c; border-top: 1px solid #f0f0f0;">
          Interview AI Agent ©2024 - 智能面试题管理系统
        </a-layout-footer>
      </a-layout>
    </div>
  </a-config-provider>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { MenuOutlined } from '@ant-design/icons-vue'

const route = useRoute()
const selectedKeys = ref([route.path])
const mobileMenuVisible = ref(false)

watch(() => route.path, (newPath) => {
  selectedKeys.value = [newPath]
})

const toggleMobileMenu = () => {
  mobileMenuVisible.value = !mobileMenuVisible.value
}

const handleMobileMenuClick = () => {
  mobileMenuVisible.value = false
}
</script>

<style>
html, body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  height: 100%;
}

#app {
  height: 100%;
  overflow-y: auto;
}

.header {
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.logo {
  margin-right: 48px;
}

.mobile-menu-toggle {
  display: none;
  color: white;
  font-size: 20px;
  cursor: pointer;
  padding: 0 12px;
}

@media (max-width: 768px) {
  .desktop-menu {
    display: none;
  }
  
  .mobile-menu-toggle {
    display: block;
  }
  
  .logo h1 {
    font-size: 1rem;
  }
  
  .header {
    padding: 0 16px;
  }
}
</style>
