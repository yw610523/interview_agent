import apiClient from './api'

export const crawlerApi = {
  // 获取爬虫配置
  getConfig() {
    return apiClient.get('/config')
  },

  // 更新爬虫配置
  updateConfig(config) {
    return apiClient.put('/config', config)
  },

  // 获取定时任务配置
  getSchedulerConfig() {
    return apiClient.get('/scheduler-config')
  },

  // 更新定时任务配置
  updateSchedulerConfig(hour, minute) {
    return apiClient.put(`/scheduler-config?hour=${hour}&minute=${minute}`)
  },

  // 手动触发批量爬取（同步，会阻塞）
  triggerCrawl() {
    return apiClient.get('/crawl/run')
  },

  // 异步触发批量爬取（立即返回任务ID）
  triggerCrawlAsync() {
    return apiClient.post('/crawl/run-async')
  },

  // 获取任务状态
  getTaskStatus(taskId) {
    return apiClient.get(`/crawl/task/${taskId}`)
  },

  // 停止任务
  stopTask(taskId) {
    return apiClient.post(`/crawl/stop/${taskId}`)
  },

  // 获取所有任务
  getAllTasks() {
    return apiClient.get('/crawl/tasks')
  },

  // 获取爬虫状态
  getCrawlStatus() {
    return apiClient.get('/crawl/status')
  },

  // 单页爬取
  crawlSinglePage(url) {
    return apiClient.post(`/crawl/single-page?url=${encodeURIComponent(url)}`)
  }
}

export const systemConfigApi = {
  // 获取系统配置
  getSystemConfig() {
    return apiClient.get('/system-config')
  },

  // 更新模型配置
  updateLlmConfig(config) {
    return apiClient.put('/llm-config', config)
  },

  // 更新Redis配置
  updateRedisConfig(redisUrl) {
    return apiClient.put('/redis-config', { redis_url: redisUrl })
  },

  // 更新邮件配置
  updateEmailConfig(config) {
    return apiClient.put('/email-config', config)
  },

  // 测试邮件发送
  testEmail() {
    return apiClient.post('/test-email')
  }
}

export const questionApi = {
  // 批量生成面试题
  generateBatch(count, difficulty, category, tags) {
    const params = new URLSearchParams()
    params.append('count', count)
    if (difficulty) params.append('difficulty', difficulty)
    if (category) params.append('category', category)
    if (tags && tags.length > 0) {
      tags.forEach(tag => params.append('tags', tag))
    }
    return apiClient.get(`/questions/generate-batch?${params.toString()}`)
  },

  // 搜索面试题
  searchQuestions(query, limit = 10, tags, difficulty, category) {
    const params = new URLSearchParams()
    params.append('query', query)
    params.append('limit', limit)
    if (tags && tags.length > 0) {
      tags.forEach(tag => params.append('tags', tag))
    }
    if (difficulty && difficulty.length > 0) {
      difficulty.forEach(d => params.append('difficulty', d))
    }
    if (category && category.length > 0) {
      category.forEach(c => params.append('category', c))
    }
    return apiClient.get(`/questions/search?${params.toString()}`)
  },

  // 获取所有面试题
  getAllQuestions(limit = 100, offset = 0) {
    return apiClient.get(`/questions?limit=${limit}&offset=${offset}`)
  },

  // 获取面试题总数
  getQuestionCount() {
    return apiClient.get('/questions/count')
  },

  // 删除面试题
  deleteQuestion(questionId) {
    return apiClient.delete(`/questions/${questionId}`)
  }
}
