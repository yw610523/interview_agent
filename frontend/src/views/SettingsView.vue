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
            <a-input v-model:value="crawlerConfig.sitemap_url" placeholder="例如: javaguide.cn"/>
          </a-form-item>

          <a-form-item label="根路径前缀">
            <a-input v-model:value="crawlerConfig.root_url" placeholder="例如: /blog, /docs（留空表示根目录）"/>
          </a-form-item>

          <a-form-item label="超时时间(秒)">
            <a-input-number v-model:value="crawlerConfig.timeout" :min="10" :max="120"/>
          </a-form-item>

          <a-form-item label="最大URL数量">
            <a-input-number v-model:value="crawlerConfig.max_urls" :min="1" placeholder="留空表示无限制"/>
          </a-form-item>

          <a-form-item label="请求间隔(秒)">
            <a-input-number v-model:value="crawlerConfig.delay_between_requests" :min="0" :max="10" :step="0.1"/>
          </a-form-item>

          <a-form-item label="User Agent">
            <a-textarea v-model:value="crawlerConfig.user_agent" :rows="2"/>
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
            <a-input-password v-model:value="llmConfig.openai_api_key" placeholder="输入API Key"/>
          </a-form-item>

          <a-form-item label="API Base URL">
            <a-input v-model:value="llmConfig.openai_api_base" placeholder="例如: https://api.openai.com/v1"/>
          </a-form-item>

          <a-form-item label="模型名称">
            <a-input v-model:value="llmConfig.openai_model" placeholder="例如: gpt-4o-mini"/>
          </a-form-item>

          <a-form-item label="Embedding模型">
            <a-input v-model:value="llmConfig.openai_embedding_model" placeholder="例如: text-embedding-3-small"/>
          </a-form-item>

          <a-form-item label="Embedding维度">
            <a-input-number v-model:value="llmConfig.embedding_dimension" :min="128" :max="4096"/>
          </a-form-item>

          <a-form-item label="最大输入Token">
            <a-input v-model:value="llmConfig.model_max_input_tokens" placeholder="留空使用默认值"/>
          </a-form-item>

          <a-form-item label="最大输出Token">
            <a-input v-model:value="llmConfig.model_max_output_tokens" placeholder="留空使用默认值"/>
          </a-form-item>

          <a-divider/>

          <a-form-item label="启用 Rerank">
            <a-switch v-model:checked="llmConfig.rerank_enabled"/>
            <span style="margin-left: 8px; color: #8c8c8c;">{{ llmConfig.rerank_enabled ? '已启用' : '未启用' }}</span>
          </a-form-item>

          <a-form-item label="Rerank 模型名称" v-if="llmConfig.rerank_enabled">
            <a-input v-model:value="llmConfig.rerank_model_name" placeholder="例如: rerank-sf"/>
            <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px;">
              复用 LLM 的 API Key 和 Base URL
            </div>
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
          <a-form-item label="Redis服务器">
            <a-input v-model:value="redisConfig.host" placeholder="例如: localhost, redis.example.com"/>
          </a-form-item>

          <a-form-item label="Redis端口">
            <a-input-number v-model:value="redisConfig.port" :min="1" :max="65535" placeholder="默认: 6379"/>
          </a-form-item>

          <a-form-item label="密码">
            <a-input-password v-model:value="redisConfig.password" placeholder="留空表示无需密码"/>
            <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px;">
              如果不需要密码认证，请留空
            </div>
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
            <a-input v-model:value="emailConfig.smtp_server" placeholder="例如: smtp.qq.com"/>
          </a-form-item>

          <a-form-item label="SMTP端口">
            <a-input-number v-model:value="emailConfig.smtp_port" :min="1" :max="65535"/>
          </a-form-item>

          <a-form-item label="用户名">
            <a-input v-model:value="emailConfig.smtp_user" placeholder="邮箱地址"/>
          </a-form-item>

          <a-form-item label="密码">
            <a-input-password v-model:value="emailConfig.smtp_password" placeholder="SMTP密码或授权码"/>
          </a-form-item>

          <a-form-item label="测试邮箱">
            <a-input v-model:value="emailConfig.smtp_test_user" placeholder="用于测试的邮箱地址"/>
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

      <!-- 内容处理配置 -->
      <a-tab-pane key="content" tab="📄 内容处理">
        <a-alert
            message="提示：滑动窗口切分策略可以解决语义截断问题，确保每个 Chunk 都保留上下文"
            type="info"
            show-icon
            style="margin-bottom: 16px"
        />

        <a-form
            :model="contentConfig"
            :label-col="{ span: 8 }"
            :wrapper-col="{ span: 16 }"
        >
          <a-form-item label="单页最大长度">
            <a-input-number v-model:value="contentConfig.max_content_length_per_page" :min="500" :max="10000" :step="100"/>
            <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px;">
              超过此长度的页面会被切分为多个 Chunk 处理（字符数）
            </div>
          </a-form-item>

          <a-form-item label="切分模式">
            <a-select v-model:value="contentConfig.chunking_mode">
              <a-select-option value="semantic">语义切分（推荐）</a-select-option>
              <a-select-option value="markdown">Markdown 标题切分</a-select-option>
              <a-select-option value="fixed">固定长度切分（不推荐）</a-select-option>
            </a-select>
            <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px;">
              语义切分：优先在段落/句子边界切分
            </div>
          </a-form-item>

          <a-divider>滑动窗口切分策略</a-divider>

          <a-form-item label="块大小 (Chunk Size)">
            <a-input-number v-model:value="contentConfig.chunk_size" :min="100" :max="4000" :step="64"/>
            <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px;">
              推荐值：256（精细）/ 512（平衡）/ 1024（长文档）
            </div>
          </a-form-item>

          <a-form-item label="重叠长度 (Overlap)">
            <a-input-number v-model:value="contentConfig.chunk_overlap" :min="0" :max="1024" :step="32"/>
            <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px;">
              相邻 Chunk 之间的重复内容，通常为 chunk_size 的 10%-25%
            </div>
          </a-form-item>

          <a-form-item label="最小 Chunk 长度">
            <a-input-number v-model:value="contentConfig.min_chunk_length" :min="50" :max="500"/>
            <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px;">
              低于此长度的内容会合并到前一个 Chunk
            </div>
          </a-form-item>

          <a-form-item label="最大 Chunk 数量">
            <a-input-number v-model:value="contentConfig.max_chunks_per_page" :min="1" :max="500"/>
            <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px;">
              单个页面最多切分为多少个块，防止过多的 LLM 调用
            </div>
          </a-form-item>

          <a-form-item label="分隔符优先级">
            <a-select
                v-model:value="contentConfig.separators"
                mode="tags"
                placeholder="输入分隔符，如: \n\n"
                style="width: 100%"
            />
            <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px;">
              系统会按顺序尝试分隔符，优先在语义边界处切分
            </div>
          </a-form-item>

          <a-form-item :wrapper-col="{ offset: 8 }">
            <a-space>
              <a-button type="primary" @click="saveContentConfig" :loading="savingContent">
                保存配置
              </a-button>
              <a-button @click="loadSystemConfig">
                重置
              </a-button>
            </a-space>
          </a-form-item>
        </a-form>
      </a-tab-pane>

      <!-- 提示词配置 -->
      <a-tab-pane key="prompts" tab="📝 提示词管理">
        <a-alert
            message="提示：修改提示词后将立即生效，新的爬虫任务将使用更新后的提示词"
            type="info"
            show-icon
            style="margin-bottom: 16px"
        />

        <a-space direction="vertical" style="width: 100%" :size="16">
          <!-- 面试题提取提示词 -->
          <a-card title="🎯 面试题提取系统提示词" size="small">
            <template #extra>
              <a-tooltip title="重置为默认值">
                <a-button size="small" @click="resetPrompt('question_extraction_system')">
                  <template #icon>
                    <UndoOutlined/>
                  </template>
                </a-button>
              </a-tooltip>
            </template>

            <a-textarea
                v-model:value="promptsConfig.question_extraction_system"
                :rows="20"
                placeholder="请输入系统提示词..."
                :disabled="savingPrompts"
                style="font-family: 'Consolas', 'Monaco', monospace; font-size: 13px;"
            />

            <div class="prompt-tips">
              <strong>💡 编写建议：</strong>
              <ul>
                <li>明确指定输出格式（如 JSON、Markdown）</li>
                <li>提供示例帮助 LLM 理解要求</li>
                <li>使用清晰的结构和分隔符</li>
                <li>强调关键要求（如字数限制、格式规范）</li>
              </ul>
            </div>
          </a-card>

          <!-- 答案生成提示词 -->
          <a-card title="✍️ 答案生成系统提示词" size="small">
            <template #extra>
              <a-tooltip title="重置为默认值">
                <a-button size="small" @click="resetPrompt('answer_generation_system')">
                  <template #icon>
                    <UndoOutlined/>
                  </template>
                </a-button>
              </a-tooltip>
            </template>

            <a-textarea
                v-model:value="promptsConfig.answer_generation_system"
                :rows="12"
                placeholder="请输入系统提示词..."
                :disabled="savingPrompts"
                style="font-family: 'Consolas', 'Monaco', monospace; font-size: 13px;"
            />
          </a-card>

          <!-- 操作按钮 -->
          <a-form-item>
            <a-space>
              <a-button type="primary" @click="savePromptsConfig" :loading="savingPrompts">
                <template #icon>
                  <SaveOutlined/>
                </template>
                保存配置
              </a-button>
              <a-button @click="loadPromptsConfig">
                <template #icon>
                  <ReloadOutlined/>
                </template>
                刷新
              </a-button>
            </a-space>
          </a-form-item>
        </a-space>
      </a-tab-pane>

    </a-tabs>
  </div>
</template>

<script setup>
import {onMounted, ref} from 'vue'
import {crawlerApi, promptsApi, systemConfigApi} from '../services'
import {message, Modal} from 'ant-design-vue'
import dayjs from 'dayjs'
import {ReloadOutlined, SaveOutlined, UndoOutlined} from '@ant-design/icons-vue'

// 当前激活的tab
const activeTab = ref('crawler')

// 爬虫配置
const crawlerConfig = ref({
  sitemap_url: '',
  root_url: '',
  timeout: 30,
  max_urls: null,
  delay_between_requests: 0.5,
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
  model_max_output_tokens: '',
  rerank_enabled: false,
  rerank_model_name: 'rerank-sf'
})

// 邮件配置
const emailConfig = ref({
  smtp_server: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  smtp_test_user: ''
})

// Redis配置
const redisConfig = ref({
  host: 'localhost',
  port: 6379,
  password: ''
})

// 定时任务配置
const schedulerConfig = ref({
  time: null,
  hour: 22,
  minute: 0
})

// 提示词配置
const promptsConfig = ref({
  question_extraction_system: '',
  answer_generation_system: ''
})

// 内容处理配置
const contentConfig = ref({
  max_content_length_per_page: 2000,
  chunk_size: 512,
  chunk_overlap: 128,
  separators: ['\n\n', '\n', '。', '！', '？', '.', '!', '?', ' '],
  chunking_mode: 'semantic',
  max_chunks_per_page: 100,
  min_chunk_length: 100
})

// 默认提示词
const defaultPrompts = {
  question_extraction_system: `你是一位资深技术面试官和技术内容专家。请仔细阅读提供的网页内容，提取高质量的技术面试问题。

## 核心任务：
1. **完整理解**：将网页内容视为一个完整的技术主题，不要过度拆分
2. **问题识别**：识别内容中的核心技术问题（可能是1个主要问题，或2-3个相关问题）
3. **详细解答**：为每个问题生成完整、详细的答案，包含所有技术细节
4. **智能分类**：根据问题类型和难度进行分类

## 重要原则：
- 如果内容是围绕一个主要技术点展开的（如“反射的应用场景”），请将其作为一个整体问题处理
- 不要将文章中的每个小知识点都拆分成独立的问题
- 答案应该详尽，包含原文中的所有技术细节和代码示例
- 答案长度至少300字以上，确保内容充实

## ⚠️ 答案格式要求（非常重要）：
**必须使用 Markdown 格式编写答案**，以提高可读性：
- 使用 \`## 标题\` 分隔不同部分
- 使用 **粗体** 强调关键概念
- 使用 \`代码块\` 包裹代码示例（指定语言，如 \`\`\`python）
- 使用 - 列表 或 1. 有序列表 组织要点
- 使用 > 引用块 标注重要说明
- 适当使用空行分隔段落

## 输出格式（必须是纯JSON数组）：
[
  {
    "title": "问题标题，必须是一个完整的疑问句",
    "answer": "基于原文的详细技术答案（至少300字，使用Markdown格式，包含所有技术细节和代码示例）",
    "source_url": "来源网页URL",
    "tags": ["相关技术标签", "如Python", "算法"],
    "importance_score": 0.8,
    "difficulty": "medium",
    "category": "问题分类"
  }
]`,

  answer_generation_system: `你是一个专业的技术面试官和解答者。请详细解答以下技术问题。

要求：
1. 答案必须使用 Markdown 格式
2. 包含代码示例时使用代码块
3. 结构清晰，分点说明
4. 答案长度至少300字`
}

// 状态
const savingCrawler = ref(false)
const savingLlm = ref(false)
const savingRedis = ref(false)
const savingEmail = ref(false)
const savingScheduler = ref(false)
const testingEmail = ref(false)
const savingPrompts = ref(false)
const savingContent = ref(false)

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

      // 加载模型配置（包含 Rerank）
      if (config.llm) {
        llmConfig.value = config.llm
        // 隐藏API Key的中间部分
        if (llmConfig.value.openai_api_key && llmConfig.value.openai_api_key.length > 10) {
          llmConfig.value.openai_api_key = llmConfig.value.openai_api_key
        }
      }

      // 兼容旧的 Rerank 配置结构
      if (config.rerank && !config.llm?.rerank_enabled) {
        llmConfig.value.rerank_enabled = config.rerank.enabled
        llmConfig.value.rerank_model_name = config.rerank.model_name
      }

      // 加载邮件配置
      if (config.email) {
        emailConfig.value = config.email
        // 不再隐藏密码，由 a-input-password 组件自动处理
      }

      // 加载 Redis 配置
      if (config.redis) {
        redisConfig.value = config.redis
        // 不再隐藏密码，由 a-input-password 组件自动处理
      }

      // 加载定时任务配置
      if (config.scheduler) {
        const {hour, minute} = config.scheduler
        schedulerConfig.value.time = dayjs().hour(hour).minute(minute)
        schedulerConfig.value.hour = hour
        schedulerConfig.value.minute = minute
      }

      // 加载内容处理配置
      if (config.content) {
        contentConfig.value = config.content
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

// 保存模型配置（包含 Rerank）
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
  if (!redisConfig.value.host) {
    message.warning('请填写Redis服务器地址')
    return
  }

  savingRedis.value = true
  try {
    const res = await systemConfigApi.updateRedisConfig(redisConfig.value)
    if (res.status === 'success') {
      message.success('Redis配置保存成功')
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

// 加载提示词配置
const loadPromptsConfig = async () => {
  try {
    const res = await promptsApi.getPrompts()
    if (res.status === 'success') {
      promptsConfig.value = res.prompts

      // 如果配置为空，使用默认值
      if (!promptsConfig.value.question_extraction_system) {
        promptsConfig.value.question_extraction_system = defaultPrompts.question_extraction_system
      }
      if (!promptsConfig.value.answer_generation_system) {
        promptsConfig.value.answer_generation_system = defaultPrompts.answer_generation_system
      }
    }
  } catch (error) {
    message.error('加载提示词配置失败')
    console.error(error)
  }
}

// 保存提示词配置
const savePromptsConfig = async () => {
  savingPrompts.value = true
  try {
    const res = await promptsApi.updatePrompts(promptsConfig.value)
    if (res.status === 'success') {
      message.success('提示词配置已保存并生效')
    }
  } catch (error) {
    message.error('保存失败: ' + (error.response?.data?.detail || error.message))
    console.error(error)
  } finally {
    savingPrompts.value = false
  }
}

// 重置提示词
const resetPrompt = (key) => {
  Modal.confirm({
    title: '确认重置',
    content: `确定要将“${key === 'question_extraction_system' ? '面试题提取' : '答案生成'}”提示词重置为默认值吗？`,
    okText: '确认',
    cancelText: '取消',
    onOk: () => {
      promptsConfig.value[key] = defaultPrompts[key]
      message.success('已重置为默认值，请点击“保存配置”应用更改')
    }
  })
}

// 保存内容处理配置
const saveContentConfig = async () => {
  savingContent.value = true
  try {
    const res = await systemConfigApi.updateContentConfig(contentConfig.value)
    if (res.status === 'success') {
      message.success('内容处理配置保存成功')
    }
  } catch (error) {
    message.error('保存内容处理配置失败')
    console.error(error)
  } finally {
    savingContent.value = false
  }
}

onMounted(() => {
  loadSystemConfig()
  loadPromptsConfig()
})
</script>

<style scoped>
.settings-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
}

.prompt-tips {
  margin-top: 12px;
  padding: 12px;
  background-color: #f6f8fa;
  border-radius: 6px;
  font-size: 13px;
}

.prompt-tips strong {
  color: #24292e;
}

.prompt-tips ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
  color: #586069;
}

.prompt-tips li {
  margin-bottom: 4px;
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
