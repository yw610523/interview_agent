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
            <a-space style="width: 100%">
              <a-input 
                v-model:value="crawlerConfig.sitemap_url" 
                placeholder="例如: javaguide.cn"
                @blur="handleSitemapUrlBlur"
                style="flex: 1"
              />
              <div v-if="sitemapTestStatus" style="min-width: 80px">
                <a-tag v-if="sitemapTestStatus === 'success'" color="success">
                  <CheckOutlined /> 可访问
                </a-tag>
                <a-tag v-else-if="sitemapTestStatus === 'error'" color="error">
                  <CloseOutlined /> 无法访问
                </a-tag>
                <a-spin v-else-if="sitemapTestStatus === 'testing'" size="small" />
              </div>
              <a-button 
                v-if="sitemapTestStatus === 'error'" 
                size="small" 
                @click="openUrlInBrowser(buildSitemapUrl())"
              >
                打开链接
              </a-button>
            </a-space>
          </a-form-item>

          <a-form-item label="根路径前缀">
            <a-input 
              v-model:value="crawlerConfig.root_url" 
              placeholder="例如: /blog, /docs（留空表示根目录）"
              @blur="handleRootUrlBlur"
            />
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
            <div v-if="loadingPaths" style="margin-bottom: 8px; color: #8c8c8c; font-size: 12px">
              <a-spin size="small" /> 正在加载路径...
            </div>
            <div v-else-if="totalUrls" style="margin-bottom: 8px; color: #8c8c8c; font-size: 12px">
              已加载 {{ totalUrls }} 个URL的路径结构
            </div>
            <a-tree
              v-if="sitemapPaths.length > 0"
              v-model:checkedKeys="crawlerConfig.url_include_patterns"
              :tree-data="sitemapPaths"
              checkable
              :default-expand-all="false"
              :max-height="300"
              style="border: 1px solid #d9d9d9; border-radius: 4px; padding: 8px"
            />
            <a-select
              v-else
              v-model:value="crawlerConfig.url_include_patterns"
              mode="tags"
              placeholder="手动输入路径模式，如: /docs/"
              style="width: 100%"
            />
            <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px">
              提示：选择的路径会自动添加 /* 通配符，匹配该路径下的所有URL
            </div>
          </a-form-item>

          <a-form-item label="URL排除规则">
            <a-tree
              v-if="sitemapPaths.length > 0"
              v-model:checkedKeys="crawlerConfig.url_exclude_patterns"
              :tree-data="sitemapPaths"
              checkable
              :default-expand-all="false"
              :max-height="300"
              style="border: 1px solid #d9d9d9; border-radius: 4px; padding: 8px"
            />
            <a-select
              v-else
              v-model:value="crawlerConfig.url_exclude_patterns"
              mode="tags"
              placeholder="手动输入路径模式，如: /admin/"
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

      <!-- 模型配置（分组：OpenAI、Embedding、Rerank） -->
      <a-tab-pane key="llm" tab="🤖 模型配置">
        <a-space direction="vertical" style="width: 100%" size="large">
          <!-- OpenAI 组 -->
          <a-card title="🔵 OpenAI 配置" :bordered="false" size="small">
            <a-form
                :model="llmConfig"
                :label-col="{ span: 8 }"
                :wrapper-col="{ span: 16 }"
            >
              <a-form-item label="API Key">
                <a-input v-model:value="llmConfig.openai_api_key" placeholder="输入API Key" type="password"/>
              </a-form-item>

              <a-form-item label="API Base URL">
                <a-input v-model:value="llmConfig.openai_api_base" placeholder="例如: https://api.openai.com/v1"/>
              </a-form-item>

              <a-form-item label="模型名称">
                <a-input v-model:value="llmConfig.openai_model" placeholder="例如: gpt-4o-mini"/>
              </a-form-item>

              <a-form-item label="最大输入Token">
                <a-input v-model:value="llmConfig.model_max_input_tokens" placeholder="留空使用默认值"/>
              </a-form-item>

              <a-form-item label="最大输出Token">
                <a-input v-model:value="llmConfig.model_max_output_tokens" placeholder="留空使用默认值"/>
              </a-form-item>
            </a-form>
          </a-card>

          <!-- Embedding 组 -->
          <a-card title="🟢 Embedding 配置" :bordered="false" size="small">
            <a-form
                :model="llmConfig"
                :label-col="{ span: 8 }"
                :wrapper-col="{ span: 16 }"
            >
              <a-form-item label="Embedding模型">
                <a-input v-model:value="llmConfig.openai_embedding_model" placeholder="例如: BAAI/bge-m3"/>
              </a-form-item>

              <a-form-item label="Embedding维度">
                <a-input-number v-model:value="llmConfig.embedding_dimension" :min="128" :max="4096"/>
              </a-form-item>
            </a-form>
          </a-card>

          <!-- Rerank 组 -->
          <a-card title="🟣 Rerank 配置" :bordered="false" size="small">
            <a-form
                :model="llmConfig"
                :label-col="{ span: 8 }"
                :wrapper-col="{ span: 16 }"
            >
              <a-form-item label="启用 Rerank">
                <a-switch v-model:checked="llmConfig.rerank_enabled"/>
                <span style="margin-left: 8px; color: #8c8c8c;">{{
                    llmConfig.rerank_enabled ? '已启用' : '未启用'
                  }}</span>
              </a-form-item>

              <a-form-item label="Rerank 模型名称" v-if="llmConfig.rerank_enabled">
                <a-input v-model:value="llmConfig.rerank_model_name" placeholder="例如: BAAI/bge-reranker-v2-m3"/>
              </a-form-item>

              <a-form-item label="API Key" v-if="llmConfig.rerank_enabled">
                <a-input v-model:value="llmConfig.rerank_api_key" placeholder="留空则复用 LLM API Key" type="password"/>
                <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px;">
                  如果留空，将使用 EMBEDDING_API_KEY 或 OPENAI_API_KEY
                </div>
              </a-form-item>

              <a-form-item label="API Base URL" v-if="llmConfig.rerank_enabled">
                <a-input v-model:value="llmConfig.rerank_api_base" placeholder="例如: https://api.siliconflow.cn/v1"/>
                <div style="color: #8c8c8c; font-size: 12px; margin-top: 4px;">
                  如果留空，将使用环境变量 RERANK_API_BASE
                </div>
              </a-form-item>
            </a-form>
          </a-card>

          <!-- 保存/重置按钮 -->
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
        </a-space>
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
            <a-input v-model:value="emailConfig.smtp_password" placeholder="SMTP密码或授权码" type="password"/>
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
        <a-form
            :model="contentConfig"
            :label-col="{ span: 8 }"
            :wrapper-col="{ span: 16 }"
        >
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
import {onMounted, ref, watch} from 'vue'
import {crawlerApi, promptsApi, systemConfigApi} from '../services'
import {message, Modal} from 'ant-design-vue'
import dayjs from 'dayjs'
import {CheckOutlined, CloseOutlined, ReloadOutlined, SaveOutlined, UndoOutlined} from '@ant-design/icons-vue'

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
  openai_embedding_model: 'BAAI/bge-m3',
  embedding_dimension: 1024,
  model_max_input_tokens: '',
  model_max_output_tokens: '',
  rerank_enabled: false,
  rerank_model_name: 'BAAI/bge-reranker-v2-m3',
  rerank_api_key: '',
  rerank_api_base: ''
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

// 提示词配置
const promptsConfig = ref({
  question_extraction_system: '',
  answer_generation_system: ''
})

// 内容处理配置
const contentConfig = ref({
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
- 使用 \`代码块\` 包裹代码示例（指定语言，如 \`\`\`python\`)
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
const savingEmail = ref(false)
const savingScheduler = ref(false)
const testingEmail = ref(false)
const savingPrompts = ref(false)
const savingContent = ref(false)

// URL连通性检测状态
const sitemapTestStatus = ref('') // '', 'testing', 'success', 'error'
let sitemapTestTimer = null

// Sitemap路径树相关
const sitemapPaths = ref([])
const totalUrls = ref(0)
const loadingPaths = ref(false)

// 原始配置副本（用于对比变更）
const originalConfigs = ref({
  llm: null,
  email: null,
  redis: null
})

// 深拷贝函数
const deepClone = (obj) => {
  if (obj === null || typeof obj !== 'object') return obj
  if (Array.isArray(obj)) return obj.map(item => deepClone(item))
  const cloned = {}
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      cloned[key] = deepClone(obj[key])
    }
  }
  return cloned
}

// 检测对象变更，只返回修改过的字段
const getChangedFields = (current, original) => {
  if (!original) return current // 如果没有原始值，返回全部
  
  const changes = {}
  for (const key in current) {
    if (current.hasOwnProperty(key)) {
      // 深度比较
      if (JSON.stringify(current[key]) !== JSON.stringify(original[key])) {
        changes[key] = current[key]
      }
    }
  }
  return changes
}

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
      }

      // 兼容旧的 Rerank 配置结构
      if (config.rerank && !config.llm?.rerank_enabled) {
        llmConfig.value.rerank_enabled = config.rerank.enabled
        llmConfig.value.rerank_model_name = config.rerank.model_name
      }

      // 保存原始配置副本（用于后续对比变更）
      originalConfigs.value.llm = deepClone(config.llm)

      // 加载邮件配置
      if (config.email) {
        emailConfig.value = config.email
        // 保存原始配置副本（用于后续对比变更）
        originalConfigs.value.email = deepClone(config.email)
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
    // 只发送变更的字段
    const changedFields = getChangedFields(llmConfig.value, originalConfigs.value.llm)
    
    // 如果没有变更，提示用户
    if (Object.keys(changedFields).length === 0) {
      message.info('没有检测到配置变更')
      return
    }
    
    console.log('检测到变更的字段:', Object.keys(changedFields))
    
    const res = await systemConfigApi.updateLlmConfig(changedFields)
    if (res.status === 'success') {
      message.success('模型配置保存成功')
      // 更新原始配置副本
      originalConfigs.value.llm = deepClone(llmConfig.value)
    }
  } catch (error) {
    message.error('保存模型配置失败')
    console.error(error)
  } finally {
    savingLlm.value = false
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
    // 只发送变更的字段
    const changedFields = getChangedFields(emailConfig.value, originalConfigs.value.email)
    
    // 如果没有变更，提示用户
    if (Object.keys(changedFields).length === 0) {
      message.info('没有检测到配置变更')
      return
    }
    
    console.log('检测到变更的字段:', Object.keys(changedFields))
    
    const res = await systemConfigApi.updateEmailConfig(changedFields)
    if (res.status === 'success') {
      message.success('邮件配置保存成功')
      // 更新原始配置副本
      originalConfigs.value.email = deepClone(emailConfig.value)
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

// 构建完整的Sitemap URL（用于测试）
const buildSitemapUrl = () => {
  let url = crawlerConfig.value.sitemap_url
  if (!url) return ''
  
  // 如果URL不包含协议，默认添加https://
  if (!url.startsWith(('http://', 'https://'))) {
    url = `https://${url}`
  }
  
  // 添加根路径前缀
  const rootUrl = crawlerConfig.value.root_url || ''
  
  // 添加sitemap.xml路径
  return `${url}${rootUrl}/sitemap.xml`
}

// 测试Sitemap URL连通性（内部方法，无防抖）
const testSitemapUrlInternal = async () => {
  const sitemapUrl = buildSitemapUrl()
  if (!sitemapUrl) {
    sitemapTestStatus.value = ''
    return false
  }
  
  sitemapTestStatus.value = 'testing'
  
  try {
    const res = await crawlerApi.testUrlConnectivity(sitemapUrl)
    if (res.accessible) {
      sitemapTestStatus.value = 'success'
      return true
    } else {
      sitemapTestStatus.value = 'error'
      return false
    }
  } catch (error) {
    sitemapTestStatus.value = 'error'
    console.error('测试URL连通性失败:', error)
    return false
  }
}

// 测试Sitemap URL连通性（带防抖，用于实时输入）
const testSitemapUrl = async () => {
  const sitemapUrl = buildSitemapUrl()
  if (!sitemapUrl) {
    sitemapTestStatus.value = ''
    return
  }
  
  // 防抖：清除之前的定时器
  if (sitemapTestTimer) {
    clearTimeout(sitemapTestTimer)
  }
  
  // 延迟500ms后执行测试，避免频繁请求
  sitemapTestTimer = setTimeout(async () => {
    sitemapTestStatus.value = 'testing'
    
    try {
      const res = await crawlerApi.testUrlConnectivity(sitemapUrl)
      if (res.accessible) {
        sitemapTestStatus.value = 'success'
      } else {
        sitemapTestStatus.value = 'error'
      }
    } catch (error) {
      sitemapTestStatus.value = 'error'
      console.error('测试URL连通性失败:', error)
    }
  }, 500)
}

// Sitemap URL失去焦点时：测试连通性 + 加载路径树
const handleSitemapUrlBlur = async () => {
  // 先测试连通性（无防抖，立即执行）
  const accessible = await testSitemapUrlInternal()
  
  // 如果连通性测试通过，加载路径树
  if (accessible) {
    await loadSitemapPaths()
  }
}

// 根路径失去焦点时：重新加载路径树
const handleRootUrlBlur = async () => {
  // 重新测试连通性（root_url变化后完整URL也变了）
  const accessible = await testSitemapUrlInternal()
  
  // 如果连通性测试通过，加载路径树
  if (accessible) {
    await loadSitemapPaths()
  }
}

// 在浏览器中打开URL
const openUrlInBrowser = (url) => {
  if (!url) return
  
  // 如果URL不包含协议，默认添加https://
  if (!url.startsWith(('http://', 'https://'))) {
    url = `https://${url}`
  }
  
  window.open(url, '_blank')
}

// 递归解码路径树中的 title（用于展示）
const decodePathTree = (nodes) => {
  if (!nodes) return []
  
  return nodes.map(node => {
    const decodedNode = { ...node }
    try {
      // 解码 title，保留原始 key 不变
      if (node.title) {
        decodedNode.title = decodeURIComponent(node.title)
      }
    } catch (e) {
      // 解码失败时保留原样
      console.warn('路径解码失败:', node.title, e)
    }
    
    // 递归处理子节点
    if (node.children && node.children.length > 0) {
      decodedNode.children = decodePathTree(node.children)
    }
    
    return decodedNode
  })
}

// 加载Sitemap路径树
const loadSitemapPaths = async () => {
  // 如果没有配置sitemap_url，不加载
  if (!crawlerConfig.value.sitemap_url) {
    sitemapPaths.value = []
    totalUrls.value = 0
    return
  }
  
  loadingPaths.value = true
  try {
    // 传递当前输入框的值（而不是已保存的配置）
    const res = await crawlerApi.getSitemapPaths(
      crawlerConfig.value.sitemap_url,
      crawlerConfig.value.root_url
    )
    console.log('Sitemap API响应:', res)
    if (res.status === 'success') {
      let paths = res.paths || []
      totalUrls.value = res.total_urls || 0
      
      console.log('原始路径数据:', paths)
      console.log('总URL数:', totalUrls.value)
      
      // 解码中文路径（用于界面展示）
      paths = decodePathTree(paths)
      console.log('解码后路径数据:', paths)
      
      // 如果配置了root_url，过滤路径树
      const rootUrl = crawlerConfig.value.root_url
      if (rootUrl && rootUrl.trim()) {
        const normalizedRoot = rootUrl.startsWith('/') ? rootUrl : '/' + rootUrl
        console.log('应用root_url过滤:', normalizedRoot)
        paths = filterPathsByRoot(paths, normalizedRoot)
        console.log('过滤后路径数据:', paths)
      }
      
      sitemapPaths.value = paths
      
      if (sitemapPaths.value.length === 0 && totalUrls.value > 0) {
        message.info('Sitemap已解析，但未发现可过滤的路径')
      }
    }
  } catch (error) {
    console.error('加载路径失败:', error)
    // URL无法访问时，清空include和exclude
    crawlerConfig.value.url_include_patterns = []
    crawlerConfig.value.url_exclude_patterns = []
    sitemapPaths.value = []
    totalUrls.value = 0
    message.warning('无法访问Sitemap，已清空URL过滤规则')
  } finally {
    loadingPaths.value = false
  }
}

// 根据root_url过滤路径树
const filterPathsByRoot = (paths, rootPath) => {
  const filtered = []
  
  for (const path of paths) {
    // 如果当前路径以rootPath开头
    if (path.key === rootPath || path.key.startsWith(rootPath + '/')) {
      // 复制节点
      const node = { ...path }
      
      // 如果有子节点，递归过滤
      if (node.children && node.children.length > 0) {
        node.children = filterPathsByRoot(node.children, rootPath)
      }
      
      // 如果是rootPath本身或者是其子路径，添加到结果
      filtered.push(node)
    }
  }
  
  return filtered
}

// 监听sitemap_url和root_url变化，自动刷新路径树
let refreshTimer = null
let isInitialLoad = true  // 标记是否正在初始化加载
// 注意：已移除实时 watch 监听，改为在 blur 事件中触发，避免输入过程中频繁请求

// 清理不符合root_url的过滤规则
const cleanupFilterRules = (rootUrl) => {
  if (!rootUrl || !rootUrl.trim()) return
  
  const normalizedRoot = rootUrl.startsWith('/') ? rootUrl : '/' + rootUrl
  
  // 过滤include_patterns
  const oldInclude = crawlerConfig.value.url_include_patterns || []
  crawlerConfig.value.url_include_patterns = oldInclude.filter(pattern => {
    // 如果pattern以rootPath开头或者是其子路径，保留
    return pattern === normalizedRoot || pattern.startsWith(normalizedRoot + '/')
  })
  
  // 过滤exclude_patterns
  const oldExclude = crawlerConfig.value.url_exclude_patterns || []
  crawlerConfig.value.url_exclude_patterns = oldExclude.filter(pattern => {
    return pattern === normalizedRoot || pattern.startsWith(normalizedRoot + '/')
  })
  
  // 如果有规则被清理，提示用户
  if (oldInclude.length !== crawlerConfig.value.url_include_patterns.length ||
      oldExclude.length !== crawlerConfig.value.url_exclude_patterns.length) {
    message.info('已根据新的根路径清理过滤规则')
  }
}

onMounted(() => {
  loadSystemConfig()
  loadPromptsConfig()
  // 延迟加载路径树，确保配置已加载
  setTimeout(() => {
    isInitialLoad = false  // 初始化完成，允许 watch 监听
    loadSitemapPaths()
  }, 500)
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
