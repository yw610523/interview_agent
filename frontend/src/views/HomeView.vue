<template>
  <div class="home-view">
    <!-- 搜索区域 -->
    <div class="search-container">
      <transition name="fade">
        <div v-if="!hasSearched" class="hero-image">
          <svg viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#4096ff;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#69c0ff;stop-opacity:1" />
              </linearGradient>
            </defs>
            <!-- 搜索图标 -->
            <circle cx="70" cy="60" r="25" fill="none" stroke="url(#grad1)" stroke-width="3"/>
            <line x1="88" y1="78" x2="105" y2="95" stroke="url(#grad1)" stroke-width="3" stroke-linecap="round"/>
            <!-- 装饰元素 -->
            <circle cx="140" cy="40" r="8" fill="#4096ff" opacity="0.3"/>
            <circle cx="160" cy="70" r="5" fill="#69c0ff" opacity="0.4"/>
            <circle cx="130" cy="90" r="6" fill="#4096ff" opacity="0.2"/>
            <!-- 文档图标 -->
            <rect x="135" y="30" width="20" height="25" rx="2" fill="none" stroke="#4096ff" stroke-width="2" opacity="0.5"/>
            <line x1="140" y1="38" x2="150" y2="38" stroke="#4096ff" stroke-width="1.5" opacity="0.5"/>
            <line x1="140" y1="43" x2="150" y2="43" stroke="#4096ff" stroke-width="1.5" opacity="0.5"/>
            <line x1="140" y1="48" x2="147" y2="48" stroke="#4096ff" stroke-width="1.5" opacity="0.5"/>
          </svg>
        </div>
      </transition>
      
      <a-input
        v-model:value="searchQuery"
        placeholder="搜索面试题..."
        size="large"
        allow-clear
        @keyup.enter="handleSearch"
        class="search-input"
      >
        <template #prefix>
          <SearchOutlined />
        </template>
        <template #suffix>
          <a-button type="primary" @click="handleSearch" :loading="searching">
            搜索
          </a-button>
        </template>
      </a-input>
    </div>

    <!-- 搜索结果 -->
    <div v-if="searchResults.length > 0" class="results-container">
      <a-list
        item-layout="vertical"
        :data-source="searchResults"
        :pagination="{
          pageSize: 5,
          showSizeChanger: false,
          showTotal: (total) => `共 ${total} 条结果`
        }"
      >
        <template #renderItem="{ item }">
          <a-list-item>
            <a-card hoverable class="result-card">
              <template #title>
                <div class="card-header">
                  <span class="question-title">{{ item.title }}</span>
                  <a-space>
                    <a-tag color="blue">{{ item.difficulty || 'medium' }}</a-tag>
                    <a-tag v-if="item.category" color="green">{{ item.category }}</a-tag>
                    <a-tag v-for="tag in (item.tags || [])" :key="tag" color="purple">
                      {{ tag }}
                    </a-tag>
                  </a-space>
                </div>
              </template>
              
              <MarkdownRenderer :content="item.answer" />
              
              <a-divider style="margin: 12px 0;" />
              
              <div class="source-info">
                <strong>来源:</strong> 
                <a :href="item.source_url" target="_blank">
                  {{ item.source_url }}
                </a>
              </div>
            </a-card>
          </a-list-item>
        </template>
      </a-list>
    </div>

    <!-- 空状态提示 -->
    <a-empty 
      v-else-if="hasSearched" 
      description="没有找到相关的面试题，请尝试其他关键词" 
      class="empty-state"
    />

    <!-- 页脚统计信息 -->
    <div class="footer">
      <a-space split="|">
        <span>面试题总数: <strong>{{ questionCount }}</strong></span>
        <span v-if="lastCrawlTime">上次更新: {{ lastCrawlTime }}</span>
      </a-space>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { questionApi, crawlerApi } from '../services'
import { message } from 'ant-design-vue'
import { SearchOutlined } from '@ant-design/icons-vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'

const questionCount = ref(0)
const lastCrawlTime = ref('')

// 搜索相关
const searchQuery = ref('')
const searching = ref(false)
const searchResults = ref([])
const hasSearched = ref(false)

// 加载统计数据
const loadStats = async () => {
  try {
    // 获取面试题总数
    const countRes = await questionApi.getQuestionCount()
    questionCount.value = countRes.count || 0

    // 获取爬虫状态
    const statusRes = await crawlerApi.getCrawlStatus()
    if (statusRes.last_crawl) {
      lastCrawlTime.value = statusRes.last_crawl.timestamp
    }
  } catch (error) {
    console.error('加载统计数据失败', error)
  }
}

// 处理搜索
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    return
  }

  searching.value = true
  hasSearched.value = true
  searchResults.value = []

  try {
    const res = await questionApi.searchQuestions(searchQuery.value, 10)
    
    searchResults.value = res.results || []
    
    if (searchResults.value.length === 0) {
      message.info('没有找到相关的面试题')
    }
  } catch (error) {
    message.error('搜索失败')
    console.error(error)
  } finally {
    searching.value = false
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.home-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  height: calc(100vh - 64px - 48px);
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.search-container {
  flex-shrink: 0;
  margin-bottom: 24px;
  padding: 0 8px;
  width: 100%;
  text-align: center;
}

.results-container {
  flex: 1;
  overflow-y: auto;
  margin-top: 0;
  width: 100%;
  padding-right: 8px;
}

/* 自定义滚动条样式 */
.results-container::-webkit-scrollbar {
  width: 6px;
}

.results-container::-webkit-scrollbar-track {
  background: transparent;
}

.results-container::-webkit-scrollbar-thumb {
  background: #d9d9d9;
  border-radius: 3px;
  transition: background 0.2s;
}

.results-container::-webkit-scrollbar-thumb:hover {
  background: #bfbfbf;
}

.hero-image {
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
}

.hero-image svg {
  width: 160px;
  height: 100px;
}

/* 淡入淡出动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.search-input :deep(.ant-input-affix-wrapper) {
  padding: 0 11px;
  border-radius: 8px;
  width: 100%;
}

.search-input :deep(.ant-input) {
  font-size: 15px;
}

.search-input :deep(.ant-input-suffix) {
  right: 0;
}

.search-input :deep(.ant-btn-primary) {
  border-radius: 6px;
  height: 32px;
  padding: 0 20px;
  font-size: 14px;
  margin: 0;
}

.results-container {
  margin-top: 24px;
  width: 100%;
}

.results-container :deep(.ant-list) {
  padding: 0;
}

.results-container :deep(.ant-list-item) {
  padding: 0;
}

.footer {
  margin-top: 24px;
  padding: 16px 0;
  text-align: center;
  color: #8c8c8c;
  font-size: 14px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
}
</style>
