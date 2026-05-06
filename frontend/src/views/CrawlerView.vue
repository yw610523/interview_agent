<template>
  <div class="crawler-view">
    <a-tabs v-model:activeKey="activeTab">
      <!-- 批量爬取 -->
      <a-tab-pane key="batch" tab="批量爬取">
        <a-row :gutter="[24, 24]">
          <!-- 配置表单 -->
          <a-col :span="24">
            <a-card title="⚙️ 爬虫配置" :bordered="false">
              <a-form
                :model="configForm"
                :label-col="{ span: 6 }"
                :wrapper-col="{ span: 18 }"
              >
                <a-form-item label="Sitemap URL" required>
                  <a-input v-model:value="configForm.sitemap_url" placeholder="例如: javaguide.cn" />
                </a-form-item>

                <a-form-item label="超时时间(秒)">
                  <a-input-number v-model:value="configForm.timeout" :min="10" :max="120" />
                </a-form-item>

                <a-form-item label="最大URL数量">
                  <a-input-number v-model:value="configForm.max_urls" :min="1" placeholder="留空表示无限制" />
                </a-form-item>

                <a-form-item label="请求间隔(秒)">
                  <a-input-number v-model:value="configForm.delay_between_requests" :min="0" :max="10" :step="0.1" />
                </a-form-item>

                <a-form-item label="输出目录">
                  <a-input v-model:value="configForm.output_dir" />
                </a-form-item>

                <a-form-item label="User Agent">
                  <a-textarea v-model:value="configForm.user_agent" :rows="2" />
                </a-form-item>

                <a-form-item label="URL包含规则">
                  <a-select
                    v-model:value="configForm.url_include_patterns"
                    mode="tags"
                    placeholder="输入URL包含模式，如: /docs/"
                    style="width: 100%"
                  />
                </a-form-item>

                <a-form-item label="URL排除规则">
                  <a-select
                    v-model:value="configForm.url_exclude_patterns"
                    mode="tags"
                    placeholder="输入URL排除模式，如: /admin/"
                    style="width: 100%"
                  />
                </a-form-item>

                <a-form-item :wrapper-col="{ offset: 6 }">
                  <a-space>
                    <a-button type="primary" @click="saveConfig" :loading="saving">
                      保存配置
                    </a-button>
                    <a-button @click="loadConfig">
                      重置
                    </a-button>
                  </a-space>
                </a-form-item>
              </a-form>
            </a-card>
          </a-col>

          <!-- 定时任务配置 -->
          <a-col :span="24">
            <a-card title="⏰ 定时任务配置" :bordered="false">
              <a-form layout="inline">
                <a-form-item label="执行时间">
                  <a-time-picker
                    v-model:value="schedulerTime"
                    format="HH:mm"
                    placeholder="选择时间"
                  />
                </a-form-item>
                <a-form-item>
                  <a-button type="primary" @click="saveSchedulerConfig" :loading="savingScheduler">
                    保存定时配置
                  </a-button>
                </a-form-item>
              </a-form>
              <a-alert
                message="注意：修改定时配置后需要重启服务才能生效"
                type="info"
                show-icon
                style="margin-top: 12px;"
              />
            </a-card>
          </a-col>

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

              <!-- 单页爬取结果 -->
              <a-alert
                v-if="singlePageResult"
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
import dayjs from 'dayjs'

const activeTab = ref('batch')

// 配置表单
const configForm = ref({
  sitemap_url: '',
  timeout: 30,
  max_urls: null,
  delay_between_requests: 0.5,
  output_dir: './crawl_results',
  user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
  url_include_patterns: [],
  url_exclude_patterns: []
})

// 定时任务时间
const schedulerTime = ref(null)

// 状态
const saving = ref(false)
const savingScheduler = ref(false)
const crawling = ref(false)
const crawlStatus = ref(null)

// 单页爬取
const singlePageUrl = ref('')
const singlePageLoading = ref(false)
const singlePageResult = ref(null)

// 加载配置
const loadConfig = async () => {
  try {
    const res = await crawlerApi.getConfig()
    if (res.status === 'success') {
      configForm.value = res.config
    }
  } catch (error) {
    message.error('加载配置失败')
    console.error(error)
  }
}

// 保存配置
const saveConfig = async () => {
  if (!configForm.value.sitemap_url) {
    message.warning('请输入Sitemap URL')
    return
  }

  saving.value = true
  try {
    const res = await crawlerApi.updateConfig(configForm.value)
    if (res.status === 'success') {
      message.success('配置保存成功')
    }
  } catch (error) {
    message.error('保存配置失败')
    console.error(error)
  } finally {
    saving.value = false
  }
}

// 保存定时配置
const saveSchedulerConfig = async () => {
  if (!schedulerTime.value) {
    message.warning('请选择执行时间')
    return
  }

  savingScheduler.value = true
  try {
    const hour = schedulerTime.value.hour()
    const minute = schedulerTime.value.minute()
    const res = await crawlerApi.updateSchedulerConfig(hour, minute)
    message.success(res.message)
  } catch (error) {
    message.error('保存定时配置失败')
    console.error(error)
  } finally {
    savingScheduler.value = false
  }
}

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

// 单页爬取
const crawlSinglePage = async () => {
  if (!singlePageUrl.value) {
    message.warning('请输入页面URL')
    return
  }

  singlePageLoading.value = true
  singlePageResult.value = null

  try {
    const res = await crawlerApi.crawlSinglePage(singlePageUrl.value)
    if (res.status === 'success') {
      singlePageResult.value = res
      message.success(`爬取成功！识别到 ${res.parsed_questions} 个问题`)
    }
  } catch (error) {
    message.error('单页爬取失败')
    console.error(error)
  } finally {
    singlePageLoading.value = false
  }
}

onMounted(() => {
  loadConfig()
  loadCrawlStatus()
})
</script>

<style scoped>
.crawler-view {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
