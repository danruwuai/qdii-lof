<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import FundCard from '../components/FundCard.vue'
import { listFunds, searchFunds, getTabCounts } from '../api'
import { useWatchStore } from '../stores'

const store = useWatchStore()

// Tabs
const tabs = [
  { key: 'all', label: '全部' },
  { key: 'watchlist', label: '监控' },
  { key: 'arbitrage', label: '套利' },
  { key: 'QDII-ETF', label: 'QDII-ETF' },
  { key: 'QDII-LOF', label: 'QDII-LOF' },
]

const activeTab = ref('all')
const searchQuery = ref('')
const searchResults = ref([])
const showSearch = ref(false)

// Filters
const sortField = ref('premium_rate')
const sortDir = ref('desc')
const premiumFilter = ref('')
const subscribeFilter = ref('')

// Pagination
const funds = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)

// Tab counts
const tabCounts = ref({})

async function loadTabCounts() {
  try {
    tabCounts.value = await getTabCounts()
  } catch (e) {
    console.error('Failed to load tab counts:', e)
  }
}

async function loadFunds() {
  loading.value = true
  try {
    const params = {
      tab: activeTab.value === 'all' ? undefined : activeTab.value,
      sort: sortField.value,
      sort_dir: sortDir.value,
      page: page.value,
      page_size: pageSize,
    }
    if (premiumFilter.value) params.premium_level = premiumFilter.value
    if (subscribeFilter.value) params.can_subscribe = subscribeFilter.value === 'yes'

    const data = await listFunds(params)
    funds.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    console.error('Failed to load funds:', e)
    funds.value = []
    total.value = 0
  }
  loading.value = false
}

async function handleSearch() {
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    showSearch.value = false
    return
  }
  try {
    searchResults.value = await searchFunds(searchQuery.value)
  } catch (e) {
    searchResults.value = []
  }
}

function selectFund(code) {
  searchQuery.value = ''
  searchResults.value = []
  showSearch.value = false
  window.location.href = `/detail/${code}`
}

function tabLabel(tab) {
  const count = tabCounts.value[tab.key]
  return count !== undefined ? `${tab.label}(${count})` : tab.label
}

watch([activeTab, sortField, sortDir, premiumFilter, subscribeFilter, page], () => {
  page.value = 1
  loadFunds()
})

onMounted(() => {
  store.load()
  loadTabCounts()
  loadFunds()
})
</script>

<template>
  <div class="index-page">
    <!-- Header -->
    <header class="header">
      <h1 class="title">基金溢价查询</h1>
      <div class="search-box">
        <input
          v-model="searchQuery"
          @input="handleSearch"
          @focus="searchQuery ? showSearch = true : null"
          placeholder="搜索基金代码/名称"
          type="search"
        />
        <div v-if="showSearch && searchResults.length" class="search-results">
          <div
            v-for="item in searchResults"
            :key="item.code"
            class="search-item"
            @click="selectFund(item.code)"
          >
            <span class="code">{{ item.code }}</span>
            <span class="name">{{ item.name }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Tabs -->
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tabLabel(tab) }}
      </button>
    </div>

    <!-- Filters -->
    <div class="filters">
      <select v-model="premiumFilter">
        <option value="">溢价等级</option>
        <option value="high">高溢价(>5%)</option>
        <option value="normal">正常(0-5%)</option>
        <option value="discount">折价(<0)</option>
      </select>
      <select v-model="subscribeFilter">
        <option value="">申购状态</option>
        <option value="yes">可申购</option>
        <option value="no">暂停申购</option>
      </select>
      <select v-model="sortField">
        <option value="premium_rate">溢价率</option>
        <option value="change_pct">涨跌幅</option>
        <option value="volume">成交额</option>
        <option value="daily_limit">日限额</option>
      </select>
      <button @click="sortDir = sortDir === 'desc' ? 'asc' : 'desc'">
        {{ sortDir === 'desc' ? '↓' : '↑' }}
      </button>
    </div>

    <!-- Fund list -->
    <div class="fund-list">
      <div v-if="loading" class="loading">加载中...</div>
      <FundCard
        v-for="fund in funds"
        :key="fund.code"
        :fund="fund"
      />
      <div v-if="!loading && funds.length === 0" class="empty">
        暂无数据
      </div>
    </div>

    <!-- Pagination -->
    <div class="pagination" v-if="total > pageSize">
      <button :disabled="page <= 1" @click="page--">上一页</button>
      <span class="page-info">第 {{ page }} 页 / 共 {{ Math.ceil(total / pageSize) }} 页</span>
      <button :disabled="page >= Math.ceil(total / pageSize)" @click="page++">下一页</button>
    </div>
  </div>
</template>

<style scoped>
.index-page {
  padding: 16px;
}

.header {
  margin-bottom: 16px;
}

.title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 12px;
  color: #333;
}

.search-box {
  position: relative;
}

.search-box input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 16px;
  outline: none;
}

.search-box input:focus {
  border-color: #1890ff;
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-top: 4px;
  max-height: 300px;
  overflow-y: auto;
  z-index: 50;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.search-item {
  padding: 12px 16px;
  display: flex;
  gap: 8px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
}

.search-item:last-child {
  border-bottom: none;
}

.search-item:hover {
  background: #f5f5f5;
}

.search-item .code {
  color: #1890ff;
  font-weight: 600;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.tabs button {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 20px;
  background: #fff;
  font-size: 14px;
  white-space: nowrap;
  cursor: pointer;
}

.tabs button.active {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}

.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filters select,
.filters button {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
}

.fund-list {
  /* padding handled by parent */
}

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #999;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 20px 0;
}

.pagination button {
  padding: 8px 20px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 13px;
  color: #999;
}
</style>
