<template>
  <div class="questions-view">
    <a-row :gutter="[24, 24]">
      <!-- 生成配置 -->
      <a-col :span="24">
        <a-card title="🎯 智能推荐题目" :bordered="false" class="form-card">
          <a-form layout="inline" class="mobile-form">
            <a-form-item label="题目数量">
              <a-input-number 
                v-model:value="questionCount" 
                :min="1" 
                :max="50" 
                style="width: 120px;"
              />
            </a-form-item>

            <a-form-item label="启用 Rerank">
              <a-switch v-model:checked="useRerank" />
            </a-form-item>

            <a-form-item>
              <a-button type="primary" @click="generateQuestions" :loading="generating">
                🎯 获取推荐
              </a-button>
            </a-form-item>
          </a-form>
          <div style="margin-top: 8px; color: #8c8c8c; font-size: 13px;">
            💡 基于您的掌握程度和艾宾浩斯遗忘曲线智能推荐，优先展示未掌握且重要的题目
            <span v-if="useRerank" style="color: #1890ff;"> | 🚀 已启用 Rerank 模型重排序</span>
          </div>
        </a-card>
      </a-col>

      <!-- 题目列表 -->
      <a-col :span="24">
        <a-card :bordered="false">
          <template #title>
            <span>📋 面试题列表 ({{ questions.length }})</span>
          </template>

          <a-empty v-if="questions.length === 0" description="点击【生成题目】按钮开始生成面试题" />

          <QuestionList
            v-else
            :questions="questions"
            :pagination="true"
            :page-size="20"
            @item-click="showQuestionDetail"
          />
        </a-card>
      </a-col>
    </a-row>

    <!-- 题目详情模态框 -->
    <QuestionDetailModal
      v-model="detailModalVisible"
      :question="currentQuestion"
      :index="currentIndex"
      @feedback-changed="handleFeedbackChanged"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { questionApi } from '../services'
import { message } from 'ant-design-vue'
import QuestionList from '../components/QuestionList.vue'
import QuestionDetailModal from '../components/QuestionDetailModal.vue'

// 生成配置
const questionCount = ref(10)
const useRerank = ref(false)  // 是否启用 Rerank

// 状态
const generating = ref(false)
const questions = ref([])

// 模态框相关
const detailModalVisible = ref(false)
const currentQuestion = ref(null)
const currentIndex = ref(0)

// 生成面试题
const generateQuestions = async () => {
  generating.value = true
  
  try {
    // 使用智能推荐 API
    const res = await questionApi.getRecommendedQuestions(
      questionCount.value,
      true,  // 排除已掌握的题目
      useRerank.value  // 是否启用 Rerank
    )
    
    if (res.questions) {
      questions.value = res.questions
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
    generating.value = false
  }
}

// 显示题目详情
const showQuestionDetail = (index) => {
  currentIndex.value = index
  currentQuestion.value = questions.value[index]
  detailModalVisible.value = true
}

// 处理反馈变化（收藏/错题本）
const handleFeedbackChanged = async ({ questionId, type, value }) => {
  console.log('反馈变化:', { questionId, type, value })
  
  // 更新当前列表中的题目数据
  const question = questions.value.find(q => q.id === questionId)
  if (question) {
    if (type === 'favorite') {
      question.is_favorite = value
    } else if (type === 'wrong_book') {
      question.is_wrong_book = value
    }
  }
  
  // 可选：重新获取推荐列表以反映优先级变化
  // await generateQuestions()
}
</script>

<style scoped>
.questions-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  min-height: calc(100vh - 112px); /* 减去 header 和 footer 高度 */
}

@media (max-width: 768px) {
  .questions-view {
    padding: 12px;
    min-height: calc(100vh - 100px);
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
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
  
  /* 移动端按钮优化 */
  .mobile-form :deep(.ant-btn) {
    width: 100%;
    height: 44px; /* 最小触摸目标 */
    font-size: 16px;
  }
  
  /* 移动端表单元素间距 */
  .mobile-form :deep(.ant-form-item-label) {
    padding-bottom: 4px;
  }
}

/* 确保下拉菜单不被遮挡 */
:deep(.ant-select-dropdown) {
  z-index: 9999 !important;
}
</style>
