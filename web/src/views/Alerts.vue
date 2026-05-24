<script setup>
import { ref, onMounted } from 'vue'
import { listAlerts, createAlert, updateAlert, deleteAlert } from '../api'
import { searchFunds } from '../api'

const alerts = ref([])
const loading = ref(true)
const showAdd = ref(false)

// Form
const editId = ref(null)
const fundCode = ref('')
const fundName = ref('')
const thresholdAbove = ref('5')
const thresholdBelow = ref('-2')
const searchResults = ref([])
const showSearch = ref(false)

// WeChat binding
const wechatOpenid = ref('')
const isWechatBound = ref(false)
const bindingStatus = ref('checking') // checking, unbound, bound, error

async function loadAlerts() {
  try {
    const data = await listAlerts()
    alerts.value = data.items || []
  } catch (e) {
    console.error('Failed to load alerts:', e)
    alerts.value = []
  }
  loading.value = false
}

async function handleSearch() {
  if (!fundCode.value.trim()) {
    searchResults.value = []
    showSearch.value = false
    return
  }
  try {
    searchResults.value = await searchFunds(fundCode.value)
  } catch (e) {
    searchResults.value = []
  }
}

function selectFund(item) {
  fundCode.value = item.code
  fundName.value = item.name
  searchResults.value = []
  showSearch.value = false
}

function resetForm() {
  editId.value = null
  fundCode.value = ''
  fundName.value = ''
  thresholdAbove.value = '5'
  thresholdBelow.value = '-2'
  showAdd.value = false
}

async function handleSubmit() {
  if (!fundCode.value) {
    alert('请选择基金')
    return
  }

  const data = {
    fund_code: fundCode.value,
    threshold_above: parseFloat(thresholdAbove.value) || 5,
    threshold_below: parseFloat(thresholdBelow.value) || -2,
  }

  try {
    if (editId.value) {
      await updateAlert(editId.value, data)
    } else {
      await createAlert(data)
    }
    resetForm()
    await loadAlerts()
  } catch (e) {
    alert('操作失败: ' + (e.response?.data?.message || e.message))
  }
}

async function handleDelete(id) {
  if (!confirm('确定删除此提醒规则？')) return
  try {
    await deleteAlert(id)
    await loadAlerts()
  } catch (e) {
    alert('删除失败')
  }
}

function editAlert(item) {
  editId.value = item.id
  fundCode.value = item.fund_code
  fundName.value = item.fund_code
  thresholdAbove.value = item.threshold_above?.toString() || '5'
  thresholdBelow.value = item.threshold_below?.toString() || '-2'
  showAdd.value = true
}

// WeChat binding functions
function checkWechatBinding() {
  const storedOpenid = localStorage.getItem('wechat_openid')
  if (storedOpenid) {
    wechatOpenid.value = storedOpenid
    isWechatBound.value = true
    bindingStatus.value = 'bound'
  } else {
    bindingStatus.value = 'unbound'
  }
}

function bindWechat() {
  // 跳转到微信OAuth授权页面
  window.location.href = '/api/v1/wechat/oauth/authorize'
}

function unbindWechat() {
  if (confirm('确定取消微信绑定？取消后您将无法通过微信接收溢价提醒。')) {
    localStorage.removeItem('wechat_openid')
    wechatOpenid.value = ''
    isWechatBound.value = false
    bindingStatus.value = 'unbound'
  }
}

onMounted(() => {
  loadAlerts()
  checkWechatBinding()
})
</script>

<template>
  <div class="alerts-page">
    <h1 class="title">溢价提醒</h1>

    <!-- WeChat Binding Card -->
    <div class="wechat-card">
      <div class="wechat-header">
        <span class="wechat-icon">💬</span>
        <span class="wechat-title">微信推送通知</span>
      </div>
      <div class="wechat-status" v-if="bindingStatus === 'checking'">
        检查绑定状态中...
      </div>
      <div class="wechat-status bound" v-else-if="isWechatBound">
        <div class="status-row">
          <span class="status-badge success">已绑定</span>
          <span class="openid">OpenID: {{ wechatOpenid.substring(0, 12) }}...</span>
        </div>
        <p class="wechat-hint">
          当溢价率触发阈值时，会通过公众号推送消息到您的微信
        </p>
        <button class="btn-unbind" @click="unbindWechat">取消绑定</button>
      </div>
      <div class="wechat-status unbound" v-else>
        <p class="wechat-hint">
          绑定公众号后，溢价提醒将推送到您的微信
        </p>
        <button class="btn-bind" @click="bindWechat">绑定公众号</button>
        <p class="wechat-note">
          注意：需要已关注公众号才能接收模板消息
        </p>
      </div>
    </div>

    <!-- Add Button -->
    <button class="add-btn" @click="showAdd = !showAdd">
      {{ showAdd ? '取消' : '+ 添加提醒规则' }}
    </button>

    <!-- Add/Edit Form -->
    <div v-if="showAdd" class="form-card">
      <div class="form-title">{{ editId ? '编辑提醒' : '添加提醒' }}</div>

      <div class="form-group">
        <label>基金</label>
        <div class="search-input-wrap">
          <input
            v-model="fundCode"
            @input="handleSearch"
            @focus="fundCode ? showSearch = true : null"
            placeholder="输入基金代码或名称"
          />
          <div v-if="showSearch && searchResults.length" class="search-results">
            <div
              v-for="item in searchResults"
              :key="item.code"
              class="search-item"
              @click="selectFund(item)"
            >
              <span class="code">{{ item.code }}</span>
              <span class="name">{{ item.name }}</span>
            </div>
          </div>
        </div>
        <div class="selected-fund" v-if="fundName">
          已选: {{ fundCode }} - {{ fundName }}
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>溢价 > % 提醒</label>
          <input v-model="thresholdAbove" type="number" step="0.1" />
        </div>
        <div class="form-group">
          <label>折价 < % 提醒</label>
          <input v-model="thresholdBelow" type="number" step="0.1" />
        </div>
      </div>

      <div class="wechat-notice" v-if="isWechatBound">
        💡 已绑定微信，触发时将通过公众号推送消息
      </div>

      <div class="form-actions">
        <button class="btn-cancel" @click="resetForm">取消</button>
        <button class="btn-submit" @click="handleSubmit">保存</button>
      </div>
    </div>

    <!-- Alerts list -->
    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="alerts.length === 0" class="empty">
      <div class="empty-icon">🔔</div>
      <div class="empty-text">暂无提醒规则</div>
      <div class="empty-hint">添加规则后，当溢价率触发阈值时会收到通知</div>
      <div class="empty-hint" v-if="isWechatBound">
        已绑定微信，通知将推送到公众号
      </div>
    </div>

    <div v-else class="alert-list">
      <div v-for="alert in alerts" :key="alert.id" class="alert-card">
        <div class="alert-header">
          <span class="fund-code">{{ alert.fund_code }}</span>
          <div class="alert-actions">
            <button @click="editAlert(alert)">编辑</button>
            <button class="delete" @click="handleDelete(alert.id)">删除</button>
          </div>
        </div>
        <div class="alert-thresholds">
          <span class="threshold">溢价 > {{ alert.threshold_above }}%</span>
          <span class="threshold" v-if="alert.threshold_below !== null">折价 < {{ alert.threshold_below }}%</span>
        </div>
        <div class="alert-status">
          <span class="status" :class="{ active: alert.is_active }">
            {{ alert.is_active ? '✅ 已启用' : '⏸️ 已暂停' }}
          </span>
          <span class="wechat-badge" v-if="isWechatBound">📱 微信推送</span>
        </div>
      </div>
    </div>

    <!-- Tips -->
    <div class="tips">
      <div class="tips-title">💡 使用提示</div>
      <ul>
        <li>当基金溢价率超过设定阈值时，会触发提醒</li>
        <li v-if="isWechatBound">✅ 已绑定微信，提醒将通过公众号模板消息推送</li>
        <li v-else>⚠️ 未绑定微信，请点击上方"绑定公众号"启用微信推送</li>
        <li>建议设置溢价 &gt; 5% 作为套利提醒，&gt; 10% 作为高溢价风险提醒</li>
        <li>折价 &lt; -2% 可作为埋伏机会提醒</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.alerts-page {
  padding: 16px;
}

.title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #333;
}

/* WeChat Binding Card */
.wechat-card {
  background: linear-gradient(135deg, #07c160 0%, #05a650 100%);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  color: #fff;
}

.wechat-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.wechat-icon {
  font-size: 24px;
}

.wechat-title {
  font-size: 16px;
  font-weight: 600;
}

.wechat-status {
  font-size: 14px;
}

.wechat-status.checking {
  opacity: 0.9;
}

.wechat-status.bound {
  background: rgba(255,255,255,0.15);
  border-radius: 8px;
  padding: 12px;
}

.wechat-status.unbound {
  background: rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 12px;
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.status-badge {
  background: #fff;
  color: #07c160;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
}

.openid {
  font-family: monospace;
  font-size: 12px;
  opacity: 0.9;
}

.wechat-hint {
  font-size: 13px;
  opacity: 0.95;
  margin-bottom: 10px;
  line-height: 1.5;
}

.wechat-note {
  font-size: 12px;
  opacity: 0.8;
  margin-top: 8px;
}

.btn-bind, .btn-unbind {
  width: 100%;
  padding: 10px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-bind {
  background: #fff;
  color: #07c160;
  border: none;
}

.btn-unbind {
  background: rgba(255,255,255,0.2);
  color: #fff;
  border: 1px solid rgba(255,255,255,0.3);
}

.add-btn {
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: 8px;
  background: #1890ff;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 16px;
}

.form-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.form-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 14px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: #666;
  margin-bottom: 6px;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 15px;
}

.search-input-wrap {
  position: relative;
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
  max-height: 200px;
  overflow-y: auto;
  z-index: 50;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.search-item {
  padding: 10px 12px;
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

.selected-fund {
  margin-top: 6px;
  font-size: 13px;
  color: #1890ff;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-row .form-group {
  flex: 1;
}

.wechat-notice {
  background: #f0f9ff;
  border: 1px solid #bae7ff;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 13px;
  color: #1890ff;
  margin-bottom: 14px;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.btn-cancel, .btn-submit {
  flex: 1;
  padding: 12px;
  border-radius: 6px;
  font-size: 15px;
  cursor: pointer;
}

.btn-cancel {
  border: 1px solid #ddd;
  background: #fff;
}

.btn-submit {
  border: none;
  background: #1890ff;
  color: #fff;
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

.alert-list {
  /* padding handled by parent */
}

.alert-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.fund-code {
  font-weight: 600;
  color: #1890ff;
  font-size: 16px;
}

.alert-actions {
  display: flex;
  gap: 8px;
}

.alert-actions button {
  padding: 4px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
}

.alert-actions button.delete {
  color: #ff4d4f;
  border-color: #ffccc7;
}

.alert-thresholds {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
}

.threshold {
  font-size: 13px;
  color: #666;
}

.alert-status {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  flex-wrap: wrap;
}

.alert-status .status.active {
  color: #52c41a;
}

.alert-status .status:not(.active) {
  color: #999;
}

.wechat-badge {
  background: #e6f7ff;
  color: #1890ff;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.tips {
  background: #f6f8ff;
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
}

.tips-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #1890ff;
}

.tips ul {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #666;
  line-height: 1.8;
}
</style>
