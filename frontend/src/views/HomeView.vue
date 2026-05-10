<template>
  <div class="home-view">
    <!-- 顶部搜索区 -->
    <div class="top-section">
      <!-- 搜索框 -->
      <div class="search-container">
        <a-input
          v-model:value="searchQuery"
          :placeholder="!hasSearched ? '输入关键词搜索面试题（留空查看推荐）' : '搜索面试题...'"
          size="large"
          allow-clear
          @keyup.enter="handleSearchOrRecommend"
          class="search-input"
        >
          <template #suffix>
            <a-button type="primary" @click="handleSearchOrRecommend" :loading="loading">
              搜索
            </a-button>
          </template>
        </a-input>
      </div>
    </div>

    <!-- 题目列表 -->
    <div class="results-container">
      <QuestionList
        :questions="displayQuestions"
        :pagination="false"
        :show-not-question="true"
        @item-click="showQuestionDetail"
        @not-question="handleNotQuestion"
      />
    </div>

    <!-- 分页组件（放在列表下方） -->
    <div v-if="hasSearched && searchResults.length > 10" class="pagination-container">
      <a-pagination
        v-model:current="currentPage"
        :total="searchResults.length"
        :page-size="10"
        show-size-changer
        :show-total="(total) => `共 ${total} 条结果`"
        @change="handlePageChange"
      />
    </div>

    <!-- 题目详情模态框 -->
    <QuestionDetailModal
      v-model="detailModalVisible"
      :question="currentQuestion"
      :index="currentIndex"
      @feedback-changed="handleFeedbackChanged"
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
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { questionApi, crawlerApi } from '../services'
import { message } from 'ant-design-vue'
import QuestionList from '../components/QuestionList.vue'
import QuestionDetailModal from '../components/QuestionDetailModal.vue'

const questionCount = ref(0)
const lastCrawlTime = ref('')

// 搜索相关
const searchQuery = ref('')
const loading = ref(false)
const searchResults = ref([])
const hasSearched = ref(false)
const currentPage = ref(1)
const pageSize = 10

// 分页后的显示数据
const displayQuestions = computed(() => {
  if (!hasSearched.value) {
    return recommendedQuestions.value
  }
  // 搜索模式：根据当前页切片
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return searchResults.value.slice(start, end)
})

// 显示的全局索引偏移（保留用于其他可能用途）
const currentIndexOffset = computed(() => {
  return hasSearched.value ? (currentPage.value - 1) * pageSize : 0
})

// 推荐相关
const recommendedQuestions = ref([])

// 模态框相关
const detailModalVisible = ref(false)
const currentQuestion = ref(null)
const currentIndex = ref(0)

// 键盘导航
const handleKeydown = (e) => {
  // 只在模态框打开时响应
  if (!detailModalVisible.value) return
  
  // 如果用户在输入框中，不拦截按键
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
  
  const list = displayQuestions.value
  if (list.length === 0) return
  
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    // 上一题
    const newIndex = (currentIndex.value - 1 + list.length) % list.length
    currentIndex.value = newIndex
    currentQuestion.value = list[newIndex]
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    // 下一题
    const newIndex = (currentIndex.value + 1) % list.length
    currentIndex.value = newIndex
    currentQuestion.value = list[newIndex]
  }
}

// 监听模态框状态变化，动态添加/移除键盘事件
watch(detailModalVisible, (visible) => {
  if (visible) {
    window.addEventListener('keydown', handleKeydown)
  } else {
    window.removeEventListener('keydown', handleKeydown)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

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

// 加载推荐题目（最多10条）
const loadRecommendedQuestions = async () => {
  loading.value = true
  hasSearched.value = false
  
  try {
    const res = await questionApi.getRecommendedQuestions(
      10,  // 固定返回10条
      true,  // 排除已掌握的题目
      true   // 自动启用 Rerank（后端会自动降级）
    )
    
    if (res.questions) {
      recommendedQuestions.value = res.questions
      
      if (res.total === 0) {
        message.info('所有题目都已掌握，太棒了！')
      } else {
        const rerankStatus = res.rerank_used ? '（已使用 Rerank 优化排序）' : ''
        console.log(`推荐了 ${res.total} 道题目${rerankStatus}`)
      }
    }
  } catch (error) {
    message.error('获取推荐题目失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 处理搜索或推荐（根据搜索框是否为空决定）
const handleSearchOrRecommend = async () => {
  // 如果搜索框为空，切换到推荐模式
  if (!searchQuery.value.trim()) {
    await loadRecommendedQuestions()
    return
  }

  // 否则执行搜索
  loading.value = true
  hasSearched.value = true
  searchResults.value = []
  currentPage.value = 1 // 重置页码

  try {
    const res = await questionApi.searchQuestions(
      searchQuery.value,
      100,  // 不限制数量，搜到多少是多少
      undefined, // tags
      undefined, // difficulty
      undefined, // category
      'hybrid', // 固定使用混合搜索
      true // 自动启用 Rerank（后端会自动降级）
    )
    
    searchResults.value = res.results || []
    
    if (searchResults.value.length === 0) {
      message.info('没有找到相关的面试题')
    } else {
      message.success(`找到 ${searchResults.value.length} 个结果`)
    }
  } catch (error) {
    message.error('搜索失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 处理页码变化
const handlePageChange = (page) => {
  currentPage.value = page
}

// 显示题目详情（直接使用当前页的数据）
const showQuestionDetail = (pageIndex) => {
  currentIndex.value = pageIndex
  currentQuestion.value = displayQuestions.value[pageIndex]
  detailModalVisible.value = true
}

// 处理反馈变化（收藏/错题本）
const handleFeedbackChanged = async ({ questionId, type, value }) => {
  console.log('反馈变化:', { questionId, type, value })
  
  // 在全部搜索结果中查找并更新
  const question = searchResults.value.find(q => q.id === questionId)
  if (question) {
    if (type === 'favorite') {
      question.is_favorite = value
    } else if (type === 'wrong_book') {
      question.is_wrong_book = value
    }
  }
}

// 处理“非问题”标记（永久删除）
const handleNotQuestion = async (questionId) => {
  try {
    await questionApi.permanentlyDeleteQuestion(questionId)
    message.success('题目已永久删除')
    
    // 从当前列表中移除
    if (hasSearched.value) {
      // 搜索模式：从 searchResults 中移除
      searchResults.value = searchResults.value.filter(q => q.id !== questionId)
    } else {
      // 推荐模式：从 recommendedQuestions 中移除
      recommendedQuestions.value = recommendedQuestions.value.filter(q => q.id !== questionId)
    }
  } catch (error) {
    message.error('删除失败')
    console.error(error)
  }
}

onMounted(() => {
  loadStats()
  // 页面加载时自动获取推荐题目
  loadRecommendedQuestions()
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
}

.top-section {
  flex-shrink: 0;
  margin-bottom: 16px;
  width: 100%;
}

.search-container {
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

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
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
  margin-top: 16px;
  padding: 16px 0;
  text-align: center;
  color: #8c8c8c;
  font-size: 14px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
}
</style>
