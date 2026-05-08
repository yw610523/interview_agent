<template>
  <div class="favorites-view">
    <a-row :gutter="[24, 24]">
      <!-- 我的收藏 -->
      <a-col :span="24">
        <a-card title="❤️ 我的收藏" :bordered="false">
          <template #extra>
            <a-tag color="blue">共 {{ favorites.length }} 道题目</a-tag>
          </template>

          <a-empty v-if="favorites.length === 0" description="暂无收藏的题目" />

          <QuestionList
            v-else
            :questions="favorites"
            :pagination="true"
            :page-size="20"
            @item-click="showQuestionDetail"
          />
        </a-card>
      </a-col>

      <!-- 错题本 -->
      <a-col :span="24">
        <a-card title="📝 错题本" :bordered="false">
          <template #extra>
            <a-tag color="red">共 {{ wrongBooks.length }} 道题目</a-tag>
          </template>

          <a-empty v-if="wrongBooks.length === 0" description="暂无错题" />

          <QuestionList
            v-else
            :questions="wrongBooks"
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
import { ref, onMounted } from 'vue'
import { feedbackApi } from '../services'
import { message } from 'ant-design-vue'
import QuestionList from '../components/QuestionList.vue'
import QuestionDetailModal from '../components/QuestionDetailModal.vue'

// 数据
const favorites = ref([])
const wrongBooks = ref([])

// 模态框相关
const detailModalVisible = ref(false)
const currentQuestion = ref(null)
const currentIndex = ref(0)

// 加载收藏列表
const loadFavorites = async () => {
  try {
    const res = await feedbackApi.getFavorites()
    favorites.value = res.questions || []
  } catch (error) {
    message.error('加载收藏列表失败')
    console.error(error)
  }
}

// 加载错题本
const loadWrongBook = async () => {
  try {
    const res = await feedbackApi.getWrongBook()
    wrongBooks.value = res.questions || []
  } catch (error) {
    message.error('加载错题本失败')
    console.error(error)
  }
}

// 显示题目详情
const showQuestionDetail = (index) => {
  // 判断是来自收藏还是错题本
  const allQuestions = [...favorites.value, ...wrongBooks.value]
  currentIndex.value = index
  currentQuestion.value = allQuestions[index]
  detailModalVisible.value = true
}

// 处理反馈变化（收藏/错题本）
const handleFeedbackChanged = async ({ questionId, type, value }) => {
  console.log('反馈变化:', { questionId, type, value })
  
  // 如果取消收藏，从收藏列表中移除
  if (type === 'favorite' && !value) {
    favorites.value = favorites.value.filter(q => q.id !== questionId)
    message.success('已从收藏列表移除')
  }
  
  // 如果从错题本移除，从错题本列表中移除
  if (type === 'wrong_book' && !value) {
    wrongBooks.value = wrongBooks.value.filter(q => q.id !== questionId)
    message.success('已从错题本移除')
  }
  
  // 如果添加到收藏/错题本，需要重新加载列表以获取完整数据
  if ((type === 'favorite' && value) || (type === 'wrong_book' && value)) {
    await Promise.all([
      loadFavorites(),
      loadWrongBook()
    ])
  }
}

// 手动取消收藏（供 QuestionList 使用）
const handleRemoveFromFavorites = async (questionId) => {
  try {
    await feedbackApi.removeFromFavorites(questionId)
    favorites.value = favorites.value.filter(q => q.id !== questionId)
    message.success('已取消收藏')
  } catch (error) {
    message.error('操作失败')
    console.error(error)
  }
}

// 手动从错题本移除（供 QuestionList 使用）
const handleRemoveFromWrongBook = async (questionId) => {
  try {
    await feedbackApi.removeFromWrongBook(questionId)
    wrongBooks.value = wrongBooks.value.filter(q => q.id !== questionId)
    message.success('已从错题本移除')
  } catch (error) {
    message.error('操作失败')
    console.error(error)
  }
}

// 初始化加载
onMounted(() => {
  loadFavorites()
  loadWrongBook()
})
</script>

<style scoped>
.favorites-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  min-height: calc(100vh - 112px);
}

@media (max-width: 768px) {
  .favorites-view {
    padding: 12px;
    min-height: calc(100vh - 100px);
  }
}
</style>
