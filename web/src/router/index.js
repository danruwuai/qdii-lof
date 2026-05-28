import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'index', component: () => import('../views/Index.vue') },
  { path: '/detail/:code', name: 'detail', component: () => import('../views/Detail.vue') },
  { path: '/monitor', name: 'watchlist', component: () => import('../views/Watchlist.vue') },
  { path: '/alert', name: 'alerts', component: () => import('../views/Alerts.vue') },
  { path: '/setting', name: 'settings', component: () => import('../views/Settings.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
