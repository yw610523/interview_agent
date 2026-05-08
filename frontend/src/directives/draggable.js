/**
 * 可拖拽和缩放的模态框指令
 * 使用方法: v-draggable
 * 功能:
 * - 拖动标题栏移动模态框
 * - 拖动右下角调整大小
 */
export default {
  mounted(el) {
    // 等待模态框完全渲染
    setTimeout(() => {
      const modalWrap = el.querySelector('.ant-modal-wrap')
      const modal = el.querySelector('.ant-modal')
      const modalHeader = el.querySelector('.ant-modal-header')
      
      if (!modalWrap || !modal || !modalHeader) return

      // 设置模态框为绝对定位
      modal.style.position = 'absolute'
      modal.style.transition = 'none'
      
      // 初始化位置(居中)
      const wrapRect = modalWrap.getBoundingClientRect()
      const modalRect = modal.getBoundingClientRect()
      let posX = (wrapRect.width - modalRect.width) / 2
      let posY = Math.max(0, (wrapRect.height - modalRect.height) / 2)
      
      modal.style.left = posX + 'px'
      modal.style.top = posY + 'px'
      
      let isDragging = false
      let startX = 0
      let startY = 0

      // 拖拽功能
      const dragStart = (e) => {
        // 只允许在标题栏拖动,但不能是按钮
        if (e.target.closest('button') || e.target.closest('.ant-modal-close')) return
        
        isDragging = true
        startX = e.clientX - posX
        startY = e.clientY - posY
        modalWrap.style.cursor = 'move'
        e.preventDefault()
      }

      const drag = (e) => {
        if (!isDragging) return
        
        posX = e.clientX - startX
        posY = e.clientY - startY
        
        // 限制在可视区域内
        const wrapRect = modalWrap.getBoundingClientRect()
        const modalRect = modal.getBoundingClientRect()
        
        posX = Math.max(0, Math.min(posX, wrapRect.width - modalRect.width))
        posY = Math.max(0, Math.min(posY, wrapRect.height - modalRect.height))
        
        modal.style.left = posX + 'px'
        modal.style.top = posY + 'px'
      }

      const dragEnd = () => {
        isDragging = false
        modalWrap.style.cursor = ''
      }

      // 绑定拖拽事件到标题栏
      modalHeader.addEventListener('mousedown', dragStart)
      document.addEventListener('mousemove', drag)
      document.addEventListener('mouseup', dragEnd)

      // 暴露给 resize 功能使用
      el._modal = modal
      el._getPos = () => ({ x: posX, y: posY })
      el._setPos = (x, y) => {
        posX = x
        posY = y
        modal.style.left = posX + 'px'
        modal.style.top = posY + 'px'
      }

      // 保存清理函数
      el._cleanupDrag = () => {
        modalHeader.removeEventListener('mousedown', dragStart)
        document.removeEventListener('mousemove', drag)
        document.removeEventListener('mouseup', dragEnd)
      }
    }, 100)
  },
  
  beforeUnmount(el) {
    // 清理事件监听器
    if (el._cleanupDrag) {
      el._cleanupDrag()
    }
  }
}
