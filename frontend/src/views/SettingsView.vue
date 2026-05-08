<template>
  <div class="settings-view">
    <a-tabs v-model:activeKey="activeTab" type="card">
      <!-- 爬虫配置 -->
      <a-tab-pane key="crawler" tab="🕷️ 爬虫配置">
        <a-form
          :model="crawlerConfig"
          :label-col="{ span: 6 }"
          :wrapper-col="{ span: 18 }"
        >
          <a-form-item label="Sitemap URL" required>
            <a-input v-model:value="crawlerConfig.sitemap_url" placeholder="例如: javaguide.cn" />
          </a-form-item>

          <a-form-item label="超时时间(秒)">
            <a-input-number v-model:value="crawlerConfig.timeout" :min="10" :max="120" />
          </a-form-item>

          <a-form-item label="最大URL数量">
            <a-input-number v-model:value="crawlerConfig.max_urls" :min="1" placeholder="留空表示无限制" />
          </a-form-item>

          <a-form-item label="请求间隔(秒)">
            <a-input-number v-model:value="crawlerConfig.delay_between_requests" :min="0" :max="10" :step="0.1" />
          </a-form-item>

          <a-form-item label="输出目录">
            <a-input v-model:value="crawlerConfig.output_dir" />
          </a-form-item>

          <a-form-item label="User Agent">
            <a-textarea v-model:value="crawlerConfig.user_agent" :rows="2" />
          </a-form-item>

          <a-form-item label="URL包含规则">
            <a-select
              v-model:value="crawlerConfig.url_include_patterns"
              mode="tags"
              placeholder="输入URL包含模式，如: /docs/"
              style="width: 100%"
            />
          </a-form-item>

          <a-form-item label="URL排除规则">
            <a-select
              v-model:value="crawlerConfig.url_exclude_patterns"
              mode="tags"
              placeholder="输入URL排除模式，如: /admin/"
              style="width: 100%"
            />
          </a-form-item>

          <a-form-item :wrapper-col="{ offset: 6 }">
            <a-space>
              <a-button type="primary" @click="saveCrawlerConfig" :loading="savingCrawler">
                保存配置
              </a-button>
              <a-button @click="loadSystemConfig">
                重置
              </a-button>
            </a-space>
          </a-form-item>
        </a-form>
      </a-tab-pane>

      <!-- 模型配置 -->
      <a-tab-pane key="llm" tab="🤖 模型配置">
        <a-form
          :model="llmConfig"
          :label-col="{ span: 8 }"
          :wrapper-col="{ span: 16 }"
        >

          <a-form-item label="API Key">
            <a-input-password v-model:value="llmConfig.openai_api_key" placeholder="输入API Key" />
          </a-form-item>

          <a-form-item label="API Base URL">
            <a-input v-model:value="llmConfig.openai_api_base" placeholder="例如: https://api.openai.com/v1" />
          </a-form-item>

          <a-form-item label="模型名称">
            <a-input v-model:value="llmConfig.openai_model" placeholder="例如: gpt-4o-mini" />
          </a-form-item>

          <a-form-item label="Embedding模型">
            <a-input v-model:value="llmConfig.openai_embedding_model" placeholder="例如: text-embedding-3-small" />
          </a-form-item>

          <a-form-item label="Embedding维度">
            <a-input-number v-model:value="llmConfig.embedding_dimension" :min="128" :max="4096" />
          </a-form-item>

          <a-form-item label="最大输入Token">
            <a-input v-model:value="llmConfig.model_max_input_tokens" placeholder="留空使用默认值" />
          </a-form-item>

          <a-form-item label="最大输出Token">
            <a-input v-model:value="llmConfig.model_max_output_tokens" placeholder="留空使用默认值" />
          </a-form-item>

          <a-form-item :wrapper-col="{ offset: 8 }">
            <a-space>
              <a-button type="primary" @click="saveLlmConfig" :loading="savingLlm">
                保存配置
              </a-button>
              <a-button @click="loadSystemConfig">
                重置
              </a-button>
            </a-space>
          </a-form-item>
        </a-form>
      </a-tab-pane>

      <!-- Rerank 配置 -->
      <a-tab-pane key="rerank" tab="🔀 Rerank 配置">
        <a-alert
          message="Rerank 模型说明"
          description="Rerank 模型用于对推荐题目进行重排序，提升推荐质量。复用 LLM 的 API Key 和 Base URL，只需配置模型名称即可。默认关闭，可根据需要开启。"
          type="info"
          show-icon
          style="margin-bottom: 16px;"
        />
        
        <a-form
          :model="rerankConfig"
          :label-col="{ span: 8 }"
          :wrapper-col="{ span: 16 }"
        >
          <a-form-item label="启用 Rerank">
            <a-switch v-model:checked="rerankConfig.enabled" />
            <span style="margin-left: 8px; color: #8c8c8c;">{{ rerankConfig.enabled ? '已启用' : '未启用' }}</span>
          </a-form-item>

          <a-form-item label="模型名称" v-if="rerankConfig.enabled">
            <a-input v-model:value="rerankConfig.model_name" placeholder="例如: rerank-sf" />
            <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px;">
              复用 LLM 的 API Key 和 Base URL
            </div>
          </a-form-item>

          <a-form-item :wrapper-col="{ offset: 8 }">
            <a-space>
              <a-button type="primary" @click="saveRerankConfig" :loading="savingRerank">
                保存配置
              </a-button>
              <a-button @click="loadSystemConfig">
                重置
              </a-button>
            </a-space>
          </a-form-item>
        </a-form>
      </a-tab-pane>

      <!-- Redis配置 -->
      <a-tab-pane key="redis" tab="🗄️ Redis配置">
        <a-alert
          message="Redis 已内置"
          description="Redis 运行在 Docker 容器内，App 自动连接 redis://redis:6379，无需手动配置。如需从宿主机访问，可在 .env 文件中修改 REDIS_PORT。"
          type="info"
          show-icon
          style="margin-bottom: 16px;"
        />
        
        <a-descriptions bordered :column="1">
          <a-descriptions-item label="连接地址">
            <code>redis://redis:6379</code>
          </a-descriptions-item>
          <a-descriptions-item label="说明">
            App 容器通过 Docker 网络直接访问 Redis，使用固定的服务名和端口。
          </a-descriptions-item>
        </a-descriptions>
      </a-tab-pane>

      <!-- 邮件配置 -->
      <a-tab-pane key="email" tab="📧 邮件配置">
        <a-form
          :model="emailConfig"
          :label-col="{ span: 8 }"
          :wrapper-col="{ span: 16 }"
        >
          <a-form-item label="SMTP服务器">
            <a-input v-model:value="emailConfig.smtp_server" placeholder="例如: smtp.qq.com" />
          </a-form-item>

          <a-form-item label="SMTP端口">
            <a-input-number v-model:value="emailConfig.smtp_port" :min="1" :max="65535" />
          </a-form-item>

          <a-form-item label="用户名">
            <a-input v-model:value="emailConfig.smtp_user" placeholder="邮箱地址" />
          </a-form-item>

          <a-form-item label="密码">
            <a-input-password v-model:value="emailConfig.smtp_password" placeholder="SMTP密码或授权码" />
          </a-form-item>

          <a-form-item label="测试邮箱">
            <a-input v-model:value="emailConfig.smtp_test_user" placeholder="用于测试的邮箱地址" />
          </a-form-item>

          <a-form-item :wrapper-col="{ offset: 8 }">
            <a-space>
              <a-button type="primary" @click="saveEmailConfig" :loading="savingEmail">
                保存配置
              </a-button>
              <a-button @click="testEmailConfig" :loading="testingEmail">
                测试邮件发送
              </a-button>
              <a-button @click="loadSystemConfig">
                重置
              </a-button>
            </a-space>
          </a-form-item>
        </a-form>
      </a-tab-pane>

      <!-- 定时任务配置 -->
      <a-tab-pane key="scheduler" tab="⏰ 定时任务">
        <a-form
          :model="schedulerConfig"
          :label-col="{ span: 8 }"
          :wrapper-col="{ span: 16 }"
        >
          <a-form-item label="执行时间">
            <a-time-picker
              v-model:value="schedulerConfig.time"
              format="HH:mm"
              placeholder="选择时间"
            />
          </a-form-item>

          <a-form-item :wrapper-col="{ offset: 8 }">
            <a-space>
              <a-button type="primary" @click="saveSchedulerConfig" :loading="savingScheduler">
                保存配置
              </a-button>
              <a-button @click="loadSystemConfig">
                重置
              </a-button>
            </a-space>
          </a-form-item>
        </a-form>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { crawlerApi, systemConfigApi } from '../services'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import apiClient from '../services/api'

// 当前激活的tab
const activeTab = ref('crawler')

// 爬虫配置
const crawlerConfig = ref({
  sitemap_url: '',
  timeout: 30,
  max_urls: null,
  delay_between_requests: 0.5,
  output_dir: './crawl_results',
  user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
  url_include_patterns: [],
  url_exclude_patterns: []
})

// 模型配置
const llmConfig = ref({
  openai_api_key: '',
  openai_api_base: '',
  openai_model: 'gpt-4o-mini',
  openai_embedding_model: 'text-embedding-3-small',
  embedding_dimension: 1536,
  model_max_input_tokens: '',
  model_max_output_tokens: ''
})

// Rerank 配置
const rerankConfig = ref({
  enabled: false,
  model_name: 'rerank-sf'
})

// 邮件配置
const emailConfig = ref({
  smtp_server: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  smtp_test_user: ''
})

// 定时任务配置
const schedulerConfig = ref({
  time: null,
  hour: 22,
  minute: 0
})

// 状态
const savingCrawler = ref(false)
const savingLlm = ref(false)
const savingRerank = ref(false)
const savingEmail = ref(false)
const savingScheduler = ref(false)
const testingEmail = ref(false)

// 加载系统配置
const loadSystemConfig = async () => {
  try {
    const res = await systemConfigApi.getSystemConfig()
    if (res.status === 'success') {
      const config = res.config
      
      // 加载爬虫配置
      if (config.crawler) {
        crawlerConfig.value = config.crawler
      }
      
      // 加载模型配置
      if (config.llm) {
        llmConfig.value = config.llm
        // 隐藏API Key的中间部分
        if (llmConfig.value.openai_api_key && llmConfig.value.openai_api_key.length > 10) {
          llmConfig.value.openai_api_key = llmConfig.value.openai_api_key
        }
      }
      
      // 加载 Rerank 配置
      if (config.rerank) {
        rerankConfig.value = config.rerank
      }
      
      // 加载邮件配置
      if (config.email) {
        emailConfig.value = config.email
        // 隐藏密码
        if (emailConfig.value.smtp_password) {
          emailConfig.value.smtp_password = '********'
        }
      }
      
      // 加载定时任务配置
      if (config.scheduler) {
        const { hour, minute } = config.scheduler
        schedulerConfig.value.time = dayjs().hour(hour).minute(minute)
        schedulerConfig.value.hour = hour
        schedulerConfig.value.minute = minute
      }
    }
  } catch (error) {
    message.error('加载配置失败')
    console.error(error)
  }
}

// 保存爬虫配置
const saveCrawlerConfig = async () => {
  if (!crawlerConfig.value.sitemap_url) {
    message.warning('请输入Sitemap URL')
    return
  }

  savingCrawler.value = true
  try {
    const res = await crawlerApi.updateConfig(crawlerConfig.value)
    if (res.status === 'success') {
      message.success('爬虫配置保存成功')
    }
  } catch (error) {
    message.error('保存配置失败')
    console.error(error)
  } finally {
    savingCrawler.value = false
  }
}

// 保存模型配置
const saveLlmConfig = async () => {
  savingLlm.value = true
  try {
    const res = await systemConfigApi.updateLlmConfig(llmConfig.value)
    if (res.status === 'success') {
      message.success('模型配置保存成功')
    }
  } catch (error) {
    message.error('保存模型配置失败')
    console.error(error)
  } finally {
    savingLlm.value = false
  }
}

// 保存 Rerank 配置
const saveRerankConfig = async () => {
  savingRerank.value = true
  try {
    const res = await systemConfigApi.updateRerankConfig(rerankConfig.value)
    if (res.status === 'success') {
      message.success(res.message || 'Rerank 配置保存成功')
    }
  } catch (error) {
    message.error('保存 Rerank 配置失败')
    console.error(error)
  } finally {
    savingRerank.value = false
  }
}

// 保存邮件配置
const saveEmailConfig = async () => {
  if (!emailConfig.value.smtp_server || !emailConfig.value.smtp_user) {
    message.warning('请填写SMTP服务器和用户名')
    return
  }

  savingEmail.value = true
  try {
    const res = await systemConfigApi.updateEmailConfig(emailConfig.value)
    if (res.status === 'success') {
      message.success('邮件配置保存成功')
    }
  } catch (error) {
    message.error('保存邮件配置失败')
    console.error(error)
  } finally {
    savingEmail.value = false
  }
}

// 保存定时配置
const saveSchedulerConfig = async () => {
  if (!schedulerConfig.value.time) {
    message.warning('请选择执行时间')
    return
  }

  savingScheduler.value = true
  try {
    const hour = schedulerConfig.value.time.hour()
    const minute = schedulerConfig.value.time.minute()
    const res = await crawlerApi.updateSchedulerConfig(hour, minute)
    message.success('定时任务配置保存成功')
    schedulerConfig.value.hour = hour
    schedulerConfig.value.minute = minute
  } catch (error) {
    message.error('保存定时配置失败')
    console.error(error)
  } finally {
    savingScheduler.value = false
  }
}

// 测试邮件配置
const testEmailConfig = async () => {
  if (!emailConfig.value.smtp_server || !emailConfig.value.smtp_user) {
    message.warning('请先填写SMTP服务器和用户名')
    return
  }

  testingEmail.value = true
  try {
    const res = await systemConfigApi.testEmail()
    if (res.status === 'success') {
      message.success(res.message)
    } else {
      message.warning(res.message)
    }
  } catch (error) {
    message.error(error.response?.data?.detail || '邮件测试失败')
    console.error(error)
  } finally {
    testingEmail.value = false
  }
}

onMounted(() => {
  loadSystemConfig()
})
</script>

<style scoped>
.settings-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
}

@media (max-width: 768px) {
  .settings-view {
    padding: 8px;
  }
  
  :deep(.ant-tabs-nav) {
    overflow-x: auto;
    flex-wrap: nowrap;
  }
  
  :deep(.ant-form-item-label) {
    text-align: left;
  }
}
</style>
