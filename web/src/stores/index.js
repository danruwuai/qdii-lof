import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getWatchlist, addToWatchlist, removeFromWatchlist } from '../api'

export const useWatchStore = defineStore('watchlist', () => {
  const items = ref([])
  const loaded = ref(false)

  const fundCodes = computed(() => items.value.map(i => i.code))

  async function load() {
    try {
      const data = await getWatchlist()
      items.value = data.items || []
    } catch (e) {
      console.error('Failed to load watchlist:', e)
      items.value = []
    }
    loaded.value = true
  }

  async function add(code) {
    await addToWatchlist({ fund_code: code })
    await load()
  }

  async function remove(code) {
    await removeFromWatchlist(code)
    await load()
  }

  function isWatching(code) {
    return fundCodes.value.includes(code)
  }

  return { items, loaded, fundCodes, load, add, remove, isWatching }
})
