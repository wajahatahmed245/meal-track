<template>
  <div class="app-root">
    <AppSidebar v-if="!isMobile" />
    <div class="main-area">
      <router-view />
    </div>
    <BottomNav v-if="isMobile" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import AppSidebar from './components/AppSidebar.vue'
import BottomNav  from './components/BottomNav.vue'

const isMobile = ref(window.innerWidth < 768)

const onResize = () => { isMobile.value = window.innerWidth < 768 }
onMounted(()  => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))
</script>
