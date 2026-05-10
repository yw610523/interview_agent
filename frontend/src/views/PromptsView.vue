<template>
  <div class="prompts-view">
    <a-page-header
        title="📝 提示词配置管理"
        sub-title="管理和编辑 LLM 提示词，自定义面试题生成规则"
    >
      <template #extra>
        <a-space>
          <a-button @click="loadPrompts">
            <template #icon>
              <ReloadOutlined/>
            </template>
            刷新
          </a-button>
          <a-button type="primary" @click="handleSave" :loading="saving">
            <template #icon>
              <SaveOutlined/>
            </template>
            保存配置
          </a-button>
        </a-space>
      </template>
    </a-page-header>

    <a-spin :spinning="loading">
      <a-row :gutter="[16, 16]">
        <!-- 面试题提取提示词 -->
        <a-col :span="24">
          <a-card title="🎯 面试题提取系统提示词" :bordered="false">
            <template #extra>
              <a-tooltip title="重置为默认值">
                <a-button size="small" @click="resetToDefault('question_extraction_system')">
                  <template #icon>
                    <UndoOutlined/>
                  </template>
                </a-button>
              </a-tooltip>
            </template>

            <a-alert
                message="提示：此提示词用于从网页内容中提取面试题和答案"
                type="info"
                show-icon
                style="margin-bottom: 16px"
            />

            <a-textarea
                v-model:value="prompts.question_extraction_system"
                :rows="25"
                placeholder="请输入系统提示词..."
                :disabled="saving"
                @change="markAsModified"
                style="font-family: 'Consolas', 'Monaco', monospace; font-size: 13px;"
            />

            <div class="prompt-tips">
              <h4>💡 提示词编写建议：</h4>
              <ul>
                <li>明确指定输出格式（如 JSON、Markdown）</li>
                <li>提供示例帮助 LLM 理解要求</li>
                <li>使用清晰的结构和分隔符</li>
                <li>强调关键要求（如字数限制、格式规范）</li>
              </ul>
            </div>
          </a-card>
        </a-col>

        <!-- 答案生成提示词 -->
        <a-col :span="24">
          <a-card title="✍️ 答案生成系统提示词" :bordered="false">
            <template #extra>
              <a-tooltip title="重置为默认值">
                <a-button size="small" @click="resetToDefault('answer_generation_system')">
                  <template #icon>
                    <UndoOutlined/>
                  </template>
                </a-button>
              </a-tooltip>
            </template>

            <a-alert
                message="提示：此提示词用于单独生成或优化答案内容"
                type="info"
                show-icon
                style="margin-bottom: 16px"
            />

            <a-textarea
                v-model:value="prompts.answer_generation_system"
                :rows="15"
                placeholder="请输入系统提示词..."
                :disabled="saving"
                @change="markAsModified"
                style="font-family: 'Consolas', 'Monaco', monospace; font-size: 13px;"
            />
          </a-card>
        </a-col>
      </a-row>
    </a-spin>

    <!-- 保存确认对话框 -->
    <a-modal
        v-model:open="saveConfirmVisible"
        title="⚠️ 确认保存"
        ok-text="确认保存"
        cancel-text="取消"
        @ok="confirmSave"
    >
      <p>保存后将立即生效，新的爬虫任务将使用更新后的提示词。</p>
      <p style="color: #ff4d4f;">注意：修改提示词不会影响已生成的题目。</p>
    </a-modal>
  </div>
</template>

<script setup>
import {onMounted, ref} from 'vue'
import {message, Modal} from 'ant-design-vue'
import {ReloadOutlined, SaveOutlined, UndoOutlined} from '@ant-design/icons-vue'
import {promptsApi} from '../services'

// 状态
const loading = ref(false)
const saving = ref(false)
const saveConfirmVisible = ref(false)
const isModified = ref(false)

// 提示词数据
const prompts = ref({
  question_extraction_system: '',
  answer_generation_system: ''
})

// 默认提示词（用于重置）
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

// 加载提示词配置
const loadPrompts = async () => {
  loading.value = true
  try {
    const res = await promptsApi.getPrompts()
    if (res.status === 'success') {
      prompts.value = res.prompts

      // 如果配置为空，使用默认值
      if (!prompts.value.question_extraction_system) {
        prompts.value.question_extraction_system = defaultPrompts.question_extraction_system
      }
      if (!prompts.value.answer_generation_system) {
        prompts.value.answer_generation_system = defaultPrompts.answer_generation_system
      }
    }
  } catch (error) {
    message.error('加载提示词配置失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 标记为已修改
const markAsModified = () => {
  isModified.value = true
}

// 重置为默认值
const resetToDefault = (key) => {
  Modal.confirm({
    title: '确认重置',
    content: `确定要将"${key === 'question_extraction_system' ? '面试题提取' : '答案生成'}"提示词重置为默认值吗？`,
    okText: '确认',
    cancelText: '取消',
    onOk: () => {
      prompts.value[key] = defaultPrompts[key]
      markAsModified()
      message.success('已重置为默认值')
    }
  })
}

// 保存配置
const handleSave = () => {
  if (!isModified.value) {
    message.info('没有修改需要保存')
    return
  }

  saveConfirmVisible.value = true
}

// 确认保存
const confirmSave = async () => {
  saving.value = true
  try {
    const res = await promptsApi.updatePrompts(prompts.value)
    if (res.status === 'success') {
      message.success('提示词配置已保存并生效')
      isModified.value = false
      saveConfirmVisible.value = false
    }
  } catch (error) {
    message.error('保存失败: ' + (error.response?.data?.detail || error.message))
    console.error(error)
  } finally {
    saving.value = false
  }
}

// 组件挂载时加载数据
onMounted(() => {
  loadPrompts()
})
</script>

<style scoped>
.prompts-view {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.prompt-tips {
  margin-top: 16px;
  padding: 12px;
  background-color: #f6f8fa;
  border-radius: 6px;
  font-size: 13px;
}

.prompt-tips h4 {
  margin: 0 0 8px 0;
  color: #24292e;
}

.prompt-tips ul {
  margin: 0;
  padding-left: 20px;
  color: #586069;
}

.prompt-tips li {
  margin-bottom: 4px;
}

:deep(.ant-textarea) {
  border-radius: 6px;
}

:deep(.ant-textarea:focus-within) {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}
</style>
