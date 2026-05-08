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
          <div style="display: flex; align-items: center; gap: 8px;">
            <a-segmented
              v-model:value="searchMode"
              :options="searchModeOptions"
              size="small"
              style="margin-right: 8px;"
            />
            <a-button type="primary" @click="handleSearch" :loading="searching">
              搜索
            </a-button>
          </div>
        </template>
      </a-input>
    </div>

    <!-- 搜索结果 -->
    <div v-if="searchResults.length > 0" class="results-container">
      <QuestionList
        :questions="searchResults"
        :pagination="true"
        :page-size="5"
        @item-click="showQuestionDetail"
      />
    </div>

    <!-- 空状态提示 -->
    <a-empty 
      v-else-if="hasSearched" 
      description="没有找到相关的面试题，请尝试其他关键词" 
      class="empty-state"
    />

    <!-- 题目详情模态框 -->
    <QuestionDetailModal
      v-model="detailModalVisible"
      :question="currentQuestion"
      :index="currentIndex"
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
import QuestionList from '../components/QuestionList.vue'
import QuestionDetailModal from '../components/QuestionDetailModal.vue'

const questionCount = ref(0)
const lastCrawlTime = ref('')

// 搜索相关
const searchQuery = ref('')
const searching = ref(false)
const searchResults = ref([])
const hasSearched = ref(false)
const searchMode = ref('semantic') // semantic | exact | hybrid
const searchModeOptions = [
  { label: '语义', value: 'semantic' },
  { label: '精确', value: 'exact' },
  { label: '混合', value: 'hybrid' }
]

// 模态框相关
const detailModalVisible = ref(false)
const currentQuestion = ref(null)
const currentIndex = ref(0)

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
    const res = await questionApi.searchQuestions(
      searchQuery.value,
      10,
      undefined, // tags
      undefined, // difficulty
      undefined, // category
      searchMode.value // search_mode
    )
    
    searchResults.value = res.results || []
    
    if (searchResults.value.length === 0) {
      message.info('没有找到相关的面试题')
    } else {
      const modeText = {
        'semantic': '语义',
        'exact': '精确',
        'hybrid': '混合'
      }
      message.success(`找到 ${searchResults.value.length} 个结果（${modeText[searchMode.value]}搜索）`)
    }
  } catch (error) {
    message.error('搜索失败')
    console.error(error)
  } finally {
    searching.value = false
  }
}

// 显示题目详情
const showQuestionDetail = (index) => {
  currentIndex.value = index
  currentQuestion.value = searchResults.value[index]
  detailModalVisible.value = true
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.home-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
  height: calc(100vh - 64px - 48px);
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

@media (max-width: 768px) {
  .home-view {
    padding: 8px;
    height: calc(100vh - 56px - 40px);
  }
  
  .hero-image svg {
    width: 120px;
    height: 75px;
  }
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
