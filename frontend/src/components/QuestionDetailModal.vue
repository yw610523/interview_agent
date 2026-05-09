<template>
  <a-modal
    v-model:open="visible"
    :title="question ? `问题 ${index + 1}: ${question.title}` : ''"
    :footer="null"
    :width="modalWidth"
    :body-style="{ padding: '24px', maxHeight: modalMaxHeight, overflowY: 'auto' }"
    :class="['question-detail-modal', { 'fullscreen': isFullscreen }]"
    @cancel="handleClose"
  >
    <template #closeIcon>
      <a-button type="text" size="small" @click="handleClose">
        <template #icon><CloseOutlined /></template>
      </a-button>
    </template>

    <template #title>
      <div class="modal-header">
        <span class="modal-title">
          问题 {{ index + 1 }}: {{ question?.title }}
        </span>
        <div class="modal-actions">
          <a-tooltip :title="isFullscreen ? '退出全屏' : '全屏'">
            <a-button type="text" size="small" @click="toggleFullscreen">
              <template #icon>
                <FullscreenExitOutlined v-if="isFullscreen" />
                <FullscreenOutlined v-else />
              </template>
            </a-button>
          </a-tooltip>
          <a-tooltip title="关闭">
            <a-button type="text" size="small" @click="handleClose">
              <template #icon><CloseOutlined /></template>
            </a-button>
          </a-tooltip>
        </div>
      </div>
    </template>

    <div v-if="question" class="question-detail-content">
      <div class="answer-section">
        <h4>答案</h4>
        <MarkdownRenderer :content="question.answer" />
      </div>
      
      <a-divider />
      
      <div class="meta-section">
        <a-descriptions bordered :column="1" size="small">
          <a-descriptions-item label="难度">
            <a-tag color="blue">{{ question.difficulty || 'medium' }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item v-if="question.category" label="分类">
            <a-tag color="green">{{ question.category }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item v-if="question.tags && question.tags.length > 0" label="标签">
            <a-tag v-for="tag in question.tags" :key="tag" color="purple">
              {{ tag }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item v-if="question.source_url" label="来源">
            <a :href="question.source_url" target="_blank" rel="noopener noreferrer">
              🔗 查看来源
            </a>
          </a-descriptions-item>
          <a-descriptions-item v-if="question.importance_score" label="重要性评分">
            <a-progress 
              :percent="Math.round(question.importance_score * 100)" 
              :stroke-color="{
                '0%': '#108ee9',
                '100%': '#87d068',
              }"
              style="width: 200px;"
            />
          </a-descriptions-item>
        </a-descriptions>
      </div>

      <!-- 用户反馈区域 -->
      <a-divider />
      <div class="feedback-section">
        <h4>📊 学习反馈</h4>
        
        <!-- 掌握程度评分 -->
        <div class="feedback-item">
          <span class="feedback-label">掌握程度：</span>
          <a-rate 
            v-model:value="feedbackData.masteryLevel" 
            :count="5"
            @change="handleMasteryChange"
            :disabled="submittingFeedback"
          />
          <span class="feedback-hint">（{{ getMasteryText(feedbackData.masteryLevel) }}）</span>
        </div>

        <!-- 收藏和错题本按钮 -->
        <div class="feedback-actions">
          <a-button 
            :type="feedbackData.isFavorite ? 'primary' : 'default'"
            :icon="feedbackData.isFavorite ? '❤️' : '🤍'"
            @click="toggleFavorite"
            :loading="submittingFeedback"
          >
            {{ feedbackData.isFavorite ? '已收藏' : '收藏' }}
          </a-button>
          
          <a-button 
            :type="feedbackData.isWrongBook ? 'danger' : 'default'"
            :icon="feedbackData.isWrongBook ? '❌' : '📝'"
            @click="toggleWrongBook"
            :loading="submittingFeedback"
          >
            {{ feedbackData.isWrongBook ? '已在错题本' : '加入错题本' }}
          </a-button>
        </div>

        <!-- 复习信息 -->
        <div v-if="feedbackData.reviewCount > 0" class="review-info">
          <a-alert
            type="info"
            show-icon
            :message="`已复习 ${feedbackData.reviewCount} 次`"
            :description="getNextReviewText()"
          />
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { CloseOutlined, FullscreenOutlined, FullscreenExitOutlined } from '@ant-design/icons-vue'
import MarkdownRenderer from './MarkdownRenderer.vue'
import { feedbackApi } from '../services'
import { message } from 'ant-design-vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  question: {
    type: Object,
    default: null
  },
  index: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:modelValue', 'close', 'feedback-changed'])

const visible = ref(false)
const isFullscreen = ref(false) // 默认不全屏
const modalWidth = ref(800) // 默认电脑端宽度
const modalMaxHeight = ref('70vh') // 默认电脑端高度

// 检测是否为移动端
const isMobile = () => {
  return window.innerWidth <= 768
}

// 滚动位置记忆（按题目 ID 存储）
const scrollPositions = new Map()
let currentScrollTop = 0

// 获取滚动容器
const getScrollContainer = () => {
  return document.querySelector('.question-detail-modal .ant-modal-body')
}

// 反馈数据
const feedbackData = ref({
  masteryLevel: 0,
  isFavorite: false,
  isWrongBook: false,
  reviewCount: 0,
  nextReviewAt: null
})
const submittingFeedback = ref(false)

// 监听外部传入的 visible
watch(() => props.modelValue, (newVal) => {
  visible.value = newVal
  if (newVal) {
    // 根据设备类型设置默认状态
    if (isMobile()) {
      isFullscreen.value = true
      modalWidth.value = '100vw'
      modalMaxHeight.value = 'calc(100vh - 110px)'
    } else {
      isFullscreen.value = false
      modalWidth.value = 800
      modalMaxHeight.value = '70vh'
    }
    // 加载反馈数据
    loadFeedback()
    // 恢复滚动位置
    restoreScrollPosition()
  } else {
    // 关闭时保存当前滚动位置
    saveScrollPosition()
  }
})

// 监听题目切换，保存旧的滚动位置并恢复新的
watch(() => props.question?.id, async (newId, oldId) => {
  // 保存旧题目的滚动位置
  if (oldId) {
    const container = getScrollContainer()
    if (container) {
      scrollPositions.set(oldId, container.scrollTop)
    }
  }
  
  // 恢复新题目的滚动位置
  if (newId) {
    await nextTick()
    restoreScrollPosition()
  }
})

// 保存滚动位置
const saveScrollPosition = () => {
  const container = getScrollContainer()
  if (container && props.question?.id) {
    scrollPositions.set(props.question.id, container.scrollTop)
  }
}

// 恢复滚动位置
const restoreScrollPosition = () => {
  const container = getScrollContainer()
  if (container && props.question?.id) {
    const savedPosition = scrollPositions.get(props.question.id) || 0
    container.scrollTop = savedPosition
  }
}

// 加载反馈数据
const loadFeedback = async () => {
  if (!props.question?.id) return
  
  try {
    const res = await feedbackApi.getFeedback(props.question.id)
    if (res.has_feedback && res.feedback) {
      feedbackData.value = {
        masteryLevel: res.feedback.mastery_level,
        isFavorite: res.feedback.is_favorite,
        isWrongBook: res.feedback.is_wrong_book,
        reviewCount: res.feedback.review_count,
        nextReviewAt: res.feedback.next_review_at
      }
    } else {
      // 重置为默认值
      feedbackData.value = {
        masteryLevel: 0,
        isFavorite: false,
        isWrongBook: false,
        reviewCount: 0,
        nextReviewAt: null
      }
    }
  } catch (error) {
    console.error('加载反馈数据失败:', error)
  }
}

// 监听内部 visible 变化
watch(visible, (newVal) => {
  emit('update:modelValue', newVal)
})

// 关闭模态框
const handleClose = () => {
  visible.value = false
  emit('close')
}

// 切换全屏
const toggleFullscreen = () => {
  // 切换前保存当前位置
  saveScrollPosition()
  
  isFullscreen.value = !isFullscreen.value
  if (isFullscreen.value) {
    modalWidth.value = '100vw'
    modalMaxHeight.value = 'calc(100vh - 110px)'
  } else {
    modalWidth.value = 800
    modalMaxHeight.value = '70vh'
  }
  
  // 切换后恢复位置
  nextTick(() => {
    restoreScrollPosition()
  })
}

// ESC 键关闭模态框，Ctrl+Enter 切换全屏
const handleKeyDown = (e) => {
  if (!visible.value) return
  
  // ESC 关闭
  if (e.key === 'Escape') {
    handleClose()
  }
  // Ctrl+Enter 切换全屏
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault()
    toggleFullscreen()
  }
}

// 获取掌握程度文本
const getMasteryText = (level) => {
  const texts = ['未学习', '了解概念', '基本掌握', '熟练运用', '深入理解', '完全掌握']
  return texts[level] || '未学习'
}

// 处理掌握程度变化
const handleMasteryChange = async (value) => {
  if (!props.question?.id) return
  
  // 防止重复提交
  if (submittingFeedback.value) {
    console.log('正在提交中，忽略本次操作')
    return
  }
  
  submittingFeedback.value = true
  try {
    await feedbackApi.submitFeedback(props.question.id, {
      masteryLevel: value
    })
    message.success('掌握程度已更新')
    // 重新加载反馈数据以获取最新的 review_count
    await loadFeedback()
  } catch (error) {
    message.error('更新失败')
    console.error(error)
  } finally {
    submittingFeedback.value = false
  }
}

// 切换收藏状态
const toggleFavorite = async () => {
  if (!props.question?.id) return
  
  submittingFeedback.value = true
  try {
    const newStatus = !feedbackData.value.isFavorite
    await feedbackApi.submitFeedback(props.question.id, {
      isFavorite: newStatus
    })
    feedbackData.value.isFavorite = newStatus
    message.success(newStatus ? '已加入收藏' : '已取消收藏')
    // 通知父组件刷新
    emit('feedback-changed', {
      questionId: props.question.id,
      type: 'favorite',
      value: newStatus
    })
  } catch (error) {
    message.error('操作失败')
    console.error(error)
  } finally {
    submittingFeedback.value = false
  }
}

// 切换错题本状态
const toggleWrongBook = async () => {
  if (!props.question?.id) return
  
  submittingFeedback.value = true
  try {
    const newStatus = !feedbackData.value.isWrongBook
    await feedbackApi.submitFeedback(props.question.id, {
      isWrongBook: newStatus
    })
    feedbackData.value.isWrongBook = newStatus
    message.success(newStatus ? '已加入错题本' : '已从错题本移除')
    // 通知父组件刷新
    emit('feedback-changed', {
      questionId: props.question.id,
      type: 'wrong_book',
      value: newStatus
    })
  } catch (error) {
    message.error('操作失败')
    console.error(error)
  } finally {
    submittingFeedback.value = false
  }
}

// 获取下次复习时间文本
const getNextReviewText = () => {
  if (!feedbackData.value.nextReviewAt) {
    return '完成评分后将计算下次复习时间'
  }
  
  try {
    const nextReview = new Date(feedbackData.value.nextReviewAt)
    const now = new Date()
    const daysUntil = Math.ceil((nextReview - now) / (1000 * 60 * 60 * 24))
    
    if (daysUntil <= 0) {
      return '今天应该复习这道题！'
    } else if (daysUntil === 1) {
      return '明天应该复习这道题'
    } else {
      return `预计 ${daysUntil} 天后复习`
    }
  } catch (error) {
    return '下次复习时间计算失败'
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-bottom: 16px;
  border-bottom: 2px solid #f0f0f0;
  margin-bottom: 8px;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #1890ff;
  flex: 1;
  margin-right: 16px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.modal-actions {
  display: flex;
  gap: 8px;
}

.question-detail-content {
  padding: 8px 0;
  position: relative;
  min-height: 200px;
}

.answer-section h4 {
  margin-bottom: 16px;
  color: #262626;
  font-size: 17px;
  font-weight: 600;
  padding-left: 12px;
  border-left: 3px solid #1890ff;
}

.meta-section {
  margin-top: 16px;
}

/* 用户反馈区域 */
.feedback-section {
  padding: 8px 0;
}

.feedback-section h4 {
  margin-bottom: 16px;
  color: #262626;
  font-size: 17px;
  font-weight: 600;
  padding-left: 12px;
  border-left: 3px solid #52c41a;
}

.feedback-item {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.feedback-label {
  font-weight: 500;
  color: #595959;
  min-width: 80px;
}

.feedback-hint {
  color: #8c8c8c;
  font-size: 13px;
}

.feedback-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.review-info {
  margin-top: 12px;
}

/* 模态框全屏样式 */
:deep(.question-detail-modal.fullscreen .ant-modal) {
  top: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  left: 0 !important;
  width: 100vw !important;
  max-width: 100vw !important;
  height: 100vh !important;
  margin: 0 !important;
  padding: 0 !important;
}

:deep(.question-detail-modal.fullscreen .ant-modal-content) {
  height: 100vh !important;
  display: flex;
  flex-direction: column;
  border-radius: 0 !important;
}

:deep(.question-detail-modal.fullscreen .ant-modal-body) {
  flex: 1;
  overflow-y: auto !important;
}

/* 移动端适配 */
@media (max-width: 768px) {
  :deep(.ant-modal) {
    top: 0 !important;
    max-width: 100vw !important;
    margin: 0 !important;
  }
  
  :deep(.ant-modal-content) {
    border-radius: 0 !important;
    min-height: 100vh;
  }
}
</style>
