<template>
  <nav class="bottom-nav">
    <router-link
      v-for="item in tabs"
      :key="item.path"
      :to="item.path"
      class="tab"
      :class="{ active: isActive(item.path) }"
    >
      <span class="tab-icon">{{ item.icon }}</span>
      <span class="tab-label">{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'
const route = useRoute()

const tabs = [
  { path: '/',          icon: '🏠', label: 'Home'     },
  { path: '/food',      icon: '🍽️', label: 'Food'     },
  { path: '/hydration', icon: '💧', label: 'Water'    },
  { path: '/exercise',  icon: '🏃', label: 'Exercise' },
  { path: '/insights',  icon: '💡', label: 'Insights' },
]

const isActive = (path) => path === '/' ? route.path === '/' : route.path.startsWith(path)
</script>

<style scoped>
.bottom-nav {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: var(--bottom-nav-h);
  background: #fff;
  border-top: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: 50;
  padding: 0 4px;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.06);
}

.tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  flex: 1;
  padding: 8px 4px;
  border-radius: var(--radius-sm);
  color: var(--text-light);
  transition: all 0.15s var(--ease);
  max-width: 72px;
}
.tab:hover { color: var(--green-600); }
.tab.active { color: var(--green-600); }

.tab-icon  { font-size: 20px; line-height: 1; }
.tab-label { font-size: 10px; font-weight: 600; }

.tab.active .tab-icon {
  filter: drop-shadow(0 2px 4px rgba(22,163,74,0.4));
}
</style>
