<template>
  <div class="page-content">
    <h1 class="page-title">💡 Insights & Tips</h1>
    <p class="page-sub">Smart analysis of your eating and wellness patterns</p>

    <!-- Score card -->
    <div class="score-card card">
      <div class="score-left">
        <div class="score-label">Today's Health Score</div>
        <div class="score-value">{{ score }}<span class="score-max">/100</span></div>
        <div class="score-badge" :class="scoreBadge.cls">{{ scoreBadge.label }}</div>
      </div>
      <div class="score-bars">
        <div v-for="metric in scoreMetrics" :key="metric.label" class="score-metric">
          <div class="sm-label">{{ metric.icon }} {{ metric.label }}</div>
          <div class="sm-bar-track">
            <div class="sm-bar-fill" :style="{ width: metric.pct + '%', background: metric.color }" />
          </div>
          <div class="sm-pct">{{ metric.pct }}%</div>
        </div>
      </div>
    </div>

    <!-- All insights -->
    <div class="insights-section">
      <div class="section-title">Today's Insights</div>
      <div class="insights-grid">
        <div
          v-for="insight in allInsights"
          :key="insight.id"
          class="insight-card card"
          :class="`insight-${insight.color}`"
        >
          <div class="ic-emoji">{{ insight.emoji }}</div>
          <div class="ic-body">
            <div class="ic-type">{{ insight.type.toUpperCase() }}</div>
            <p class="ic-text">{{ insight.message }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- What to reduce -->
    <div class="reduce-section card">
      <div class="section-title">⚠️ What to Watch</div>
      <div class="reduce-list">
        <div v-for="item in toReduce" :key="item.label" class="reduce-item">
          <span class="ri-emoji">{{ item.emoji }}</span>
          <div class="ri-body">
            <div class="ri-label">{{ item.label }}</div>
            <div class="ri-note">{{ item.note }}</div>
          </div>
          <div class="ri-severity" :class="item.severity">{{ item.severity }}</div>
        </div>
      </div>
    </div>

    <!-- Weekly pattern -->
    <div class="pattern-card card">
      <div class="section-title">📅 Weekly Pattern</div>
      <p class="pattern-text">
        You have a consistent breakfast habit (5/7 days) 🌅 but tend to overeat on weekends
        (Saturday avg: 2,200 cal vs 1,750 weekday avg). Consider lighter weekend dinners.
      </p>
      <div class="pattern-tags">
        <span class="ptag green">✓ Consistent Breakfast</span>
        <span class="ptag green">✓ Good Protein Balance</span>
        <span class="ptag orange">⚠ Weekend Overeating</span>
        <span class="ptag blue">💡 Increase Hydration</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { store } from '../store/index.js'
import { insights } from '../data/mock.js'

const allInsights = [...insights, {
  id: 5, type: 'positive', emoji: '🌅', message: 'You have a solid breakfast routine — logged 5 of the last 7 days.', color: 'green',
}]

const score = computed(() => {
  let s = 60
  if (store.caloriePct >= 50 && store.caloriePct <= 100) s += 15
  if (store.waterPct >= 60)    s += 15
  if (store.exercise.completed) s += 10
  return Math.min(s, 100)
})

const scoreBadge = computed(() => {
  if (score.value >= 85) return { cls: 'badge-green',  label: '🌟 Excellent' }
  if (score.value >= 70) return { cls: 'badge-blue',   label: '👍 Good'      }
  if (score.value >= 55) return { cls: 'badge-orange', label: '📈 Fair'      }
  return                        { cls: 'badge-gray',   label: '💪 Keep Going' }
})

const scoreMetrics = computed(() => [
  { icon: '🔥', label: 'Calorie Goal',  pct: store.caloriePct, color: '#f97316' },
  { icon: '💧', label: 'Hydration',     pct: store.waterPct,   color: '#0ea5e9' },
  { icon: '🏃', label: 'Exercise',      pct: store.exercise.completed ? 100 : 0, color: '#22c55e' },
  { icon: '🍽️', label: 'Meals Logged',  pct: Math.min(store.mealsLogged * 20, 100), color: '#8b5cf6' },
])

const toReduce = [
  { emoji: '🍛', label: 'High-calorie dinners', note: 'Your dinner avg is 556 cal — try lighter options 2–3x a week.', severity: 'moderate' },
  { emoji: '🧂', label: 'Sodium tracking',      note: 'You have not tracked sodium. Curry dishes tend to be high.', severity: 'low' },
  { emoji: '🥤', label: 'Sugary drinks',        note: 'Replace Lemonade with plain water 1–2 times per day.', severity: 'low' },
]
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.page-sub   { font-size: 13px; color: var(--text-muted); margin-bottom: 20px; }

/* Score card */
.score-card {
  display: flex; gap: 24px; padding: 24px; margin-bottom: 20px;
  flex-wrap: wrap; align-items: flex-start;
}
.score-left { min-width: 140px; }
.score-label { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
.score-value { font-size: 56px; font-weight: 800; color: var(--green-600); line-height: 1; }
.score-max   { font-size: 20px; color: var(--text-muted); }
.score-badge { display: inline-flex; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; margin-top: 8px; }

.score-bars { flex: 1; display: flex; flex-direction: column; gap: 14px; min-width: 200px; }
.score-metric { display: grid; grid-template-columns: 120px 1fr 40px; align-items: center; gap: 10px; }
.sm-label  { font-size: 12px; font-weight: 500; color: var(--text-muted); }
.sm-bar-track { height: 8px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.sm-bar-fill  { height: 100%; border-radius: 4px; transition: width 0.5s var(--ease); }
.sm-pct { font-size: 12px; font-weight: 600; color: var(--text); text-align: right; }

/* Insights grid */
.insights-section { margin-bottom: 20px; }
.insights-grid { display: flex; flex-direction: column; gap: 10px; }
.insight-card {
  display: flex; gap: 14px; padding: 16px 18px; border-left: 4px solid transparent;
}
.insight-card.insight-green  { border-left-color: var(--green-500);  background: var(--green-50); }
.insight-card.insight-blue   { border-left-color: var(--blue-500);   background: var(--blue-50); }
.insight-card.insight-orange { border-left-color: var(--orange-500); background: var(--orange-50); }
.insight-card.insight-purple { border-left-color: var(--purple-500); background: var(--purple-50); }

.ic-emoji { font-size: 24px; flex-shrink: 0; }
.ic-type  { font-size: 10px; font-weight: 700; letter-spacing: 0.08em; color: var(--text-light); margin-bottom: 3px; }
.ic-text  { font-size: 13px; line-height: 1.5; color: var(--text); }

/* What to reduce */
.reduce-section { padding: 20px; margin-bottom: 20px; }
.reduce-list { display: flex; flex-direction: column; gap: 12px; }
.reduce-item { display: flex; align-items: flex-start; gap: 12px; }
.ri-emoji    { font-size: 22px; flex-shrink: 0; }
.ri-body     { flex: 1; }
.ri-label    { font-size: 14px; font-weight: 600; }
.ri-note     { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.ri-severity { font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 10px; white-space: nowrap; }
.ri-severity.high     { background: #fee2e2; color: #dc2626; }
.ri-severity.moderate { background: var(--orange-50); color: var(--orange-600); }
.ri-severity.low      { background: var(--blue-50); color: var(--blue-600); }

/* Pattern */
.pattern-card { padding: 20px; }
.pattern-text { font-size: 14px; color: var(--text); line-height: 1.6; margin-bottom: 14px; }
.pattern-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.ptag { display: inline-flex; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.ptag.green  { background: var(--green-100);  color: var(--green-700); }
.ptag.orange { background: var(--orange-100); color: var(--orange-600); }
.ptag.blue   { background: var(--blue-100);   color: var(--blue-600); }
</style>
