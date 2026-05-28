<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useWatchStore } from '../stores'

const props = defineProps({
  fund: { type: Object, required: true },
  compact: { type: Boolean, default: false }
})

const router = useRouter()
const store = useWatchStore()

function goToDetail() {
  router.push(`/detail/${props.fund.code}`)
}

const premiumRate = computed(() => props.fund.premium?.premium_rate ?? null)
const isHigh = computed(() => premiumRate.value !== null && premiumRate.value > 10)
const isMedium = computed(() => premiumRate.value !== null && premiumRate.value > 5 && premiumRate.value <= 10)
const isDiscount = computed(() => premiumRate.value !== null && premiumRate.value < 0)

function premiumColor() {
  if (premiumRate.value === null) return '#999'
  if (premiumRate.value > 5) return '#ff4d4f'
  if (premiumRate.value > 0) return '#fa8c16'
  return '#52c41a'
}

function formatNum(n) {
  if (n === null || n === undefined) return '--'
  return typeof n === 'number' ? n.toFixed(3) : n
}

function formatPct(n) {
  if (n === null || n === undefined) return '--'
  return typeof n === 'number' ? (n > 0 ? `+${n.toFixed(2)}%` : `${n.toFixed(2)}%`) : n
}
</script>

<template>
  <div class="fund-card" :class="{ compact }" @click="goToDetail" style="cursor: pointer;">
    <div class="card-header">
      <div class="fund-info">
        <span class="code">{{ fund.code }}</span>
        <span class="name">{{ fund.name }}</span>
        <span class="type-tag" v-if="fund.fund_type">{{ fund.fund_type }}</span>
      </div>
      <button class="watch-btn" @click="store.isWatching(fund.code) ? store.remove(fund.code) : store.add(fund.code)">
        {{ store.isWatching(fund.code) ? '❤️' : '🤍' }}
      </button>
    </div>

    <div class="card-body" v-if="!compact">
      <div class="price-row">
        <div class="price-item">
          <span class="label">现价</span>
          <span class="value">{{ formatNum(fund.market_price) }}</span>
        </div>
        <div class="price-item">
          <span class="label">涨跌</span>
          <span class="value change" :class="{ up: fund.change_pct > 0, down: fund.change_pct < 0 }">
            {{ formatPct(fund.change_pct) }}
          </span>
        </div>
        <div class="price-item">
          <span class="label">净值</span>
          <span class="value">{{ formatNum(fund.nav) }}</span>
          <span class="nav-date" v-if="fund.nav_date">{{ fund.nav_date }}</span>
          <span class="nav-accuracy" v-if="fund.premium?.nav_accuracy">({{ fund.premium.nav_accuracy }})</span>
        </div>
        <div class="price-item premium">
          <span class="label">溢价率</span>
          <span class="value" :style="{ color: premiumColor() }">
            {{ premiumRate !== null ? (premiumRate > 0 ? `+${premiumRate.toFixed(2)}%` : `${premiumRate.toFixed(2)}%`) : '--' }}
          </span>
          <span class="premium-note" v-if="fund.premium?.is_estimated" title="基于T+2净值估算">⚠️估算</span>
        </div>
      </div>

      <div class="meta-row">
        <span class="meta-item">
          <span class="label">申购</span>
          <span class="value" :class="{ disabled: !fund.can_subscribe }">
            {{ fund.can_subscribe ? '开放' : '暂停' }}
          </span>
        </span>
        <span class="meta-item" v-if="fund.daily_limit !== null && fund.daily_limit < 1000">
          <span class="label">限额</span>
          <span class="value warn">{{ fund.daily_limit }}元</span>
        </span>
        <span class="meta-item" v-if="fund.underlying_index">
          <span class="label">跟踪</span>
          <span class="value">{{ fund.underlying_index }}</span>
        </span>
      </div>

      <div class="arbitrage-tag" v-if="fund.arbitrage_type">
        <span class="tag" :class="fund.arbitrage_type">
          {{ fund.arbitrage_type }}
          <span v-if="fund.net_profit !== null">(净利{{ fund.net_profit }}%)</span>
        </span>
        <span class="risk-tags" v-if="fund.risk_tags?.length">
          {{ fund.risk_tags.join(' · ') }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fund-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.fund-card.compact {
  padding: 12px 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.fund-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.code {
  font-weight: 600;
  color: #1890ff;
  font-size: 15px;
}

.name {
  font-weight: 500;
  font-size: 15px;
}

.type-tag {
  background: #e6f7ff;
  color: #1890ff;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
}

.watch-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 4px;
}

.price-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.price-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.price-item .label {
  font-size: 11px;
  color: #999;
}

.price-item .value {
  font-size: 15px;
  font-weight: 600;
}

.price-item .value.change.up {
  color: #ff4d4f;
}

.price-item .value.change.down {
  color: #52c41a;
}

.price-item.premium .value {
  font-size: 16px;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.meta-item .label {
  color: #999;
}

.meta-item .value {
  font-weight: 500;
}

.meta-item .value.disabled {
  color: #999;
}

.meta-item .value.warn {
  color: #fa8c16;
}

.arbitrage-tag {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tag {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 4px;
  font-weight: 500;
}

.tag.溢价套利 { background: #fff1f0; color: #ff4d4f; }
.tag.持有者卖出 { background: #fff7e6; color: #fa8c16; }
.tag.折价埋伏 { background: #f6ffed; color: #52c41a; }
.tag.低溢价埋伏 { background: #e6f7ff; color: #1890ff; }
.tag.溢价回落 { background: #fffbe6; color: #faad14; }

.risk-tags {
  font-size: 11px;
  color: #999;
}

@media (max-width: 480px) {
  .price-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
