<template>
  <div class="review-view">
    <div class="review-header">
      <h2>面试题审核管理</h2>
      <a-button type="primary" @click="loadPendingList" :loading="loading">
        🔄 刷新
      </a-button>
    </div>

    <!-- 统计卡片 -->
    <a-row :gutter="16" class="stats-row">
      <a-col :span="6">
        <a-card class="stat-card pending">
          <div class="stat-value">{{ stats.pending_count || 0 }}</div>
          <div class="stat-label">待审核</div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card approved">
          <div class="stat-value">{{ stats.approved_count || 0 }}</div>
          <div class="stat-label">已通过</div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card rejected">
          <div class="stat-value">{{ stats.rejected_count || 0 }}</div>
          <div class="stat-label">已拒绝</div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card sources">
          <div class="stat-sources">
            <div><span>批量爬虫:</span> {{ stats.batch_async_count || 0 }}</div>
            <div><span>单页爬取:</span> {{ stats.single_url_count || 0 }}</div>
            <div><span>API导入:</span> {{ stats.api_ingest_count || 0 }}</div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 操作按钮 -->
    <div class="action-bar">
      <a-space>
        <a-button type="primary" @click="approveAll" :loading="processing" :disabled="pendingList.length === 0">
          ✅ 全部通过
        </a-button>
        <a-button danger @click="rejectSelected" :loading="processing" :disabled="selectedRowKeys.length === 0">
          ❌ 拒绝选中
        </a-button>
        <a-button @click="loadPendingList" :loading="loading">
          📋 刷新列表
        </a-button>
      </a-space>
      <span class="tip">勾选题目后点击"拒绝选中"进行拒绝操作</span>
    </div>

    <!-- 待审核列表 -->
    <a-table
      :columns="columns"
      :data-source="pendingList"
      :loading="loading"
      :pagination="{ pageSize: 20 }"
      :row-selection="{ selectedRowKeys, onChange: onSelectChange }"
      row-key="id"
      class="pending-table"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'title'">
          <div class="title-cell">
            <div class="question-title">{{ record.title }}</div>
            <div class="question-meta">
              <a-tag v-if="record.difficulty" :color="getDifficultyColor(record.difficulty)">
                {{ record.difficulty }}
              </a-tag>
              <a-tag v-if="record.category">{{ record.category }}</a-tag>
              <span class="source-tag" :title="record.source">{{ getSourceLabel(record.source) }}</span>
            </div>
          </div>
        </template>
        <template v-else-if="column.key === 'answer'">
          <div class="answer-preview">{{ record.answer.substring(0, 150) }}{{ record.answer.length > 150 ? '...' : '' }}</div>
        </template>
        <template v-else-if="column.key === 'tags'">
          <a-tag v-for="tag in record.tags" :key="tag">{{ tag }}</a-tag>
        </template>
        <template v-else-if="column.key === 'created_at'">
          {{ formatTime(record.created_at) }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click="previewQuestion(record)">
              👁️ 预览
            </a-button>
            <a-button type="link" size="small" @click="approveOne(record.id)" :loading="processing">
              ✅ 通过
            </a-button>
            <a-button type="link" danger size="small" @click="rejectOne(record.id)" :loading="processing">
              ❌ 拒绝
            </a-button>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 预览模态框 -->
    <a-modal
      v-model:open="previewVisible"
      title="题目预览"
      :width="800"
      :footer="null"
    >
      <div v-if="previewQuestionData" class="preview-content">
        <h3>{{ previewQuestionData.title }}</h3>
        <div class="preview-meta">
          <a-tag :color="getDifficultyColor(previewQuestionData.difficulty)">
            {{ previewQuestionData.difficulty }}
          </a-tag>
          <a-tag v-if="previewQuestionData.category">{{ previewQuestionData.category }}</a-tag>
          <span v-if="previewQuestionData.tags">
            <a-tag v-for="tag in previewQuestionData.tags" :key="tag">{{ tag }}</a-tag>
          </span>
        </div>
        <div class="preview-source">
          来源: <a :href="previewQuestionData.source_url" target="_blank">{{ previewQuestionData.source_url }}</a>
        </div>
        <div class="preview-answer">
          <h4>答案:</h4>
          <MarkdownRenderer :content="previewQuestionData.answer" />
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import { reviewApi } from '../services'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'

const loading = ref(false)
const processing = ref(false)
const pendingList = ref([])
const stats = ref({
  pending_count: 0,
  approved_count: 0,
  rejected_count: 0,
  batch_async_count: 0,
  single_url_count: 0,
  api_ingest_count: 0
})
const selectedRowKeys = ref([])
const previewVisible = ref(false)
const previewQuestionData = ref(null)

const columns = [
  { title: '题目', key: 'title', width: '30%' },
  { title: '答案预览', key: 'answer', width: '35%' },
  { title: '标签', key: 'tags', width: '15%' },
  { title: '时间', key: 'created_at', width: '10%' },
  { title: '操作', key: 'action', width: '15%' }
]

// 加载待审核列表
const loadPendingList = async () => {
  loading.value = true
  try {
    const res = await reviewApi.getPendingList(100, 0)
    pendingList.value = res.questions || []
    await loadStats()
  } catch (error) {
    console.error('加载待审核列表失败', error)
    message.error('加载待审核列表失败')
  } finally {
    loading.value = false
  }
}

// 加载统计信息
const loadStats = async () => {
  try {
    const res = await reviewApi.getStats()
    stats.value = res.stats || {}
  } catch (error) {
    console.error('加载统计失败', error)
  }
}

// 审核通过（单个）
const approveOne = async (id) => {
  processing.value = true
  try {
    const res = await reviewApi.approveQuestions([id])
    if (res.status === 'success') {
      message.success(`已通过 ${res.approved} 个题目`)
      await loadPendingList()
    }
  } catch (error) {
    message.error('审核通过失败')
    console.error(error)
  } finally {
    processing.value = false
  }
}

// 审核通过（全部）
const approveAll = async () => {
  processing.value = true
  try {
    const res = await reviewApi.approveQuestions(null, true)
    if (res.status === 'success') {
      message.success(`已通过 ${res.approved} 个题目`)
      await loadPendingList()
    }
  } catch (error) {
    message.error('批量审核通过失败')
    console.error(error)
  } finally {
    processing.value = false
  }
}

// 审核拒绝（单个）
const rejectOne = async (id) => {
  processing.value = true
  try {
    const res = await reviewApi.rejectQuestions([id])
    if (res.status === 'success') {
      message.success(`已拒绝 ${res.rejected} 个题目`)
      await loadPendingList()
    }
  } catch (error) {
    message.error('审核拒绝失败')
    console.error(error)
  } finally {
    processing.value = false
  }
}

// 审核拒绝（选中）
const rejectSelected = async () => {
  if (selectedRowKeys.value.length === 0) {
    message.warning('请先选择要拒绝的题目')
    return
  }
  processing.value = true
  try {
    const res = await reviewApi.rejectQuestions(selectedRowKeys.value)
    if (res.status === 'success') {
      message.success(`已拒绝 ${res.rejected} 个题目`)
      selectedRowKeys.value = []
      await loadPendingList()
    }
  } catch (error) {
    message.error('批量审核拒绝失败')
    console.error(error)
  } finally {
    processing.value = false
  }
}

// 预览题目
const previewQuestion = (record) => {
  previewQuestionData.value = record
  previewVisible.value = true
}

// 选择变化
const onSelectChange = (keys) => {
  selectedRowKeys.value = keys
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN')
}

// 获取难度颜色
const getDifficultyColor = (difficulty) => {
  const colors = {
    easy: 'green',
    medium: 'blue',
    hard: 'red'
  }
  return colors[difficulty] || 'default'
}

// 获取来源标签
const getSourceLabel = (source) => {
  const labels = {
    batch_async: '批量爬虫',
    single_url: '单页爬取',
    batch_url_list: 'URL列表',
    batch_scheduled: '定时爬虫',
    scheduled_crawl: '调度爬取',
    api_ingest: 'API导入'
  }
  return labels[source] || source
}

// 简单的 Markdown 渲染（用于预览）
const renderMarkdown = (text) => {
  if (!text) return ''
  // 简单处理：替换换行和代码块
  return text
    .replace(/```(\w+)?/g, '<pre><code>')
    .replace(/```/g, '</code></pre>')
    .replace(/\n/g, '<br/>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

// 加载初始数据
onMounted(() => {
  loadPendingList()
  loadStats()
})
</script>

<style scoped>
.review-view {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.review-header h2 {
  margin: 0;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  text-align: center;
}

.stat-card.pending {
  border-top: 3px solid #1890ff;
}

.stat-card.approved {
  border-top: 3px solid #52c41a;
}

.stat-card.rejected {
  border-top: 3px solid #ff4d4f;
}

.stat-card.sources {
  border-top: 3px solid #722ed1;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 8px;
}

.stat-sources {
  font-size: 12px;
  color: #666;
  text-align: left;
  padding: 8px 0;
}

.stat-sources div {
  margin: 4px 0;
}

.stat-sources span {
  display: inline-block;
  width: 80px;
  color: #999;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px;
  background: #f5f5f5;
  border-radius: 8px;
}

.action-bar .tip {
  color: #999;
  font-size: 12px;
}

.pending-table {
  background: #fff;
}

.title-cell {
  max-width: 300px;
}

.question-title {
  font-weight: 500;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.question-meta {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.source-tag {
  font-size: 11px;
  color: #999;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 3px;
}

.answer-preview {
  color: #666;
  font-size: 13px;
  max-height: 60px;
  overflow: hidden;
}

.preview-content {
  max-height: 60vh;
  overflow-y: auto;
}

.preview-content h3 {
  margin-bottom: 16px;
}

.preview-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.preview-source {
  color: #666;
  margin-bottom: 16px;
  font-size: 13px;
}

.preview-source a {
  color: #1890ff;
}

.preview-answer {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 8px;
}

.preview-answer h4 {
  margin-bottom: 12px;
}
</style>