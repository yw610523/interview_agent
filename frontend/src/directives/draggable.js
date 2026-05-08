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

      // 设置模态框为可定位
      modal.style.position = 'relative'
      modal.style.transition = 'none'
      
      // 初始化位置
      let posX = 0
      let posY = 0
      let isDragging = false
      let startX = 0
      let startY = 0

      // 拖拽功能
      const dragStart = (e) => {
        // 只允许在标题栏拖动，但不能是按钮
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
        
        modal.style.transform = `translate(${posX}px, ${posY}px)`
      }

      const dragEnd = () => {
        isDragging = false
        modalWrap.style.cursor = ''
      }

      // 绑定拖拽事件到标题栏
      modalHeader.addEventListener('mousedown', dragStart)
      document.addEventListener('mousemove', drag)
      document.addEventListener('mouseup', dragEnd)

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
