<script setup>
import { onMounted } from 'vue'
import FundCard from '../components/FundCard.vue'
import { useWatchStore } from '../stores'

const store = useWatchStore()

onMounted(() => {
  store.load()
})
</script>

<template>
  <div class="watchlist-page">
    <h1 class="title">监控列表</h1>

    <div v-if="!store.loaded" class="loading">加载中...</div>

    <div v-else-if="store.items.length === 0" class="empty">
      <div class="empty-icon">👁️</div>
      <div class="empty-text">暂无监控基金</div>
      <div class="empty-hint">返回列表添加关注的基金</div>
    </div>

    <div v-else class="fund-list">
      <FundCard v-for="item in store.items" :key="item.code" :fund="item" />
    </div>
  </div>
</template>

<style scoped>
.watchlist-page {
  padding: 16px;
}

.title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #333;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
}

.empty {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-text {
  font-size: 18px;
  color: #666;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 13px;
  color: #999;
}

.fund-list {
  /* padding handled by parent */
}
</style>
