<template>
  <div class="page-content">
    <div class="page-header">
      <h1 class="page-title">🍽️ AI Food Suggestions</h1>
      <p class="page-sub">Get personalised Pakistani food recommendations for your remaining calories</p>
    </div>

    <!-- Calorie status card -->
    <div class="card calorie-card">
      <div v-if="loadingStatus" class="calorie-loading">Loading today's data…</div>
      <template v-else>
        <div class="calorie-row">
          <div class="calorie-stat">
            <div class="calorie-label">Daily Goal</div>
            <div class="calorie-value">{{ dailyGoal }} kcal</div>
          </div>
          <div class="calorie-stat">
            <div class="calorie-label">Consumed</div>
            <div class="calorie-value consumed">{{ consumed }} kcal</div>
          </div>
          <div class="calorie-stat">
            <div class="calorie-label">Remaining</div>
            <div class="calorie-value" :class="remainingClass">{{ remaining }} kcal</div>
          </div>
        </div>
        <div class="calorie-bar-bg">
          <div class="calorie-bar-fill" :style="{ width: Math.min(consumedPct, 100) + '%' }" :class="remainingClass"></div>
        </div>
        <div class="calorie-bar-label">{{ consumedPct }}% of daily goal consumed</div>
      </template>
    </div>

    <!-- Usage indicator -->
    <div class="usage-row">
      <div class="usage-dots">
        <span
          v-for="i in LIMIT"
          :key="i"
          class="usage-dot"
          :class="{ used: i <= usageCount }"
        />
      </div>
      <div class="usage-text">
        <template v-if="usageCount >= LIMIT">
          All {{ LIMIT }} suggestions used today
        </template>
        <template v-else>
          {{ usageCount }} of {{ LIMIT }} AI suggestions used today
          · {{ LIMIT - usageCount }} remaining
        </template>
      </div>
    </div>

    <!-- Generate button -->
    <button
      class="btn btn-primary generate-btn"
      :disabled="generateDisabled"
      @click="generate"
    >
      <span v-if="generating">⏳ Getting suggestions…</span>
      <span v-else-if="remaining <= 0">✅ Calorie goal reached — no suggestions needed</span>
      <span v-else-if="usageCount >= LIMIT">🚫 Daily limit reached — try again tomorrow</span>
      <span v-else>✨ Get Food Suggestions</span>
    </button>

    <!-- Error -->
    <div v-if="errorMsg" class="error-banner">
      ⚠️ {{ errorMsg }}
      <button class="btn btn-sm btn-outline ml-8" @click="errorMsg = ''">Dismiss</button>
    </div>

    <!-- Suggestions -->
    <div v-if="suggestions.length" class="suggestions-section">
      <h2 class="section-title">Suggestions for you</h2>
      <p class="section-sub">Based on your {{ remaining }} kcal remaining · {{ timeOfDay }}</p>

      <div
        v-for="(s, idx) in suggestions"
        :key="idx"
        class="card suggestion-card"
        :class="suggestionClass(idx)"
      >
        <div class="suggestion-badge">{{ LABELS[idx] }}</div>
        <div class="suggestion-name">{{ s.name }}</div>
        <div class="suggestion-desc">{{ s.description }}</div>

        <div class="suggestion-chips">
          <span class="chip chip-cal">~{{ s.estimated_calories }} kcal</span>
          <span class="chip chip-price">Est. PKR {{ s.estimated_price_min_pkr }}–{{ s.estimated_price_max_pkr }}</span>
          <span class="chip chip-after">After eating: {{ consumed + s.estimated_calories }} / {{ dailyGoal }} kcal</span>
        </div>

        <div v-if="s.notes" class="suggestion-notes">{{ s.notes }}</div>
      </div>

      <p class="disclaimer">
        * Calorie and price estimates are approximate. Prices reflect typical Lahore market rates (2026) and may vary by vendor.
      </p>
    </div>

    <!-- Limit reached message (after suggestions are shown) -->
    <div v-if="usageCount >= LIMIT && !generating" class="limit-card card">
      🚫 You've used all {{ LIMIT }} AI food suggestions for today. Try again tomorrow!
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'

const LIMIT = 5
const LABELS = ['💰 Budget Option', '🍛 Balanced Option', '🏪 Restaurant Option']

const loadingStatus = ref(true)
const generating    = ref(false)
const errorMsg      = ref('')

const dailyGoal    = ref(2000)
const consumed     = ref(0)
const usageCount   = ref(0)
const suggestions  = ref([])
const timeOfDay    = ref('')

const remaining    = computed(() => Math.max(0, dailyGoal.value - consumed.value))
const consumedPct  = computed(() => dailyGoal.value > 0 ? Math.round((consumed.value / dailyGoal.value) * 100) : 0)

const remainingClass = computed(() => {
  if (remaining.value <= 0) return 'cal-zero'
  if (remaining.value < 200) return 'cal-low'
  return 'cal-ok'
})

const generateDisabled = computed(() =>
  generating.value || remaining.value <= 0 || usageCount.value >= LIMIT
)

function suggestionClass(idx) {
  return ['card-budget', 'card-balanced', 'card-restaurant'][idx] || ''
}

function getTimeOfDay() {
  const h = new Date().getHours()
  if (h >= 5  && h < 12) return 'morning'
  if (h >= 12 && h < 17) return 'afternoon'
  if (h >= 17 && h < 21) return 'evening'
  return 'night'
}

async function loadStatus() {
  loadingStatus.value = true
  try {
    const [summary, usage] = await Promise.all([
      api.getTodaySummary(),
      api.getFoodSuggestionUsage(),
    ])
    dailyGoal.value  = summary.calorie_goal
    consumed.value   = summary.total_calories
    usageCount.value = usage.requests_used_today
    timeOfDay.value  = getTimeOfDay()
  } catch (e) {
    errorMsg.value = 'Failed to load today\'s data. Please refresh.'
  } finally {
    loadingStatus.value = false
  }
}

async function generate() {
  if (generateDisabled.value) return
  generating.value = true
  errorMsg.value   = ''
  try {
    const data = await api.generateFoodSuggestions()
    suggestions.value  = data.suggestions
    usageCount.value   = data.requests_used_today
    dailyGoal.value    = data.daily_goal
    consumed.value     = data.consumed_today
  } catch (e) {
    const detail = e?.message
    if (e?.status === 429) {
      usageCount.value = LIMIT
      errorMsg.value = detail || 'Daily limit reached. Try again tomorrow.'
    } else {
      errorMsg.value = detail || 'AI service is temporarily unavailable. Please try again.'
    }
  } finally {
    generating.value = false
  }
}

onMounted(loadStatus)
</script>

<style scoped>
.page-sub {
  color: var(--text-muted);
  font-size: 14px;
  margin-top: 4px;
}

/* Calorie card */
.calorie-card { padding: 20px; margin-bottom: 16px; }
.calorie-loading { color: var(--text-light); font-size: 14px; text-align: center; padding: 12px 0; }

.calorie-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.calorie-stat { flex: 1; text-align: center; }
.calorie-label { font-size: 11px; color: var(--text-light); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
.calorie-value { font-size: 18px; font-weight: 700; color: var(--text); }
.calorie-value.consumed { color: var(--orange-500); }

.cal-ok   { color: var(--green-600); }
.cal-low  { color: #d97706; }
.cal-zero { color: var(--text-muted); }

.calorie-bar-bg { height: 6px; background: var(--border-light); border-radius: 99px; overflow: hidden; }
.calorie-bar-fill {
  height: 100%;
  border-radius: 99px;
  transition: width 0.4s ease;
  background: var(--green-500);
}
.calorie-bar-fill.cal-low  { background: #d97706; }
.calorie-bar-fill.cal-zero { background: var(--text-muted); }
.calorie-bar-label { font-size: 11px; color: var(--text-light); margin-top: 6px; }

/* Usage indicator */
.usage-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.usage-dots { display: flex; gap: 5px; }
.usage-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--border);
  border: 1.5px solid var(--border);
  transition: background 0.2s;
}
.usage-dot.used { background: var(--green-500); border-color: var(--green-500); }
.usage-text { font-size: 13px; color: var(--text-muted); }

/* Generate button */
.generate-btn {
  width: 100%;
  justify-content: center;
  padding: 14px;
  font-size: 15px;
  margin-bottom: 16px;
}

/* Error */
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #c2410c;
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  font-size: 13px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

/* Suggestions */
.suggestions-section { margin-top: 8px; }
.section-title { font-size: 17px; font-weight: 700; color: var(--text); margin-bottom: 2px; }
.section-sub   { font-size: 13px; color: var(--text-muted); margin-bottom: 14px; }

.suggestion-card { padding: 16px; margin-bottom: 12px; border-left: 4px solid var(--border); }
.card-budget     { border-left-color: var(--green-500); }
.card-balanced   { border-left-color: var(--orange-500); }
.card-restaurant { border-left-color: #6366f1; }

.suggestion-badge {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-light);
  margin-bottom: 6px;
}
.suggestion-name { font-size: 16px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
.suggestion-desc { font-size: 13px; color: var(--text-muted); margin-bottom: 10px; line-height: 1.45; }

.suggestion-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.chip {
  font-size: 12px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 99px;
}
.chip-cal   { background: var(--green-50);  color: var(--green-700); }
.chip-price { background: #fef3c7; color: #92400e; }
.chip-after { background: var(--bg-subtle, #f5f5f5); color: var(--text-muted); font-weight: 500; }

.suggestion-notes { font-size: 12px; color: var(--text-light); font-style: italic; line-height: 1.4; }

.disclaimer {
  font-size: 11px;
  color: var(--text-light);
  margin-top: 12px;
  line-height: 1.5;
}

.limit-card {
  text-align: center;
  padding: 18px;
  color: var(--text-muted);
  font-size: 14px;
  margin-top: 8px;
}

.ml-8 { margin-left: 8px; }
</style>
