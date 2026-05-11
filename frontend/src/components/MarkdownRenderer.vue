<template>
  <div class="markdown-renderer" ref="containerRef" v-html="renderedHtml"></div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import mermaid from 'mermaid'
import 'highlight.js/styles/github.css'

const props = defineProps({
  content: {
    type: String,
    default: ''
  }
})

const containerRef = ref(null)

// 初始化 mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
})

// 初始化 markdown-it，配置代码高亮和 Mermaid 支持
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true,  // 支持换行符转换为 <br>
  highlight: function (str, lang) {
    // 如果是 mermaid 代码块，返回特殊容器（使用 escapeHtml 确保安全）
    if (lang === 'mermaid') {
      return `<div class="mermaid">${md.utils.escapeHtml(str)}</div>`
    }
    
    if (lang && hljs.getLanguage(lang)) {
      try {
        return '<pre class="hljs"><code>' +
               hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
               '</code></pre>'
      } catch (__) {}
    }
    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>'
  }
})

// 渲染 Markdown 内容
const renderedHtml = computed(() => {
  if (!props.content) return ''
  
  let content = props.content
  
  // 如果内容不包含任何 Markdown 标记，尝试智能转换
  if (!content.includes('#') && !content.includes('**') && !content.includes('```')) {
    // 纯文本，进行基本的格式化
    content = autoFormatPlainText(content)
  }
  
  return md.render(content)
})

// 渲染 Mermaid 图表
const renderMermaid = async () => {
  if (!containerRef.value) return
  
  try {
    // 找到所有待渲染的 mermaid 节点
    const elements = containerRef.value.querySelectorAll('.mermaid')
    if (elements.length === 0) return

    for (const el of elements) {
      // 跳过已经渲染过的（带有 data-processed 属性）
      if (el.getAttribute('data-processed')) continue
      
      const content = el.textContent.trim()
      if (!content) continue
      
      const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`
      
      try {
        // 使用 mermaid.render 渲染
        const { svg } = await mermaid.render(id, content)
        el.innerHTML = svg
        el.setAttribute('data-processed', 'true')
      } catch (error) {
        console.error('Mermaid 语法错误:', error)
        el.innerHTML = `<pre style="color:red">Error: ${error.message}</pre>`
      }
    }
  } catch (error) {
    console.error('Mermaid 渲染失败:', error)
  }
}

// 监听内容变化
watch(() => props.content, async () => {
  await nextTick()
  // 延迟一小会儿确保 v-html 已经完全挂载到 DOM
  setTimeout(() => {
    renderMermaid()
  }, 0)
}, { immediate: true })

// 自动格式化纯文本为基本 Markdown
const autoFormatPlainText = (text) => {
  // 1. 将明显的标题转换为 Markdown 标题
  // 匹配 "一、" "二、" 或 "1." "2." 开头的行
  text = text.replace(/^(\d+\.\s)(.+)$/gm, '## $2')
  text = text.replace(/^([一二三四五六七八九十]+、)(.+)$/gm, '## $2')
  
  // 2. 确保段落之间有空行（单个换行符转换为双换行）
  const newline = String.fromCharCode(10) // \n
  const regex = new RegExp(newline + '([^' + newline + '])', 'g')
  text = text.replace(regex, newline + newline + '$1')
  
  return text
}
</script>

<style scoped>
.markdown-renderer {
  line-height: 1.8;
  font-size: 14px;
}

/* 标题样式 */
.markdown-renderer :deep(h1),
.markdown-renderer :deep(h2),
.markdown-renderer :deep(h3),
.markdown-renderer :deep(h4),
.markdown-renderer :deep(h5),
.markdown-renderer :deep(h6) {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
  color: #24292e;
}

.markdown-renderer :deep(h1) {
  font-size: 2em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-renderer :deep(h2) {
  font-size: 1.5em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-renderer :deep(h3) {
  font-size: 1.25em;
}

/* 段落样式 */
.markdown-renderer :deep(p) {
  margin-top: 0;
  margin-bottom: 16px;
}

/* 列表样式 */
.markdown-renderer :deep(ul),
.markdown-renderer :deep(ol) {
  margin-top: 0;
  margin-bottom: 16px;
  padding-left: 2em;
}

.markdown-renderer :deep(li) {
  margin-top: 0.25em;
}

/* 代码块样式 */
.markdown-renderer :deep(pre.hljs) {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 6px;
  margin-bottom: 16px;
}

.markdown-renderer :deep(code) {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(27, 31, 35, 0.05);
  border-radius: 6px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}

.markdown-renderer :deep(pre.hljs code) {
  padding: 0;
  margin: 0;
  font-size: 100%;
  background-color: transparent;
  border-radius: 0;
}

/* Mermaid 图表容器样式 */
.markdown-renderer :deep(.mermaid) {
  display: flex;
  justify-content: center;
  margin: 16px 0;
  padding: 16px;
  background-color: #f6f8fa;
  border-radius: 6px;
  overflow-x: auto;
}

/* 引用块样式 */
.markdown-renderer :deep(blockquote) {
  padding: 0 1em;
  color: #6a737d;
  border-left: 0.25em solid #dfe2e5;
  margin: 0 0 16px 0;
}

/* 链接样式 */
.markdown-renderer :deep(a) {
  color: #0366d6;
  text-decoration: none;
}

.markdown-renderer :deep(a:hover) {
  text-decoration: underline;
}

/* 表格样式 */
.markdown-renderer :deep(table) {
  border-spacing: 0;
  border-collapse: collapse;
  margin-bottom: 16px;
  width: 100%;
}

.markdown-renderer :deep(table th),
.markdown-renderer :deep(table td) {
  padding: 6px 13px;
  border: 1px solid #dfe2e5;
}

.markdown-renderer :deep(table tr) {
  background-color: #fff;
  border-top: 1px solid #c6cbd1;
}

.markdown-renderer :deep(table tr:nth-child(2n)) {
  background-color: #f6f8fa;
}

/* 图片样式 */
.markdown-renderer :deep(img) {
  max-width: 100%;
  box-sizing: border-box;
}

/* 水平线样式 */
.markdown-renderer :deep(hr) {
  height: 0.25em;
  padding: 0;
  margin: 24px 0;
  background-color: #e1e4e8;
  border: 0;
}
</style>
