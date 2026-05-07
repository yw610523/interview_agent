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

      <!-- Redis配置 -->
      <a-tab-pane key="redis" tab="🗄️ Redis配置">
        <a-form
          :model="redisConfig"
          :label-col="{ span: 8 }"
          :wrapper-col="{ span: 16 }"
        >
          <a-form-item label="主机地址">
            <a-input v-model:value="redisConfig.redis_host" placeholder="例如: localhost" />
          </a-form-item>

          <a-form-item label="端口">
            <a-input-number v-model:value="redisConfig.redis_port" :min="1" :max="65535" />
          </a-form-item>

          <a-form-item label="密码">
            <a-input-password v-model:value="redisConfig.redis_password" placeholder="Redis密码（可选）" />
          </a-form-item>

          <a-form-item label="数据库">
            <a-input-number v-model:value="redisConfig.redis_db" :min="0" :max="15" />
          </a-form-item>

          <a-form-item :wrapper-col="{ offset: 8 }">
            <a-space>
              <a-button type="primary" @click="saveRedisConfig" :loading="savingRedis">
                保存配置
              </a-button>
              <a-button @click="loadSystemConfig">
                重置
              </a-button>
            </a-space>
          </a-form-item>
        </a-form>
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

// Redis配置
const redisConfig = ref({
  redis_host: 'localhost',
  redis_port: 6379,
  redis_password: '',
  redis_db: 0
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
const savingRedis = ref(false)
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
      
      // 加载Redis配置
      if (config.redis) {
        const redisUrl = config.redis.redis_url || 'redis://localhost:6379'
        // 解析 Redis URL - 支持有/无数据库号的格式
        // 格式1: redis://host:port/db
        // 格式2: redis://host:port
        // 格式3: redis://:password@host:port/db
        const match = redisUrl.match(/redis:\/\/(?:(.*):(.*)@)?([^:]+):(\d+)(?:\/(\d+))?/)
        if (match) {
          redisConfig.value = {
            redis_host: match[3],
            redis_port: parseInt(match[4]),
            redis_password: match[2] ? '********' : '',
            redis_db: match[5] ? parseInt(match[5]) : 0
          }
        } else {
          redisConfig.value = {
            redis_host: 'localhost',
            redis_port: 6379,
            redis_password: '',
            redis_db: 0
          }
        }
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

// 保存Redis配置
const saveRedisConfig = async () => {
  if (!redisConfig.value.redis_host) {
    message.warning('请输入主机地址')
    return
  }

  savingRedis.value = true
  try {
    // 构建 Redis URL
    const { redis_host, redis_port, redis_password, redis_db } = redisConfig.value
    
    // 如果有密码，添加到URL中
    let redisUrl
    if (redis_password && redis_password !== '********') {
      redisUrl = `redis://:${redis_password}@${redis_host}:${redis_port}/${redis_db}`
    } else {
      redisUrl = `redis://${redis_host}:${redis_port}/${redis_db}`
    }
    
    const res = await systemConfigApi.updateRedisConfig(redisUrl)
    if (res.status === 'success') {
      if (res.hot_reload) {
        message.success(res.message + ' ✨')
      } else {
        message.warning(res.message)
      }
    }
  } catch (error) {
    message.error('保存Redis配置失败')
    console.error(error)
  } finally {
    savingRedis.value = false
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
  padding: 24px;
}
</style>
