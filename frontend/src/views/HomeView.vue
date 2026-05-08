<template>
  <div class="home-view">
    <!-- 顶部功能区 -->
    <div class="top-section">
      <!-- 智能推荐配置 -->
      <a-card :bordered="false" class="recommend-card">
        <a-space direction="vertical" style="width: 100%;">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div style="display: flex; align-items: center; gap: 16px;">
              <span style="font-weight: 500;">🎯 智能推荐</span>
              <a-input-number 
                v-model:value="recommendCount" 
                :min="1" 
                :max="50"
                size="small"
                style="width: 100px;"
                addon-before="数量"
              />
              <a-tooltip title="启用 Rerank 模型进行智能重排序">
                <a-switch v-model:checked="useRerank" size="small">
                  <template #checkedChildren>🚀</template>
                  <template #unCheckedChildren>⚡</template>
                </a-switch>
              </a-tooltip>
              <span style="font-size: 12px; color: #8c8c8c;">
                {{ useRerank ? '已启用 Rerank' : '未启用 Rerank' }}
              </span>
            </div>
            <a-button type="primary" @click="loadRecommendedQuestions" :loading="loadingRecommend">
              🎯 获取推荐
            </a-button>
          </div>
          <div style="font-size: 12px; color: #8c8c8c; line-height: 1.5;">
            💡 基于掌握程度和艾宾浩斯遗忘曲线智能推荐，优先展示未掌握且重要的题目
            <span v-if="useRerank" style="color: #1890ff;"> | 🚀 Rerank 模型同时用于搜索重排序</span>
          </div>
        </a-space>
      </a-card>

      <!-- 搜索框 -->
      <div class="search-container">
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
    </div>

    <!-- 题目列表 -->
    <div class="results-container">
      <QuestionList
        :questions="displayQuestions"
        :pagination="true"
        :page-size="10"
        @item-click="showQuestionDetail"
      />
    </div>

    <!-- 空状态提示 -->
    <a-empty 
      v-if="!loadingRecommend && displayQuestions.length === 0 && !hasSearched" 
      description="点击【获取推荐】按钮查看智能推荐的面试题" 
      class="empty-state"
    />
    <a-empty 
      v-else-if="hasSearched && displayQuestions.length === 0" 
      description="没有找到相关的面试题，请尝试其他关键词" 
      class="empty-state"
    />

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
import { ref, onMounted, computed } from 'vue'
import { questionApi, crawlerApi } from '../services'
import { message } from 'ant-design-vue'
import { SearchOutlined } from '@ant-design/icons-vue'
import QuestionList from '../components/QuestionList.vue'
import QuestionDetailModal from '../components/QuestionDetailModal.vue'

const questionCount = ref(0)
const lastCrawlTime = ref('')

// 推荐相关
const recommendCount = ref(10)
const useRerank = ref(false)  // 是否启用 Rerank（同时用于搜索和推荐）
const loadingRecommend = ref(false)
const recommendedQuestions = ref([])

// 搜索相关
const searchQuery = ref('')
const searching = ref(false)
const searchResults = ref([])
const hasSearched = ref(false)
const searchMode = ref('hybrid') // semantic | exact | hybrid
const searchModeOptions = [
  { label: '语义', value: 'semantic' },
  { label: '精确', value: 'exact' },
  { label: '混合', value: 'hybrid' }
]

// 显示的题目列表（搜索结果或推荐结果）
const displayQuestions = computed(() => {
  return hasSearched.value ? searchResults.value : recommendedQuestions.value
})

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

// 加载推荐题目
const loadRecommendedQuestions = async () => {
  loadingRecommend.value = true
  hasSearched.value = false
  
  try {
    const res = await questionApi.getRecommendedQuestions(
      recommendCount.value,
      true,  // 排除已掌握的题目
      useRerank.value  // 是否启用 Rerank
    )
    
    if (res.questions) {
      recommendedQuestions.value = res.questions
      const rerankText = useRerank.value ? '（使用 Rerank 重排序）' : ''
      message.success(`已推荐 ${res.total} 道高优先级题目${rerankText}`)
      
      if (res.total === 0) {
        message.info('所有题目都已掌握，太棒了！')
      }
    }
  } catch (error) {
    message.error('获取推荐题目失败')
    console.error(error)
  } finally {
    loadingRecommend.value = false
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
      searchMode.value, // search_mode
      useRerank.value // use_rerank - 搜索时也使用 Rerank
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
      const rerankText = useRerank.value ? ' + Rerank' : ''
      message.success(`找到 ${searchResults.value.length} 个结果（${modeText[searchMode.value]}搜索${rerankText}）`)
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
  currentQuestion.value = displayQuestions.value[index]
  detailModalVisible.value = true
}

// 处理反馈变化（收藏/错题本）
const handleFeedbackChanged = async ({ questionId, type, value }) => {
  console.log('反馈变化:', { questionId, type, value })
  
  // 更新当前列表中的题目数据
  const updateList = hasSearched.value ? searchResults.value : recommendedQuestions.value
  const question = updateList.find(q => q.id === questionId)
  if (question) {
    if (type === 'favorite') {
      question.is_favorite = value
    } else if (type === 'wrong_book') {
      question.is_wrong_book = value
    }
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

.recommend-card {
  margin-bottom: 12px;
  background: linear-gradient(135deg, #f0f5ff 0%, #e6f4ff 100%);
  border-radius: 8px;
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
