<template>
  <div class="home-view">
    <a-row :gutter="[24, 24]">
      <!-- 欢迎卡片 -->
      <a-col :span="24">
        <a-card title="🎯 欢迎使用 Interview AI Agent" :bordered="false">
          <p style="font-size: 16px; line-height: 1.8;">
            这是一个基于大模型的智能面试题管理系统，支持自动爬取技术文档、AI识别面试题、向量存储和语义搜索。
          </p>
          <a-divider />
          <a-space direction="vertical" size="large" style="width: 100%;">
            <div>
              <h3>✨ 主要功能</h3>
              <ul style="line-height: 2;">
                <li><strong>智能爬虫</strong>：支持批量爬取和单页爬取，自动识别面试问题</li>
                <li><strong>配置管理</strong>：在前端界面直接配置爬虫参数</li>
                <li><strong>面试题生成</strong>：随机生成指定类型、数量的面试题</li>
                <li><strong>答案展示</strong>：点击按钮查看答案，支持展开/收起</li>
              </ul>
            </div>
          </a-space>
        </a-card>
      </a-col>

      <!-- 快速操作卡片 -->
      <a-col :xs="24" :md="12">
        <a-card title="🚀 快速开始" :bordered="false">
          <a-space direction="vertical" size="middle" style="width: 100%;">
            <a-button type="primary" size="large" block @click="$router.push('/crawler')">
              进入爬虫管理
            </a-button>
            <a-button type="primary" size="large" block @click="$router.push('/questions')">
              生成面试题
            </a-button>
          </a-space>
        </a-card>
      </a-col>

      <!-- 统计信息卡片 -->
      <a-col :xs="24" :md="12">
        <a-card title="📊 系统状态" :bordered="false">
          <a-spin :spinning="loading">
            <a-descriptions bordered :column="1" size="small">
              <a-descriptions-item label="面试题总数">
                <a-tag color="blue">{{ questionCount }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="上次爬取时间">
                {{ lastCrawlTime || '暂无' }}
              </a-descriptions-item>
              <a-descriptions-item label="上次爬取问题数">
                {{ lastCrawlQuestions || 0 }}
              </a-descriptions-item>
            </a-descriptions>
          </a-spin>
          <a-button 
            type="link" 
            @click="loadStats" 
            style="margin-top: 12px;"
          >
            刷新统计
          </a-button>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { questionApi, crawlerApi } from '../services'
import { message } from 'ant-design-vue'

const loading = ref(false)
const questionCount = ref(0)
const lastCrawlTime = ref('')
const lastCrawlQuestions = ref(0)

// 加载统计数据
const loadStats = async () => {
  loading.value = true
  try {
    // 获取面试题总数
    const countRes = await questionApi.getQuestionCount()
    questionCount.value = countRes.count || 0

    // 获取爬虫状态
    const statusRes = await crawlerApi.getCrawlStatus()
    if (statusRes.last_crawl) {
      lastCrawlTime.value = statusRes.last_crawl.timestamp
      lastCrawlQuestions.value = statusRes.last_crawl.parsed_questions || 0
    }
  } catch (error) {
    message.error('加载统计数据失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.home-view {
  max-width: 1200px;
  margin: 0 auto;
}

h3 {
  margin-bottom: 16px;
}

ul {
  padding-left: 20px;
}
</style>
