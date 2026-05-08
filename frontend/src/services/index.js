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

  // 更新 Rerank 配置
  updateRerankConfig(config) {
    return apiClient.put('/rerank-config', config)
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
  searchQuestions(query, limit = 10, tags, difficulty, category, searchMode = 'semantic', useRerank = false) {
    const params = new URLSearchParams()
    params.append('query', query)
    params.append('limit', limit)
    params.append('search_mode', searchMode)
    params.append('use_rerank', useRerank)
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
  },

  // 智能推荐题目
  getRecommendedQuestions(limit = 20, excludeMastered = true, useRerank = false) {
    return apiClient.get(`/questions/recommended?limit=${limit}&exclude_mastered=${excludeMastered}&use_rerank=${useRerank}`)
  }
}

// 用户反馈相关 API (RESTful)
export const feedbackApi = {
  // 提交反馈
  submitFeedback(questionId, { masteryLevel, isFavorite, isWrongBook }) {
    const params = new URLSearchParams()
    if (masteryLevel !== undefined && masteryLevel !== null) {
      params.append('mastery_level', masteryLevel)
    }
    if (isFavorite !== undefined && isFavorite !== null) {
      params.append('is_favorite', isFavorite)
    }
    if (isWrongBook !== undefined && isWrongBook !== null) {
      params.append('is_wrong_book', isWrongBook)
    }
    return apiClient.post(`/questions/${questionId}/feedback?${params.toString()}`)
  },

  // 获取题目反馈
  getFeedback(questionId) {
    return apiClient.get(`/questions/${questionId}/feedback`)
  },

  // 获取收藏列表
  getFavorites() {
    return apiClient.get('/users/me/favorites')
  },

  // 取消收藏
  removeFromFavorites(questionId) {
    return apiClient.delete(`/users/me/favorites/${questionId}`)
  },

  // 获取错题本
  getWrongBook() {
    return apiClient.get('/users/me/wrong-books')
  },

  // 从错题本移除
  removeFromWrongBook(questionId) {
    return apiClient.delete(`/users/me/wrong-books/${questionId}`)
  }
}
