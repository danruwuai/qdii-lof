import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || ''

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
})

// List funds with filters
export async function listFunds(params) {
  const res = await api.get('/api/v1/funds', { params })
  return res.data
}

// Get fund detail
export async function getFundDetail(code) {
  const res = await api.get(`/api/v1/funds/${code}`)
  return res.data
}

// Search funds
export async function searchFunds(q) {
  const res = await api.get('/api/v1/funds/search', { params: { q } })
  return res.data
}

// Get tab counts
export async function getTabCounts() {
  const res = await api.get('/api/v1/funds/tab-counts')
  return res.data
}

// Watchlist
export async function getWatchlist() {
  const res = await api.get('/api/v1/watchlist')
  return res.data
}

export async function addToWatchlist(item) {
  const res = await api.post('/api/v1/watchlist', item)
  return res.data
}

export async function removeFromWatchlist(fund_code) {
  const res = await api.delete(`/api/v1/watchlist/${fund_code}`)
  return res.data
}

// Alerts
export async function listAlerts() {
  const res = await api.get('/api/v1/alerts')
  return res.data
}

export async function createAlert(data) {
  const res = await api.post('/api/v1/alerts', data)
  return res.data
}

export async function updateAlert(id, data) {
  const res = await api.put(`/api/v1/alerts/${id}`, data)
  return res.data
}

export async function deleteAlert(id) {
  const res = await api.delete(`/api/v1/alerts/${id}`)
  return res.data
}

// Market status
export async function getMarketStatus() {
  const res = await api.get('/api/v1/market-status')
  return res.data
}

// Health check
export async function healthCheck() {
  const res = await api.get('/health')
  return res.data
}

export default api
