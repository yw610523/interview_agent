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
                <li><strong>配置管理</strong>：在系统设置页面配置爬虫参数和定时任务</li>
                <li><strong>面试题生成</strong>：随机生成指定类型、数量的面试题</li>
                <li><strong>语义搜索</strong>：在首页快速搜索面试题，支持关键词检索</li>
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
            <a-button size="large" block @click="$router.push('/settings')">
              系统设置
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

      <!-- 快速搜索卡片 -->
      <a-col :span="24">
        <a-card title="🔍 快速搜索面试题" :bordered="false">
          <a-form layout="inline" @submit.prevent="handleSearch">
            <a-form-item label="关键词" style="flex: 1;">
              <a-input
                v-model:value="searchQuery"
                placeholder="输入关键词搜索面试题，例如：Python、算法、数据库..."
                allow-clear
                @press-enter="handleSearch"
                style="width: 100%; min-width: 300px;"
              >
                <template #prefix>
                  <SearchOutlined />
                </template>
              </a-input>
            </a-form-item>
            
            <a-form-item label="数量">
              <a-input-number 
                v-model:value="searchLimit" 
                :min="1" 
                :max="50" 
                style="width: 100px;"
              />
            </a-form-item>

            <a-form-item>
              <a-button type="primary" @click="handleSearch" :loading="searching">
                🔍 搜索
              </a-button>
            </a-form-item>
          </a-form>

          <!-- 搜索结果 -->
          <div v-if="searchResults.length > 0" style="margin-top: 24px;">
            <a-divider>搜索结果 ({{ searchResults.length }})</a-divider>
            <a-list
              item-layout="vertical"
              :data-source="searchResults"
              :pagination="{
                pageSize: 5,
                showSizeChanger: false,
                showTotal: (total) => `共 ${total} 条结果`
              }"
            >
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-card hoverable style="width: 100%; margin-bottom: 12px;">
                    <template #title>
                      <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 16px;">{{ item.title }}</span>
                        <a-space>
                          <a-tag color="blue">{{ item.difficulty || 'medium' }}</a-tag>
                          <a-tag v-if="item.category" color="green">{{ item.category }}</a-tag>
                          <a-tag v-for="tag in (item.tags || [])" :key="tag" color="purple">
                            {{ tag }}
                          </a-tag>
                        </a-space>
                      </div>
                    </template>
                    
                    <MarkdownRenderer :content="item.answer" />
                    
                    <a-divider style="margin: 12px 0;" />
                    
                    <div style="font-size: 13px; color: #666;">
                      <strong>来源:</strong> 
                      <a :href="item.source_url" target="_blank" style="margin-left: 8px;">
                        {{ item.source_url }}
                      </a>
                    </div>
                  </a-card>
                </a-list-item>
              </template>
            </a-list>
          </div>

          <!-- 空状态提示 -->
          <a-empty 
            v-else-if="hasSearched" 
            description="没有找到相关的面试题，请尝试其他关键词" 
            style="margin-top: 24px;"
          />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { questionApi, crawlerApi } from '../services'
import { message } from 'ant-design-vue'
import { SearchOutlined } from '@ant-design/icons-vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'

const loading = ref(false)
const questionCount = ref(0)
const lastCrawlTime = ref('')
const lastCrawlQuestions = ref(0)

// 搜索相关
const searchQuery = ref('')
const searchLimit = ref(10)
const searching = ref(false)
const searchResults = ref([])
const hasSearched = ref(false)

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

// 处理搜索
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    message.warning('请输入搜索关键词')
    return
  }

  searching.value = true
  hasSearched.value = true
  searchResults.value = []

  try {
    const res = await questionApi.searchQuestions(
      searchQuery.value,
      searchLimit.value
    )
    
    searchResults.value = res.results || []
    
    if (searchResults.value.length === 0) {
      message.info('没有找到相关的面试题')
    } else {
      message.success(`找到 ${res.total} 条相关结果`)
    }
  } catch (error) {
    message.error('搜索失败')
    console.error(error)
  } finally {
    searching.value = false
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
