/**
 * 可拖拽模态框指令
 * 使用方法: v-draggable
 */
export default {
  mounted(el, binding) {
    const modalHeader = el.querySelector('.ant-modal-header')
    const modal = el.querySelector('.ant-modal')
    
    if (!modalHeader || !modal) return

    let isDragging = false
    let currentX
    let currentY
    let initialX
    let initialY
    let xOffset = 0
    let yOffset = 0

    const dragStart = (e) => {
      // 只允许在标题栏拖动
      if (e.target !== modalHeader && !modalHeader.contains(e.target)) return
      
      // 如果点击的是按钮，不拖动
      if (e.target.closest('button')) return

      initialX = e.clientX - xOffset
      initialY = e.clientY - yOffset

      if (e.target === modalHeader || modalHeader.contains(e.target)) {
        isDragging = true
      }
    }

    const dragEnd = () => {
      initialX = currentX
      initialY = currentY

      isDragging = false
    }

    const drag = (e) => {
      if (isDragging) {
        e.preventDefault()

        currentX = e.clientX - initialX
        currentY = e.clientY - initialY

        xOffset = currentX
        yOffset = currentY

        modal.style.transform = `translate(${currentX}px, ${currentY}px)`
      }
    }

    // 保存事件处理器以便后续移除
    el._dragHandlers = { dragStart, dragEnd, drag }

    document.addEventListener('mousedown', dragStart)
    document.addEventListener('mouseup', dragEnd)
    document.addEventListener('mousemove', drag)
  },
  
  beforeUnmount(el) {
    // 清理事件监听器
    if (el._dragHandlers) {
      document.removeEventListener('mousedown', el._dragHandlers.dragStart)
      document.removeEventListener('mouseup', el._dragHandlers.dragEnd)
      document.removeEventListener('mousemove', el._dragHandlers.drag)
    }
  }
}
