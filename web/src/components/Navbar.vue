<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const navItems = [
  { name: 'index', path: '/', label: '列表', icon: '📋' },
  { name: 'watchlist', path: '/monitor', label: '监控', icon: '👁️' },
  { name: 'alerts', path: '/alert', label: '提醒', icon: '🔔' },
  { name: 'settings', path: '/setting', label: '设置', icon: '⚙️' },
]

const activeIndex = computed(() => {
  if (route.name === 'index') return 0
  if (route.name === 'watchlist') return 1
  if (route.name === 'alerts') return 2
  if (route.name === 'settings') return 3
  return -1
})
</script>

<template>
  <nav class="navbar">
    <router-link
      v-for="(item, i) in navItems"
      :key="item.name"
      :to="item.path"
      :class="{ active: activeIndex === i }"
    >
      <span class="icon">{{ item.icon }}</span>
      <span class="label">{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped>
.navbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-around;
  align-items: center;
  height: 56px;
  background: #fff;
  border-top: 1px solid #e8e8e8;
  padding-bottom: env(safe-area-inset-bottom);
  z-index: 100;
}

@media (min-width: 768px) {
  .navbar {
    left: calc(50% - 384px);
    right: calc(50% - 384px);
    max-width: 768px;
  }
}

.navbar a {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  color: #999;
  font-size: 12px;
  transition: color 0.2s;
}

.navbar a.active {
  color: #1890ff;
}

.navbar .icon {
  font-size: 20px;
  margin-bottom: 2px;
}

.navbar .label {
  font-size: 11px;
}
</style>
