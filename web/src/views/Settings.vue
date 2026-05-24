<script setup>
import { ref } from 'vue'
import { healthCheck } from '../api'

const backendStatus = ref({ status: 'checking' })
const checking = ref(true)

async function checkBackend() {
  checking.value = true
  try {
    backendStatus.value = await healthCheck()
  } catch (e) {
    backendStatus.value = { status: 'offline', error: e.message }
  }
  checking.value = false
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    alert('已复制')
  }).catch(() => {
    alert('复制失败')
  })
}
</script>

<template>
  <div class="settings-page">
    <h1 class="title">设置</h1>

    <!-- Backend status -->
    <div class="card">
      <div class="card-title">后端状态</div>
      <div class="status-row">
        <span class="label">API 状态</span>
        <span class="value" :class="{ online: backendStatus.status === 'ok', offline: backendStatus.status === 'offline' }">
          {{ checking ? '检查中...' : backendStatus.status === 'ok' ? '✅ 正常' : '❌ 离线' }}
        </span>
      </div>
      <button class="check-btn" @click="checkBackend" :disabled="checking">
        {{ checking ? '检查中...' : '重新检查' }}
      </button>
    </div>

    <!-- PWA info -->
    <div class="card">
      <div class="card-title">PWA 使用说明</div>
      <div class="info-list">
        <div class="info-item">
          <strong>添加到桌面</strong>
          <p>Chrome/Edge: 点击地址栏右侧的"安装"图标</p>
          <p>Safari (iOS): 点击分享按钮 → "添加到主屏幕"</p>
          <p>微信 (Android): 点击右上角"..." → "添加到桌面"</p>
        </div>
        <div class="info-item">
          <strong>全屏运行</strong>
          <p>添加后点击桌面图标，应用将以独立窗口运行，无浏览器地址栏</p>
        </div>
        <div class="info-item">
          <strong>离线使用</strong>
          <p>首次访问后，静态资源会被缓存，断网时仍可打开页面</p>
          <p>实时数据需要网络连接</p>
        </div>
      </div>
    </div>

    <!-- API info -->
    <div class="card">
      <div class="card-title">API 信息</div>
      <div class="info-list">
        <div class="info-item">
          <strong>API 地址</strong>
          <code>{{ window.location.origin }}</code>
          <button @click="copyToClipboard(window.location.origin)">复制</button>
        </div>
        <div class="info-item">
          <strong>后端文档</strong>
          <p>访问 <code>/docs</code> 查看 Swagger 文档</p>
        </div>
      </div>
    </div>

    <!-- About -->
    <div class="card">
      <div class="card-title">关于</div>
      <div class="info-list">
        <div class="info-item">
          <strong>项目名称</strong>
          <p>QDII/LOF/ETF 基金溢价查询</p>
        </div>
        <div class="info-item">
          <strong>免责声明</strong>
          <p>本工具仅供个人/家族内部信息共享使用，不构成任何投资建议。</p>
          <p>QDII 基金净值存在 T+2 延迟，溢价率存在较大波动风险，请谨慎决策。</p>
        </div>
        <div class="info-item">
          <strong>数据源</strong>
          <p>akshare / 东方财富 / 天天基金 / 集思录</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  padding: 16px;
}

.title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #333;
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status-row .label {
  font-size: 14px;
  color: #666;
}

.status-row .value {
  font-weight: 600;
  font-size: 15px;
}

.status-row .value.online { color: #52c41a; }
.status-row .value.offline { color: #ff4d4f; }

.check-btn {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  font-size: 14px;
  cursor: pointer;
}

.check-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item strong {
  display: block;
  font-size: 14px;
  color: #333;
  margin-bottom: 4px;
}

.info-item p {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
  margin: 0;
}

.info-item code {
  display: block;
  background: #f5f5f5;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
  color: #1890ff;
  word-break: break-all;
  margin: 6px 0;
}

.info-item button {
  margin-top: 6px;
  padding: 6px 14px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
}
</style>
