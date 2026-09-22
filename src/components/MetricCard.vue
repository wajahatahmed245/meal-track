<template>
  <div class="metric-card card" :class="`metric-${color}`">
    <div class="metric-icon-wrap">
      <span class="metric-icon">{{ icon }}</span>
    </div>
    <div class="metric-body">
      <div class="metric-value">
        {{ value }}<span v-if="unit" class="metric-unit"> {{ unit }}</span>
      </div>
      <div class="metric-label">{{ label }}</div>
      <div v-if="sub" class="metric-sub">{{ sub }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  icon:  { type: String, required: true },
  value: { type: [String, Number], required: true },
  unit:  { type: String, default: '' },
  label: { type: String, required: true },
  sub:   { type: String, default: '' },
  color: { type: String, default: 'orange' }, // orange | blue | purple | green
})
</script>

<style scoped>
.metric-card {
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: transform 0.15s var(--ease), box-shadow 0.15s var(--ease);
  cursor: default;
}
.metric-card:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow);
}

.metric-icon-wrap {
  width: 48px; height: 48px;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.metric-value {
  font-size: 22px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.5px;
}
.metric-unit { font-size: 14px; font-weight: 500; color: var(--text-muted); }
.metric-label { font-size: 12px; color: var(--text-muted); font-weight: 500; margin-top: 2px; }
.metric-sub   { font-size: 11px; color: var(--text-light); margin-top: 2px; }

/* Color variants */
.metric-orange .metric-icon-wrap { background: var(--orange-50); }
.metric-orange .metric-value      { color: var(--orange-500); }

.metric-blue .metric-icon-wrap { background: var(--blue-50); }
.metric-blue .metric-value      { color: var(--blue-500); }

.metric-purple .metric-icon-wrap { background: var(--purple-50); }
.metric-purple .metric-value      { color: var(--purple-500); }

.metric-green .metric-icon-wrap { background: var(--green-50); }
.metric-green .metric-value      { color: var(--green-600); }
</style>
