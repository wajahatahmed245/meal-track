<template>
  <div class="insights card">
    <div class="section-title">
      <span>💡 Insights & Tips</span>
      <router-link to="/insights" class="see-more">See all →</router-link>
    </div>
    <div class="insights-list">
      <div
        v-for="insight in items"
        :key="insight.id"
        class="insight-item"
        :class="`insight-${insight.color}`"
      >
        <span class="insight-emoji">{{ insight.emoji }}</span>
        <p class="insight-text">{{ insight.message }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  items: { type: Array, required: true },
})
</script>

<style scoped>
.insights { padding: 20px; }

.see-more {
  font-size: 12px;
  color: var(--green-600);
  font-weight: 500;
}
.see-more:hover { text-decoration: underline; }

.insights-list { display: flex; flex-direction: column; gap: 8px; }

.insight-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  border-left: 3px solid transparent;
}
.insight-emoji { font-size: 18px; flex-shrink: 0; margin-top: 1px; }
.insight-text  { font-size: 13px; line-height: 1.5; color: var(--text); }

.insight-green  { background: var(--green-50);  border-left-color: var(--green-500);  }
.insight-blue   { background: var(--blue-50);   border-left-color: var(--blue-500);   }
.insight-orange { background: var(--orange-50); border-left-color: var(--orange-500); }
.insight-purple { background: var(--purple-50); border-left-color: var(--purple-500); }
</style>
