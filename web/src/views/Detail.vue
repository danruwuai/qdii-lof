<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PremiumBadge from '../components/PremiumBadge.vue'
import { getFundDetail } from '../api'
import { useWatchStore } from '../stores'

const route = useRoute()
const router = useRouter
const store = useWatchStore()

const fund = ref(null)
const loading = ref(true)
const activeChartTab = ref('premium')

onMounted(async () => {
  const code = route.params.code
  try {
    fund.value = await getFundDetail(code)
    store.load()
  } catch (e) {
    console.error('Failed to load detail:', e)
  }
  loading.value = false
})

function formatNum(n) {
  if (n === null || n === undefined) return '--'
  return typeof n === 'number' ? n.toFixed(4) : n
}

function formatPct(n) {
  if (n === null || n === undefined) return '--'
  return typeof n === 'number' ? (n > 0 ? `+${n.toFixed(2)}%` : `${n.toFixed(2)}%`) : n
}

function formatDate(d) {
  if (!d) return '--'
  return String(d)
}
</script>

<template>
  <div class="detail-page">
    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="!fund || fund.code === '未知'" class="error">
      基金不存在
    </div>

    <div v-else class="content">
      <!-- Header -->
      <div class="fund-header">
        <div class="fund-code">{{ fund.code }}</div>
        <div class="fund-name">{{ fund.name }}</div>
        <div class="fund-tags">
          <span class="tag" v-if="fund.fund_type">{{ fund.fund_type }}</span>
          <span class="tag" v-if="fund.tracking_region">{{ fund.tracking_region }}</span>
        </div>
      </div>

      <!-- Premium rate hero -->
      <div class="premium-hero">
        <div class="label">实时溢价率</div>
        <div class="value">
          <PremiumBadge :rate="fund.premium?.premium_rate" size="large" />
        </div>
        <div class="sub">
          <span>现价: {{ formatNum(fund.market_price) }}</span>
          <span>净值: {{ formatNum(fund.nav) }}</span>
        </div>
      </div>

      <!-- Key metrics -->
      <div class="metrics-grid">
        <div class="metric">
          <div class="label">涨跌幅</div>
          <div class="value" :class="{ up: fund.change_pct > 0, down: fund.change_pct < 0 }">
            {{ formatPct(fund.change_pct) }}
          </div>
        </div>
        <div class="metric">
          <div class="label">净值</div>
          <div class="value">{{ formatNum(fund.nav) }}</div>
        </div>
        <div class="metric">
          <div class="label">净值日期</div>
          <div class="value">{{ formatDate(fund.nav_date) }}</div>
        </div>
        <div class="metric">
          <div class="label">成交额</div>
          <div class="value">{{ fund.volume ? (fund.volume / 10000).toFixed(2) + '万' : '--' }}</div>
        </div>
        <div class="metric">
          <div class="label">申购状态</div>
          <div class="value" :class="{ disabled: !fund.can_subscribe }">
            {{ fund.can_subscribe ? '开放' : '暂停' }}
          </div>
        </div>
        <div class="metric" v-if="fund.daily_limit !== null">
          <div class="label">日限额</div>
          <div class="value warn">{{ fund.daily_limit }}元</div>
        </div>
      </div>

      <!-- Watch button -->
      <button class="watch-action" @click="store.isWatching(fund.code) ? store.remove(fund.code) : store.add(fund.code)">
        {{ store.isWatching(fund.code) ? '❤️ 已监控' : '🤍 加入监控' }}
      </button>

      <!-- Tabs: 持仓 / 溢价历史 -->
      <div class="section-tabs">
        <button :class="{ active: activeChartTab === 'premium' }" @click="activeChartTab = 'premium'">
          溢价历史
        </button>
        <button :class="{ active: activeChartTab === 'holdings' }" @click="activeChartTab = 'holdings'">
          前十大持仓
        </button>
      </div>

      <!-- Premium history -->
      <div v-if="activeChartTab === 'premium'" class="section">
        <div class="section-title">溢价率历史 (最近{{ fund.premium_history?.length || 0 }}条)</div>
        <div class="history-list">
          <div
            v-for="(item, i) in fund.premium_history"
            :key="i"
            class="history-item"
          >
            <span class="time">{{ item.time }}</span>
            <PremiumBadge :rate="item.premium_rate" size="small" />
            <span class="price">价{{ item.market_price }}</span>
            <span class="nav">净{{ item.nav_value }}</span>
          </div>
          <div v-if="!fund.premium_history?.length" class="empty">暂无历史数据</div>
        </div>
      </div>

      <!-- Holdings -->
      <div v-if="activeChartTab === 'holdings'" class="section">
        <div class="section-title">前十大持仓 (最新)</div>
        <div class="holdings-list">
          <div
            v-for="h in fund.holdings"
            :key="h.asset_code"
            class="holding-item"
          >
            <span class="asset-name">{{ h.asset_name }}</span>
            <span class="asset-type">{{ h.asset_type }}</span>
            <span class="weight">{{ h.weight }}%</span>
          </div>
          <div v-if="!fund.holdings?.length" class="empty">暂无持仓数据</div>
        </div>
      </div>

      <!-- Risk tags -->
      <div class="risk-info" v-if="fund.risk_tags?.length">
        <div class="section-title">风险提示</div>
        <div class="risk-tags">
          <span v-for="tag in fund.risk_tags" :key="tag" class="risk-tag">{{ tag }}</span>
        </div>
      </div>

      <!-- Disclaimer -->
      <div class="disclaimer">
        数据仅供参考，不构成投资建议。QDII基金净值有T+2延迟，溢价率存在波动风险。
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-page {
  padding: 16px;
}

.loading, .error {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.fund-header {
  text-align: center;
  margin-bottom: 16px;
}

.fund-code {
  font-size: 20px;
  font-weight: 700;
  color: #1890ff;
}

.fund-name {
  font-size: 18px;
  font-weight: 600;
  margin-top: 4px;
}

.fund-tags {
  margin-top: 8px;
  display: flex;
  justify-content: center;
  gap: 8px;
}

.tag {
  background: #f0f0f0;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 4px;
  color: #666;
}

.premium-hero {
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  border-radius: 12px;
  padding: 24px 20px;
  text-align: center;
  color: #fff;
  margin-bottom: 16px;
}

.premium-hero .label {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 8px;
}

.premium-hero .value {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 8px;
}

.premium-hero .sub {
  font-size: 13px;
  opacity: 0.85;
  display: flex;
  justify-content: center;
  gap: 24px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric {
  background: #fff;
  border-radius: 8px;
  padding: 14px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.metric .label {
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
}

.metric .value {
  font-size: 16px;
  font-weight: 600;
}

.metric .value.up { color: #ff4d4f; }
.metric .value.down { color: #52c41a; }
.metric .value.warn { color: #fa8c16; }
.metric .value.disabled { color: #999; }

.watch-action {
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 20px;
}

.watch-action:active {
  opacity: 0.8;
}

.section-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  border-bottom: 1px solid #e8e8e8;
}

.section-tabs button {
  padding: 10px 16px;
  border: none;
  background: none;
  font-size: 15px;
  color: #999;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.section-tabs button.active {
  color: #1890ff;
  border-bottom-color: #1890ff;
}

.section {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #333;
}

.history-list, .holdings-list {
  max-height: 400px;
  overflow-y: auto;
}

.history-item, .holding-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
  font-size: 13px;
}

.history-item:last-child, .holding-item:last-child {
  border-bottom: none;
}

.history-item .time { color: #999; width: 130px; }
.history-item .price { color: #666; }
.history-item .nav { color: #666; }

.holding-item .asset-name { flex: 1; }
.holding-item .asset-type { color: #999; font-size: 12px; }
.holding-item .weight { font-weight: 600; color: #1890ff; }

.risk-info {
  background: #fffbe6;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.risk-tag {
  display: inline-block;
  background: #fff;
  border: 1px solid #ffd591;
  color: #fa8c16;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  margin-right: 8px;
  margin-bottom: 8px;
}

.disclaimer {
  font-size: 12px;
  color: #999;
  text-align: center;
  padding: 16px;
  line-height: 1.6;
}

.empty {
  text-align: center;
  padding: 20px;
  color: #999;
}

@media (max-width: 480px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .premium-hero .sub {
    flex-direction: column;
    gap: 4px;
  }
}
</style>
