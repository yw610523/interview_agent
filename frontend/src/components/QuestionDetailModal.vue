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
            <a :href="question.source_url" target="_blank">
              {{ question.source_url }}
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
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { CloseOutlined, FullscreenOutlined, FullscreenExitOutlined } from '@ant-design/icons-vue'
import MarkdownRenderer from './MarkdownRenderer.vue'

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

const emit = defineEmits(['update:modelValue', 'close'])

const visible = ref(false)
const isFullscreen = ref(false)
const modalWidth = ref(800)
const modalMaxHeight = ref('70vh')

// 监听外部传入的 visible
watch(() => props.modelValue, (newVal) => {
  visible.value = newVal
  if (newVal) {
    isFullscreen.value = false
    modalWidth.value = 800
  }
})

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
  isFullscreen.value = !isFullscreen.value
  if (isFullscreen.value) {
    modalWidth.value = window.innerWidth
    modalMaxHeight.value = 'calc(100vh - 110px)'
  } else {
    modalWidth.value = 800
    modalMaxHeight.value = '70vh'
  }
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
</style>
