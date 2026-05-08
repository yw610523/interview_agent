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
}
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

/* 确保下拉菜单不被遮挡 */
:deep(.ant-select-dropdown) {
  z-index: 9999 !important;
}
</style>
