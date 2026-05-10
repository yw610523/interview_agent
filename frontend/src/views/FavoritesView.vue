<template>
  <div class="favorites-view">
    <a-row :gutter="[24, 24]">
      <!-- 我的收藏 -->
      <a-col :span="24">
        <a-card title="❤️ 我的收藏" :bordered="false" :loading="loadingFavorites">
          <template #extra>
            <a-tag color="blue">共 {{ favorites.length }} 道题目</a-tag>
          </template>

          <a-empty v-if="!loadingFavorites && favorites.length === 0" description="暂无收藏的题目" />

          <QuestionList
            v-else-if="!loadingFavorites"
            :questions="favorites"
            :pagination="true"
            :page-size="20"
            @item-click="(index) => showQuestionDetail(index, 'favorites')"
          />
        </a-card>
      </a-col>

      <!-- 错题本 -->
      <a-col :span="24">
        <a-card title="📝 错题本" :bordered="false" :loading="loadingWrongBooks">
          <template #extra>
            <a-tag color="red">共 {{ wrongBooks.length }} 道题目</a-tag>
          </template>

          <a-empty v-if="!loadingWrongBooks && wrongBooks.length === 0" description="暂无错题" />

          <QuestionList
            v-else-if="!loadingWrongBooks"
            :questions="wrongBooks"
            :pagination="true"
            :page-size="20"
            @item-click="(index) => showQuestionDetail(index, 'wrongBooks')"
          />
        </a-card>
      </a-col>

      <!-- 已掌握（软删除） -->
      <a-col :span="24">
        <a-card title="✅ 已掌握（30天后可恢复）" :bordered="false" :loading="loadingHiddenQuestions">
          <template #extra>
            <div style="display: flex; gap: 8px; align-items: center;">
              <a-tag color="green">共 {{ hiddenQuestions.length }} 道题目</a-tag>
              <a-popconfirm
                v-if="!loadingHiddenQuestions && hiddenQuestions.length > 0"
                title="确认永久删除所有已掌握题目？"
                ok-text="删除"
                cancel-text="取消"
                ok-type="danger"
                @confirm="permanentlyDeleteAllHidden"
              >
                <a-button size="small" danger>
                  清空全部
                </a-button>
              </a-popconfirm>
            </div>
          </template>

          <a-empty v-if="!loadingHiddenQuestions && hiddenQuestions.length === 0" description="暂无已掌握的题目" />

          <QuestionList
            v-else-if="!loadingHiddenQuestions"
            :questions="hiddenQuestions"
            :pagination="true"
            :page-size="20"
            :show-permanent-delete="true"
            :show-restore="true"
            @item-click="(index) => showQuestionDetail(index, 'hidden')"
            @permanent-delete="handlePermanentDelete"
            @restore="handleRestoreQuestion"
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
import { message, Modal } from 'ant-design-vue'
import QuestionList from '../components/QuestionList.vue'
import QuestionDetailModal from '../components/QuestionDetailModal.vue'

// 数据
const favorites = ref([])
const wrongBooks = ref([])
const hiddenQuestions = ref([])

// 加载状态
const loadingFavorites = ref(true)
const loadingWrongBooks = ref(true)
const loadingHiddenQuestions = ref(true)

// 模态框相关
const detailModalVisible = ref(false)
const currentQuestion = ref(null)
const currentIndex = ref(0)

// 加载收藏列表
const loadFavorites = async () => {
  loadingFavorites.value = true
  try {
    const res = await feedbackApi.getFavorites()
    favorites.value = res.questions || []
  } catch (error) {
    message.error('加载收藏列表失败')
    console.error(error)
  } finally {
    loadingFavorites.value = false
  }
}

// 加载错题本
const loadWrongBook = async () => {
  loadingWrongBooks.value = true
  try {
    const res = await feedbackApi.getWrongBook()
    wrongBooks.value = res.questions || []
  } catch (error) {
    message.error('加载错题本失败')
    console.error(error)
  } finally {
    loadingWrongBooks.value = false
  }
}

// 加载已掌握题目
const loadHiddenQuestions = async () => {
  loadingHiddenQuestions.value = true
  try {
    const res = await feedbackApi.getHiddenQuestions()
    hiddenQuestions.value = res.questions || []
  } catch (error) {
    message.error('加载已掌握题目失败')
    console.error(error)
  } finally {
    loadingHiddenQuestions.value = false
  }
}

// 显示题目详情
const showQuestionDetail = (index, listType = 'favorites') => {
  // 根据列表类型获取对应的题目列表
  let questionList = []
  if (listType === 'favorites') {
    questionList = favorites.value
  } else if (listType === 'wrongBooks') {
    questionList = wrongBooks.value
  } else if (listType === 'hidden') {
    questionList = hiddenQuestions.value
  }
  
  currentIndex.value = index
  currentQuestion.value = questionList[index]
  detailModalVisible.value = true
}

// 处理反馈变化（收藏/错题本/掌握程度/隐藏）
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
  
  // 如果题目被隐藏（软删除），需要从所有列表中移除并重新加载
  if (type === 'hidden' && value) {
    console.log('题目已隐藏，刷新列表...')
    await Promise.all([
      loadFavorites(),
      loadWrongBook(),
      loadHiddenQuestions()
    ])
    message.success('题目已隐藏，30天后可恢复')
    return
  }
  
  // 如果掌握程度变为5（已掌握），题目会被软删除，需要从所有列表中移除并重新加载
  if (type === 'mastery' && value === 5) {
    console.log('题目已掌握，刷新列表...')
    await Promise.all([
      loadFavorites(),
      loadWrongBook(),
      loadHiddenQuestions()
    ])
    message.success('题目标记为已掌握，30天后可恢复')
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

// 永久删除题目
const handlePermanentDelete = async (questionId) => {
  try {
    Modal.confirm({
      title: '确认永久删除',
      content: '此操作不可恢复，题目将彻底从数据库中删除',
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await feedbackApi.permanentlyDeleteQuestion(questionId)
          hiddenQuestions.value = hiddenQuestions.value.filter(q => q.id !== questionId)
          message.success('题目已永久删除')
        } catch (error) {
          message.error('删除失败')
          console.error(error)
        }
      }
    })
  } catch (error) {
    message.error('操作失败')
    console.error(error)
  }
}

// 恢夏题目（从软删除状态恢复）
const handleRestoreQuestion = async (questionId) => {
  try {
    Modal.confirm({
      title: '确认恢夏题目',
      content: '该题目将重新出现在推荐列表中',
      okText: '确认恢夏',
      cancelText: '取消',
      onOk: async () => {
        try {
          // 将 hide_from_recommendation 设置为 false
          await feedbackApi.submitFeedback(questionId, {
            hideFromRecommendation: false
          })
          hiddenQuestions.value = hiddenQuestions.value.filter(q => q.id !== questionId)
          message.success('题目已恢夏，将重新出现在推荐中')
          // 重新加载收藏和错题本列表，因为题目可能在其中
          await Promise.all([
            loadFavorites(),
            loadWrongBook()
          ])
        } catch (error) {
          message.error('恢夏失败')
          console.error(error)
        }
      }
    })
  } catch (error) {
    message.error('操作失败')
    console.error(error)
  }
}

// 清空所有已掌握题目
const permanentlyDeleteAllHidden = async () => {
  try {
    // 逐个删除
    for (const q of hiddenQuestions.value) {
      await feedbackApi.permanentlyDeleteQuestion(q.id)
    }
    hiddenQuestions.value = []
    message.success(`已永久删除 ${hiddenQuestions.value.length} 道题目`)
  } catch (error) {
    message.error('清空失败')
    console.error(error)
  }
}

// 初始化加载
onMounted(() => {
  loadFavorites()
  loadWrongBook()
  loadHiddenQuestions()
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
