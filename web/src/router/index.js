import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'index', component: () => import('../views/Index.vue') },
  { path: '/detail/:code', name: 'detail', component: () => import('../views/Detail.vue') },
  { path: '/watchlist', name: 'watchlist', component: () => import('../views/Watchlist.vue') },
  { path: '/alerts', name: 'alerts', component: () => import('../views/Alerts.vue') },
  { path: '/settings', name: 'settings', component: () => import('../views/Settings.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
