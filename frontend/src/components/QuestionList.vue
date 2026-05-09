<template>
  <div class="question-list">
    <a-list
      :data-source="questions"
      :pagination="pagination ? {
        pageSize: pageSize,
        showSizeChanger: true,
        showTotal: (total) => `共 ${total} 道题目`
      } : false"
    >
      <template #renderItem="{ item, index }">
        <a-list-item class="question-item" @click="$emit('itemClick', index)">
          <a-list-item-meta>
            <template #title>
              <div class="question-title">{{ item.title }}</div>
            </template>
          </a-list-item-meta>
        </a-list-item>
      </template>
    </a-list>
  </div>
</template>

<script setup>
defineProps({
  questions: {
    type: Array,
    required: true,
    default: () => []
  },
  pagination: {
    type: Boolean,
    default: true
  },
  pageSize: {
    type: Number,
    default: 20
  }
})

defineEmits(['itemClick'])
</script>

<style scoped>
.question-list {
  min-height: 200px;
}

.question-item {
  cursor: pointer;
  transition: all 0.3s;
  border-bottom: 1px solid #f0f0f0;
  padding: 12px 16px;
}

.question-item:hover {
  background-color: #fafafa;
  transform: translateX(4px);
}

.question-title {
  font-size: 15px;
  font-weight: 500;
  color: #262626;
  margin-bottom: 8px;
}

.question-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 移动端隐藏标签和操作按钮 */
@media (max-width: 768px) {
  .desktop-only {
    display: none !important;
  }
  
  .question-item {
    padding: 16px;
  }
  
  .question-title {
    font-size: 16px;
    margin-bottom: 0;
  }
}
</style>
