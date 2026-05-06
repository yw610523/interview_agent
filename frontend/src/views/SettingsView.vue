<template>
  <div class="settings-view">
    <a-row :gutter="[24, 24]">
      <!-- 爬虫配置 -->
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
    </a-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { crawlerApi } from '../services'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'

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

// 加载配置
const loadConfig = async () => {
  try {
    const res = await crawlerApi.getConfig()
    if (res.status === 'success') {
      configForm.value = res.config
      
      // 如果有定时任务配置，加载它
      try {
        const schedulerRes = await crawlerApi.getSchedulerConfig()
        if (schedulerRes.status === 'success' && schedulerRes.config) {
          const { hour, minute } = schedulerRes.config
          schedulerTime.value = dayjs().hour(hour).minute(minute)
        }
      } catch (error) {
        console.warn('加载定时任务配置失败:', error)
      }
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

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.settings-view {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
