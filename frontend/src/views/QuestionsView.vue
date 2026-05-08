<template>
  <div class="questions-view">
    <a-row :gutter="[24, 24]">
      <!-- 生成配置 -->
      <a-col :span="24">
        <a-card title="🎯 生成面试题" :bordered="false" class="form-card">
          <a-form layout="inline" class="mobile-form">
            <a-form-item label="题目数量">
              <a-input-number 
                v-model:value="questionCount" 
                :min="1" 
                :max="50" 
                style="width: 120px;"
              />
            </a-form-item>

            <a-form-item label="难度">
              <a-select 
                v-model:value="difficulty" 
                placeholder="全部"
                style="width: 120px;"
                allow-clear
                :options="difficultyOptions"
              />
            </a-form-item>

            <a-form-item label="分类">
              <a-input 
                v-model:value="category" 
                placeholder="例如: Python"
                style="width: 150px;"
              />
            </a-form-item>

            <a-form-item label="标签">
              <a-select
                v-model:value="tags"
                mode="tags"
                placeholder="输入标签"
                style="width: 200px;"
              />
            </a-form-item>

            <a-form-item>
              <a-button type="primary" @click="generateQuestions" :loading="generating">
                🎯 生成题目
              </a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>

      <!-- 题目列表 -->
      <a-col :span="24">
        <a-card :bordered="false">
          <template #title>
            <span>📋 面试题列表 ({{ questions.length }})</span>
          </template>

          <a-empty v-if="questions.length === 0" description="点击【生成题目】按钮开始生成面试题" />

          <div v-else class="questions-list">
            <a-list
              :data-source="questions"
              :pagination="{
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 道题目`
              }"
            >
              <template #renderItem="{ item, index }">
                <a-list-item class="question-item" @click="showQuestionDetail(index)">
                  <a-list-item-meta>
                    <template #title>
                      <div class="question-title">{{ item.title }}</div>
                    </template>
                    <template #description>
                      <div class="question-tags">
                        <a-tag color="blue">{{ item.difficulty || 'medium' }}</a-tag>
                        <a-tag v-if="item.category" color="green">{{ item.category }}</a-tag>
                        <a-tag v-for="tag in (item.tags || [])" :key="tag" color="purple">
                          {{ tag }}
                        </a-tag>
                      </div>
                    </template>
                  </a-list-item-meta>
                  <template #actions>
                    <a-button type="link" size="small">查看详情 →</a-button>
                  </template>
                </a-list-item>
              </template>
            </a-list>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 题目详情模态框 -->
    <a-modal
      v-model:open="detailModalVisible"
      :title="currentQuestion ? `问题 ${currentIndex + 1}: ${currentQuestion.title}` : ''"
      :footer="null"
      :width="modalWidth"
      :body-style="{ padding: '24px', maxHeight: modalMaxHeight, overflowY: 'auto' }"
      :class="['question-detail-modal', { 'fullscreen': isFullscreen }]"
      @cancel="closeModal"
      wrap-class-name="draggable-modal"
      v-draggable
    >
      <template #closeIcon>
        <a-button type="text" size="small" @click="closeModal">
          <template #icon><CloseOutlined /></template>
        </a-button>
      </template>

      <template #title>
        <div class="modal-header">
          <span class="modal-title">
            问题 {{ currentIndex + 1 }}: {{ currentQuestion?.title }}
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
              <a-button type="text" size="small" @click="closeModal">
                <template #icon><CloseOutlined /></template>
              </a-button>
            </a-tooltip>
          </div>
        </div>
      </template>

      <div v-if="currentQuestion" class="question-detail-content" ref="modalContentRef">
        <div class="answer-section">
          <h4>答案</h4>
          <MarkdownRenderer :content="currentQuestion.answer" />
        </div>
        
        <a-divider />
        
        <div class="meta-section">
          <a-descriptions bordered :column="1" size="small">
            <a-descriptions-item label="难度">
              <a-tag color="blue">{{ currentQuestion.difficulty || 'medium' }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item v-if="currentQuestion.category" label="分类">
              <a-tag color="green">{{ currentQuestion.category }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item v-if="currentQuestion.tags && currentQuestion.tags.length > 0" label="标签">
              <a-tag v-for="tag in currentQuestion.tags" :key="tag" color="purple">
                {{ tag }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item v-if="currentQuestion.source_url" label="来源">
              <a :href="currentQuestion.source_url" target="_blank">
                {{ currentQuestion.source_url }}
              </a>
            </a-descriptions-item>
            <a-descriptions-item v-if="currentQuestion.importance_score" label="重要性评分">
              <a-progress 
                :percent="Math.round(currentQuestion.importance_score * 100)" 
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
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { questionApi } from '../services'
import { message } from 'ant-design-vue'
import { CloseOutlined, FullscreenOutlined, FullscreenExitOutlined } from '@ant-design/icons-vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'

// 生成配置
const questionCount = ref(10)
const difficulty = ref(undefined)
const category = ref('')
const tags = ref([])

// 难度选项
const difficultyOptions = [
  { value: 'easy', label: '简单' },
  { value: 'medium', label: '中等' },
  { value: 'hard', label: '困难' }
]

// 状态
const generating = ref(false)
const questions = ref([])

// 模态框相关
const detailModalVisible = ref(false)
const currentQuestion = ref(null)
const currentIndex = ref(0)
const isFullscreen = ref(false)
const modalWidth = ref(800)
const modalMaxHeight = ref('70vh')

// 生成面试题
const generateQuestions = async () => {
  generating.value = true
  
  try {
    const res = await questionApi.generateBatch(
      questionCount.value,
      difficulty.value,
      category.value || null,
      tags.value.length > 0 ? tags.value : null
    )
    
    if (res.status === 'success') {
      questions.value = res.questions
      message.success(`成功生成 ${res.count} 道面试题`)
      
      if (res.count === 0) {
        message.warning('没有找到符合条件的题目，请调整筛选条件')
      }
    }
  } catch (error) {
    message.error('生成面试题失败')
    console.error(error)
  } finally {
    generating.value = false
  }
}

// 显示题目详情
const showQuestionDetail = (index) => {
  currentIndex.value = index
  currentQuestion.value = questions.value[index]
  detailModalVisible.value = true
  isFullscreen.value = false
  modalWidth.value = 800
}

// 关闭模态框
const closeModal = () => {
  detailModalVisible.value = false
  currentQuestion.value = null
  isFullscreen.value = false
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

// ESC 键关闭模态框
const handleEscKey = (e) => {
  if (e.key === 'Escape' && detailModalVisible.value) {
    closeModal()
  }
}

// 生命周期钩子
onMounted(() => {
  document.addEventListener('keydown', handleEscKey)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscKey)
})
</script>

<style scoped>
.questions-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

@media (max-width: 768px) {
  .questions-view {
    padding: 8px;
  }
  
  .mobile-form {
    flex-direction: column;
    align-items: stretch;
  }
  
  .mobile-form :deep(.ant-form-item) {
    margin-bottom: 12px;
    width: 100%;
  }
  
  .mobile-form :deep(.ant-form-item-control) {
    width: 100%;
  }
  
  .mobile-form :deep(.ant-input-number),
  .mobile-form :deep(.ant-select),
  .mobile-form :deep(.ant-input) {
    width: 100% !important;
  }
}

/* 题目列表样式 */
.questions-list {
  min-height: 200px;
}

.question-item {
  cursor: pointer;
  transition: all 0.3s;
  border-bottom: 1px solid #f0f0f0;
  padding: 12px 16px;
}

.question-item:hover {
  background-color: #fafafa;
  transform: translateX(4px);
}

.question-title {
  font-size: 15px;
  font-weight: 500;
  color: #262626;
  margin-bottom: 8px;
}

.question-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 模态框样式 */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.modal-title {
  font-size: 16px;
  font-weight: 500;
  flex: 1;
  margin-right: 16px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.modal-actions {
  display: flex;
  gap: 8px;
}

.question-detail-content {
  padding: 8px 0;
}

.answer-section h4 {
  margin-bottom: 16px;
  color: #262626;
  font-size: 16px;
}

.meta-section {
  margin-top: 16px;
}

/* 确保下拉菜单不被遮挡 */
:deep(.ant-select-dropdown) {
  z-index: 9999 !important;
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

/* 可拖拽模态框 */
:deep(.draggable-modal .ant-modal) {
  cursor: move;
}

:deep(.draggable-modal .ant-modal-header) {
  cursor: move;
  user-select: none;
}

:deep(.draggable-modal .ant-modal-body) {
  cursor: default;
}
</style>
