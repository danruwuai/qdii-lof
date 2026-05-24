<script setup>
import { RouterView, useRoute } from 'vue-router'
import Navbar from './components/Navbar.vue'

const route = useRoute()
const hideNavbar = route.name === 'detail' // 详情页隐藏底部导航
</script>

<template>
  <div id="app">
    <RouterView />
    <Navbar v-if="!hideNavbar" />
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f5f5f5;
  color: #333;
  -webkit-tap-highlight-color: transparent;
}

#app {
  min-height: 100vh;
  padding-bottom: 56px; /* navbar height */
}

@media (min-width: 768px) {
  #app {
    max-width: 768px;
    margin: 0 auto;
    border-left: 1px solid #eee;
    border-right: 1px solid #eee;
  }
}
</style>
