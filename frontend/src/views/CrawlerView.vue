<template>
  <div class="crawler-view">
    <a-tabs v-model:activeKey="activeTab">
      <!-- 批量爬取 -->
      <a-tab-pane key="batch" tab="批量爬取">
        <a-row :gutter="[24, 24]">
          <!-- 操作按钮 -->
          <a-col :span="24">
            <a-card :bordered="false">
              <a-space size="large">
                <a-button type="primary" size="large" @click="triggerAsyncCrawl" :loading="crawling">
                  🚀 启动异步批量爬取
                </a-button>
                <a-button 
                  danger 
                  size="large" 
                  @click="stopCrawlTask" 
                  :disabled="!currentTaskId || !isTaskRunning"
                  :loading="stoppingTask"
                >
                  ⏹️ 终止当前任务
                </a-button>
                <a-button size="large" @click="loadCrawlStatus">
                  📊 查看爬取状态
                </a-button>
              </a-space>
            </a-card>
          </a-col>

          <!-- 爬取状态 -->
          <a-col :span="24" v-if="displayCrawlStatus">
            <a-card title="📈 爬取状态" :bordered="false">
              <a-descriptions bordered :column="2">
                <a-descriptions-item label="状态">
                  <a-tag :color="getStatusColor(displayCrawlStatus.status)">
                    {{ displayCrawlStatus.status }}
                  </a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="总 URL 数">
                  {{ displayCrawlStatus.statistics?.total_urls || displayCrawlStatus.total_urls || 0 }}
                </a-descriptions-item>
                <a-descriptions-item label="成功扫描">
                  {{ displayCrawlStatus.statistics?.successful_scans || 0 }}
                </a-descriptions-item>
                <a-descriptions-item label="失败扫描">
                  {{ displayCrawlStatus.statistics?.failed_scans || 0 }}
                </a-descriptions-item>
                <a-descriptions-item label="识别问题数">
                  {{ displayCrawlStatus.parsed_questions || 0 }}
                </a-descriptions-item>
                <a-descriptions-item label="入库问题数">
                  {{ displayCrawlStatus.inserted_questions || 0 }}
                </a-descriptions-item>
              </a-descriptions>
            </a-card>
          </a-col>

          <!-- 当前运行任务状态 -->
          <a-col :span="24" v-if="currentTask">
            <a-card title="🔄 当前任务进度" :bordered="false">
              <a-progress 
                :percent="currentTask.progress" 
                :status="getProgressStatus(currentTask.status)"
                :stroke-color="getProgressColor(currentTask.status)"
              />
              <a-descriptions bordered :column="3" size="small" style="margin-top: 16px;">
                <a-descriptions-item label="任务ID">
                  {{ currentTask.task_id }}
                </a-descriptions-item>
                <a-descriptions-item label="状态">
                  <a-tag :color="getStatusColor(currentTask.status)">
                    {{ currentTask.status }}
                  </a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="处理进度">
                  {{ currentTask.processed_urls }} / {{ currentTask.total_urls }}
                </a-descriptions-item>
                <a-descriptions-item label="已识别问题">
                  {{ currentTask.parsed_questions }}
                </a-descriptions-item>
                <a-descriptions-item label="已入库问题">
                  {{ currentTask.inserted_questions }}
                </a-descriptions-item>
                <a-descriptions-item label="开始时间" v-if="currentTask.start_time">
                  {{ formatTime(currentTask.start_time) }}
                </a-descriptions-item>
              </a-descriptions>
              <a-alert 
                v-if="currentTask.error_message" 
                :message="currentTask.error_message" 
                type="error" 
                show-icon 
                style="margin-top: 16px;"
              />
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- 单页爬取 -->
      <a-tab-pane key="single" tab="单页爬取">
        <a-row :gutter="[24, 24]">
          <a-col :span="24">
            <a-card title="🔍 智能爬取单个页面" :bordered="false">
              <a-form layout="inline">
                <a-form-item label="页面URL" style="width: 100%;">
                  <a-input
                    v-model:value="singlePageUrl"
                    placeholder="输入要爬取的页面URL"
                    style="width: 100%; max-width: 600px;"
                  />
                </a-form-item>
                <a-form-item>
                  <a-button type="primary" @click="crawlSinglePage" :loading="singlePageLoading">
                    开始爬取
                  </a-button>
                </a-form-item>
              </a-form>

              <a-divider />

              <!-- 处理状态提示 -->
              <a-alert
                v-if="singlePageProcessing"
                message="正在处理中..."
                type="info"
                show-icon
              >
                <template #description>
                  <div>{{ processingMessage }}</div>
                  <a-progress 
                    v-if="processingProgress > 0" 
                    :percent="processingProgress" 
                    status="active" 
                    :stroke-color="{ from: '#108ee9', to: '#87d068' }"
                  />
                </template>
              </a-alert>

              <!-- 实时日志显示区域 -->
              <a-card 
                v-if="realtimeLogs.length > 0 || singlePageProcessing" 
                title="📋 实时处理日志" 
                :bordered="false" 
                style="margin-top: 16px; background: #f5f5f5;"
              >
                <div class="log-container">
                  <div 
                    v-for="(log, index) in realtimeLogs" 
                    :key="index" 
                    class="log-item"
                    :class="`log-${log.step}`"
                  >
                    <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
                    <span class="log-message">{{ log.message }}</span>
                  </div>
                  <div v-if="singlePageProcessing && realtimeLogs.length === 0" class="log-placeholder">
                    等待处理开始...
                  </div>
                </div>
              </a-card>

              <!-- 单页爬取结果 -->
              <a-alert
                v-if="singlePageResult && !singlePageProcessing"
                :message="`爬取完成！识别到 ${singlePageResult.parsed_questions} 个问题，已入库 ${singlePageResult.inserted_questions} 个`"
                type="success"
                show-icon
                closable
              >
                <template #description>
                  <a-descriptions :column="2" size="small">
                    <a-descriptions-item label="页面标题">
                      {{ singlePageResult.title }}
                    </a-descriptions-item>
                    <a-descriptions-item label="字数">
                      {{ singlePageResult.word_count }}
                    </a-descriptions-item>
                    <a-descriptions-item label="加载时间">
                      {{ singlePageResult.load_time }}s
                    </a-descriptions-item>
                  </a-descriptions>
                </template>
              </a-alert>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { crawlerApi } from '../services'
import { message } from 'ant-design-vue'

const activeTab = ref('batch')

// 状态
const crawling = ref(false)
const crawlStatus = ref(null)
const currentTaskId = ref(null)
const currentTask = ref(null)
const stoppingTask = ref(false)
let pollingInterval = null

// 计算任务是否正在运行
const isTaskRunning = computed(() => {
  return currentTask.value && 
         (currentTask.value.status === 'running' || currentTask.value.status === 'pending')
})

// 计算显示的爬取状态（优先显示当前任务数据）
const displayCrawlStatus = computed(() => {
  // 如果有当前任务且任务已完成/停止/失败，显示任务数据
  if (currentTask.value && 
      (currentTask.value.status === 'completed' || 
       currentTask.value.status === 'stopped' || 
       currentTask.value.status === 'failed')) {
    return {
      status: currentTask.value.status === 'completed' ? 'completed' : 
              currentTask.value.status === 'stopped' ? 'stopped' : 'failed',
      statistics: {
        total_urls: currentTask.value.total_urls || 0,
        successful_scans: currentTask.value.processed_urls || 0,
        failed_scans: 0,
      },
      parsed_questions: currentTask.value.parsed_questions || 0,
      inserted_questions: currentTask.value.inserted_questions || 0,
    }
  }
  // 否则显示旧的全局状态
  return crawlStatus.value?.last_crawl || crawlStatus.value
})

// 触发异步批量爬取
const triggerAsyncCrawl = async () => {
  crawling.value = true
  try {
    const res = await crawlerApi.triggerCrawlAsync()
    message.success(`爬虫任务已启动！任务ID: ${res.task_id}`)
    currentTaskId.value = res.task_id
    
    // 开始轮询任务状态
    startPolling(res.task_id)
  } catch (error) {
    message.error('启动爬虫任务失败')
    console.error(error)
  } finally {
    crawling.value = false
  }
}

// 停止当前任务
const stopCrawlTask = async () => {
  if (!currentTaskId.value) {
    message.warning('没有正在运行的任务')
    return
  }
  
  stoppingTask.value = true
  try {
    await crawlerApi.stopTask(currentTaskId.value)
    message.success('已请求停止任务')
    // 继续轮询以获取最终状态
  } catch (error) {
    message.error('停止任务失败')
    console.error(error)
  } finally {
    stoppingTask.value = false
  }
}

// 开始轮询任务状态
const startPolling = (taskId) => {
  // 清除之前的轮询
  if (pollingInterval) {
    clearInterval(pollingInterval)
  }
  
  // 立即获取一次状态
  fetchTaskStatus(taskId)
  
  // 每2秒轮询一次
  pollingInterval = setInterval(() => {
    fetchTaskStatus(taskId)
  }, 2000)
}

// 获取任务状态
const fetchTaskStatus = async (taskId) => {
  try {
    const task = await crawlerApi.getTaskStatus(taskId)
    currentTask.value = task
    
    // 如果任务已完成、停止或失败，停止轮询
    if (task.status === 'completed' || 
        task.status === 'stopped' || 
        task.status === 'failed') {
      if (pollingInterval) {
        clearInterval(pollingInterval)
        pollingInterval = null
      }
      
      // 显示完成消息
      if (task.status === 'completed') {
        message.success(`任务完成！识别到 ${task.parsed_questions} 个问题`)
      } else if (task.status === 'stopped') {
        message.info('任务已被终止')
      } else if (task.status === 'failed') {
        message.error(`任务失败: ${task.error_message}`)
      }
      
      // 加载最新的爬取状态
      await loadCrawlStatus()
    }
  } catch (error) {
    console.error('获取任务状态失败:', error)
  }
}

// 加载爬取状态
const loadCrawlStatus = async () => {
  try {
    const res = await crawlerApi.getCrawlStatus()
    crawlStatus.value = res
  } catch (error) {
    message.error('加载状态失败')
    console.error(error)
  }
}

// 获取状态颜色
const getStatusColor = (status) => {
  const colorMap = {
    'pending': 'default',
    'running': 'processing',
    'completed': 'success',
    'stopped': 'warning',
    'failed': 'error'
  }
  return colorMap[status] || 'default'
}

// 获取进度条状态
const getProgressStatus = (status) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  if (status === 'stopped') return 'exception'
  return 'active'
}

// 获取进度条颜色
const getProgressColor = (status) => {
  const colorMap = {
    'pending': '#d9d9d9',
    'running': { from: '#108ee9', to: '#87d068' },
    'completed': '#52c41a',
    'stopped': '#faad14',
    'failed': '#ff4d4f'
  }
  return colorMap[status] || '#d9d9d9'
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', { hour12: false })
}

// 格式化日志时间
const formatLogTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

// 单页爬取（使用SSE实时日志）
const singlePageUrl = ref('')
const singlePageLoading = ref(false)
const singlePageResult = ref(null)
const singlePageProcessing = ref(false)
const processingMessage = ref('')
const processingProgress = ref(0)
const realtimeLogs = ref([])
let eventSource = null

// 单页爬取（使用SSE实时日志）
const crawlSinglePage = async () => {
  if (!singlePageUrl.value) {
    message.warning('请输入页面URL')
    return
  }

  singlePageLoading.value = true
  singlePageResult.value = null
  singlePageProcessing.value = true
  processingMessage.value = '正在初始化...'
  processingProgress.value = 0
  realtimeLogs.value = []
  
  // 关闭之前的连接
  if (eventSource) {
    eventSource.close()
  }

  try {
    // 创建SSE连接
    const encodedUrl = encodeURIComponent(singlePageUrl.value)
    eventSource = new EventSource(`/api/crawl/single-page/stream?url=${encodedUrl}`)
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'start') {
          processingMessage.value = data.message
          processingProgress.value = data.progress
        } else if (data.type === 'log') {
          // 添加实时日志
          realtimeLogs.value.push({
            message: data.message,
            progress: data.progress,
            step: data.step,
            timestamp: data.timestamp
          })
          
          // 更新进度和消息
          processingProgress.value = data.progress
          processingMessage.value = data.message
          
          // 自动滚动到底部
          setTimeout(() => {
            const logContainer = document.querySelector('.log-container')
            if (logContainer) {
              logContainer.scrollTop = logContainer.scrollHeight
            }
          }, 100)
        } else if (data.type === 'complete') {
          // 处理完成
          singlePageResult.value = data.result
          message.success(`爬取成功！识别到 ${data.result.parsed_questions} 个问题`)
          
          // 延迟隐藏处理状态
          setTimeout(() => {
            singlePageProcessing.value = false
          }, 1000)
          
          // 关闭SSE连接
          eventSource.close()
          eventSource = null
        } else if (data.type === 'error') {
          message.error(data.message || '爬取失败')
          singlePageProcessing.value = false
          eventSource.close()
          eventSource = null
        }
      } catch (e) {
        console.error('解析SSE消息失败:', e)
      }
    }
    
    eventSource.onerror = (error) => {
      console.error('SSE连接错误:', error)
      message.error('实时连接失败，请重试')
      singlePageProcessing.value = false
      eventSource.close()
      eventSource = null
    }
    
  } catch (error) {
    message.error('单页爬取失败')
    console.error(error)
    singlePageProcessing.value = false
  } finally {
    singlePageLoading.value = false
  }
}

onMounted(() => {
  loadCrawlStatus()
})

onUnmounted(() => {
  // 清理轮询
  if (pollingInterval) {
    clearInterval(pollingInterval)
  }
  // 清理SSE连接
  if (eventSource) {
    eventSource.close()
  }
})
</script>

<style scoped>
.crawler-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
}

@media (max-width: 768px) {
  .crawler-view {
    padding: 8px;
  }
  
  :deep(.ant-descriptions-item-label),
  :deep(.ant-descriptions-item-content) {
    display: block;
    width: 100% !important;
  }
  
  :deep(.ant-form-inline) {
    flex-direction: column;
    align-items: stretch;
  }
  
  :deep(.ant-form-item) {
    margin-bottom: 12px;
    width: 100%;
  }
}

.log-container {
  max-height: 400px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  padding: 12px;
  background: #1e1e1e;
  border-radius: 4px;
}

.log-item {
  padding: 4px 8px;
  margin-bottom: 4px;
  border-left: 3px solid transparent;
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.log-scanning {
  border-left-color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
}

.log-scanned {
  border-left-color: #52c41a;
  background: rgba(82, 196, 26, 0.1);
}

.log-analyzing,
.log-processing {
  border-left-color: #faad14;
  background: rgba(250, 173, 20, 0.1);
}

.log-inserting,
.log-finalizing {
  border-left-color: #722ed1;
  background: rgba(114, 46, 209, 0.1);
}

.log-completed,
.log-finished {
  border-left-color: #52c41a;
  background: rgba(82, 196, 26, 0.15);
  font-weight: bold;
}

.log-error {
  border-left-color: #ff4d4f;
  background: rgba(255, 77, 79, 0.1);
  color: #ff4d4f;
}

.log-info {
  border-left-color: #d9d9d9;
  background: rgba(217, 217, 217, 0.05);
}

.log-warning {
  border-left-color: #faad14;
  background: rgba(250, 173, 20, 0.15);
  color: #faad14;
}

.log-time {
  color: #8c8c8c;
  margin-right: 12px;
  font-size: 12px;
}

.log-message {
  color: #d9d9d9;
}

.log-placeholder {
  color: #8c8c8c;
  text-align: center;
  padding: 20px;
  font-style: italic;
}
</style>
