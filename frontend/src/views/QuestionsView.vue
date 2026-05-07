<template>
  <div class="questions-view">
    <a-row :gutter="[24, 24]">
      <!-- 生成配置 -->
      <a-col :span="24">
        <a-card title="🎲 生成面试题" :bordered="false">
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
                @change="handleDifficultyChange"
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
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>📋 面试题列表 ({{ questions.length }})</span>
              <a-space>
                <a-button size="small" @click="expandAll" v-if="questions.length > 0">
                  展开全部答案
                </a-button>
                <a-button size="small" @click="collapseAll" v-if="questions.length > 0">
                  收起全部答案
                </a-button>
              </a-space>
            </div>
          </template>

          <a-empty v-if="questions.length === 0" description="点击【生成题目】按钮开始生成面试题" />

          <div class="questions-container" v-else>
            <a-collapse v-model:activeKey="activeKeys" accordion>
              <a-collapse-panel 
                v-for="(question, index) in questions" 
                :key="index.toString()"
              >
                <template #header>
                  <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <div style="flex: 1;">
                      <strong style="font-size: 16px;">问题 {{ index + 1 }}: {{ question.title }}</strong>
                    </div>
                    <div style="margin-left: 16px;">
                      <a-tag color="blue">{{ question.difficulty || 'medium' }}</a-tag>
                      <a-tag v-if="question.category" color="green">{{ question.category }}</a-tag>
                      <a-tag v-for="tag in (question.tags || [])" :key="tag" color="purple">
                        {{ tag }}
                      </a-tag>
                    </div>
                  </div>
                </template>

                <div class="answer-content">
                  <MarkdownRenderer :content="question.answer" />
                  
                  <a-divider />
                  
                  <div class="question-meta">
                    <a-space direction="vertical" size="small">
                      <div>
                        <strong>来源:</strong> 
                        <a :href="question.source_url" target="_blank">
                          {{ question.source_url }}
                        </a>
                      </div>
                      <div v-if="question.importance_score">
                        <strong>重要性评分:</strong> 
                        <a-progress 
                          :percent="Math.round(question.importance_score * 100)" 
                          :stroke-color="{
                            '0%': '#108ee9',
                            '100%': '#87d068',
                          }"
                          style="width: 200px; display: inline-block; margin-left: 8px;"
                        />
                      </div>
                    </a-space>
                  </div>
                </div>
              </a-collapse-panel>
            </a-collapse>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { questionApi } from '../services'
import { message } from 'ant-design-vue'
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
const activeKeys = ref([])

// 生成面试题
const generateQuestions = async () => {
  generating.value = true
  activeKeys.value = []
  
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

// 难度选择变化处理
const handleDifficultyChange = (value) => {
  console.log('难度选择变化:', value)
  console.log('当前difficulty值:', difficulty.value)
}

// 监听difficulty变化
watch(difficulty, (newVal, oldVal) => {
  console.log('difficulty从', oldVal, '变为', newVal)
})

// 展开所有答案
const expandAll = () => {
  activeKeys.value = questions.value.map((_, index) => index.toString())
}

// 收起所有答案
const collapseAll = () => {
  activeKeys.value = []
}
</script>

<style scoped>
.questions-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
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

.answer-content {
  padding: 8px 0;
}

.question-meta {
  margin-top: 16px;
  font-size: 14px;
  color: #666;
}

.question-meta a {
  word-break: break-all;
}

/* 题目列表容器 - 添加滚动条 */
.questions-container {
  max-height: calc(100vh - 400px);
  overflow-y: auto;
  padding-right: 8px;
  padding-bottom: 20px;
}

/* 自定义滚动条样式 */
.questions-container::-webkit-scrollbar {
  width: 8px;
}

.questions-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.questions-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.questions-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

:deep(.ant-collapse-header) {
  background-color: #fafafa;
}

:deep(.ant-collapse-content-box) {
  background-color: #fff;
}

/* 确保下拉菜单不被遮挡 */
:deep(.ant-select-dropdown) {
  z-index: 9999 !important;
}
</style>
