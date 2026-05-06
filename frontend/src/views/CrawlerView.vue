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
                <a-button type="primary" size="large" @click="triggerCrawl" :loading="crawling">
                  🚀 立即执行批量爬取
                </a-button>
                <a-button size="large" @click="loadCrawlStatus">
                  📊 查看爬取状态
                </a-button>
              </a-space>
            </a-card>
          </a-col>

          <!-- 爬取状态 -->
          <a-col :span="24" v-if="crawlStatus">
            <a-card title="📈 爬取状态" :bordered="false">
              <a-descriptions bordered :column="2">
                <a-descriptions-item label="状态">
                  <a-tag :color="crawlStatus.status === 'completed' ? 'success' : 'default'">
                    {{ crawlStatus.status }}
                  </a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="总URL数">
                  {{ crawlStatus.statistics?.total_urls || 0 }}
                </a-descriptions-item>
                <a-descriptions-item label="成功扫描">
                  {{ crawlStatus.statistics?.successful_scans || 0 }}
                </a-descriptions-item>
                <a-descriptions-item label="失败扫描">
                  {{ crawlStatus.statistics?.failed_scans || 0 }}
                </a-descriptions-item>
                <a-descriptions-item label="识别问题数">
                  {{ crawlStatus.parsed_questions || 0 }}
                </a-descriptions-item>
                <a-descriptions-item label="入库问题数">
                  {{ crawlStatus.inserted_questions || 0 }}
                </a-descriptions-item>
              </a-descriptions>
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
                    placeholder="输入要爬取的页面URL，例如: https://www.runoob.com/python3/python3-tutorial.html"
                    style="width: 600px;"
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
import { ref, onMounted } from 'vue'
import { crawlerApi } from '../services'
import { message } from 'ant-design-vue'

const activeTab = ref('batch')

// 状态
const crawling = ref(false)
const crawlStatus = ref(null)

// 单页爬取
const singlePageUrl = ref('')
const singlePageLoading = ref(false)
const singlePageResult = ref(null)
const singlePageProcessing = ref(false)
const processingMessage = ref('')
const processingProgress = ref(0)
const realtimeLogs = ref([])
let eventSource = null

// 触发批量爬取
const triggerCrawl = async () => {
  crawling.value = true
  try {
    const res = await crawlerApi.triggerCrawl()
    message.success(`爬取完成！识别到 ${res.parsed_questions} 个问题`)
    // 加载最新状态
    await loadCrawlStatus()
  } catch (error) {
    message.error('爬取失败')
    console.error(error)
  } finally {
    crawling.value = false
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

// 格式化日志时间
const formatLogTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

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
</script>

<style scoped>
.crawler-view {
  max-width: 1200px;
  margin: 0 auto;
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
