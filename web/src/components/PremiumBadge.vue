<script setup>
defineProps({
  rate: { type: Number, required: true },
  size: { type: String, default: 'default' }
})

const color = computed(() => {
  if (rate > 10) return '#ff4d4f'
  if (rate > 5) return '#fa8c16'
  if (rate > 0) return '#faad14'
  return '#52c41a'
})

const text = computed(() => {
  if (rate === null || rate === undefined) return '--'
  return rate > 0 ? `+${rate.toFixed(2)}%` : `${rate.toFixed(2)}%`
})

const sizeClass = computed(() => `size-${size}`)
</script>

<template>
  <span class="premium-badge" :class="sizeClass" :style="{ color }">
    {{ text }}
  </span>
</template>

<style scoped>
.premium-badge {
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(0,0,0,0.04);
}

.premium-badge.size-small { font-size: 12px; padding: 1px 6px; }
.premium-badge.size-default { font-size: 14px; }
.premium-badge.size-large { font-size: 18px; }
</style>
