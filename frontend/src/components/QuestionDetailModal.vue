<template>
  <a-modal
    v-model:open="visible"
    :title="question ? `问题 ${index + 1}: ${question.title}` : ''"
    :footer="null"
    :width="modalWidth"
    :style="isFullscreen ? { maxWidth: '100%', top: 0, padding: 0, margin: 0 } : {}"
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
          <!-- 移动端默认全屏，不显示全屏切换按钮 -->
          <a-tooltip v-if="!isMobile()" :title="isFullscreen ? '退出全屏' : '全屏'">
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
          <a-descriptions-item label="重要性评分">
            <a-slider 
              v-model:value="question.importance_score" 
              :min="0" 
              :max="1" 
              :step="0.05"
              :marks="{0: '0%', 0.25: '25%', 0.5: '50%', 0.75: '75%', 1: '100%'}"
              @change="handleImportanceChange"
              :disabled="submittingFeedback"
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
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { CloseOutlined, FullscreenOutlined, FullscreenExitOutlined } from '@ant-design/icons-vue'
import MarkdownRenderer from './MarkdownRenderer.vue'
import { feedbackApi } from '../services'
import { message, Modal } from 'ant-design-vue'

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
  hideFromRecommendation: false
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
        hideFromRecommendation: res.feedback.hide_from_recommendation || false
      }
    } else {
      // 重置为默认值
      feedbackData.value = {
        masteryLevel: 0,
        isFavorite: false,
        isWrongBook: false,
        hideFromRecommendation: false
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
  
  // 动态设置宽度和高度
  if (isFullscreen.value) {
    modalWidth.value = '100%'
    modalMaxHeight.value = 'calc(100vh - 120px)'
  } else {
    modalWidth.value = isMobile() ? '100%' : 800
    modalMaxHeight.value = isMobile() ? 'calc(100vh - 110px)' : '70vh'
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
    const res = await feedbackApi.submitFeedback(props.question.id, {
      masteryLevel: value
    })
    
    // 检查是否需要弹窗确认
    if (res.auto_hide && res.auto_hide.need_confirm) {
      // 需要用户确认
      Modal.confirm({
        title: '题目已掌握',
        content: `该题重要性为${Math.round(res.question_importance * 100)}%，已达到${getMasteryText(value)}水平。是否将其从推荐中隐藏？`,
        okText: '隐藏（30天后可恢复）',
        cancelText: '继续显示',
        onOk: async () => {
          await feedbackApi.submitFeedback(props.question.id, {
            hideFromRecommendation: true
          })
          message.success('题目已隐藏')
          await loadFeedback()
          // 通知父组件刷新（使用 hidden 类型表示题目被隐藏）
          emit('feedback-changed', {
            questionId: props.question.id,
            type: 'hidden',
            value: true
          })
        },
        onCancel: () => {
          message.info('题目将继续出现在推荐中')
        }
      })
    } else if (res.auto_hide && res.auto_hide.should_hide) {
      // 自动软删除
      message.success(`题目已自动隐藏（重要性${Math.round(res.question_importance * 100)}%，${getMasteryText(value)}）`)
      await loadFeedback()
      // 通知父组件刷新（传递掌握程度）
      emit('feedback-changed', {
        questionId: props.question.id,
        type: 'mastery',
        value: value
      })
    } else {
      // 普通更新
      message.success('掌握程度已更新')
      await loadFeedback()
      // 通知父组件刷新（传递掌握程度）
      emit('feedback-changed', {
        questionId: props.question.id,
        type: 'mastery',
        value: value
      })
    }
  } catch (error) {
    message.error('更新失败')
    console.error(error)
  } finally {
    submittingFeedback.value = false
  }
}

// 处理重要性变化
let importanceTimer = null
const handleImportanceChange = async (value) => {
  if (!props.question?.id) return
  
  // 防抖：延迟500ms后提交
  clearTimeout(importanceTimer)
  importanceTimer = setTimeout(async () => {
    submittingFeedback.value = true
    try {
      await feedbackApi.updateImportance(props.question.id, value)
      message.success('重要性已更新')
      // 通知父组件刷新
      emit('feedback-changed', {
        questionId: props.question.id,
        type: 'importance',
        value: value
      })
    } catch (error) {
      message.error('更新失败')
      console.error(error)
    } finally {
      submittingFeedback.value = false
    }
  }, 500)
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

/* 模态框全屏样式 */
:deep(.question-detail-modal.fullscreen) {
  /* 移除 a-modal 默认的宽度限制 */
  max-width: 100vw !important;
  top: 0 !important;
  padding-bottom: 0 !important;
}

:deep(.question-detail-modal.fullscreen .ant-modal) {
  width: 100% !important;
  max-width: 100% !important; /* 覆盖控制台看到的 calc(100vw - 32px) */
  top: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  left: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}

:deep(.question-detail-modal.fullscreen .ant-modal-content) {
  height: 100vh !important;
  border-radius: 0 !important;
  display: flex;
  flex-direction: column;
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
