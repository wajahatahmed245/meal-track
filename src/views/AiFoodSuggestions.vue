<template>
  <div class="page-content">
    <div class="page-header">
      <h1 class="page-title">🍽️ AI Food Suggestions</h1>
      <p class="page-sub">Personalised Pakistani food ideas fitted to your remaining calories</p>
      <router-link to="/ai-evaluation" class="ai-eval-link">🤖 View AI Daily Evaluation →</router-link>
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
        <span v-for="i in LIMIT" :key="i" class="usage-dot" :class="{ used: i <= usageCount }" />
      </div>
      <div class="usage-text">
        <template v-if="usageCount >= LIMIT">All {{ LIMIT }} suggestions used today</template>
        <template v-else>{{ usageCount }} of {{ LIMIT }} AI suggestions used · {{ LIMIT - usageCount }} remaining</template>
      </div>
    </div>

    <!-- Generate button -->
    <button class="btn btn-primary generate-btn" :disabled="generateDisabled" @click="generate">
      <span v-if="generating">⏳ Getting suggestions…</span>
      <span v-else-if="remaining <= 0">✅ Calorie goal reached — no suggestions needed</span>
      <span v-else-if="usageCount >= LIMIT">🚫 Daily limit reached — try again tomorrow</span>
      <span v-else>✨ Get New Suggestions</span>
    </button>

    <!-- Error -->
    <div v-if="errorMsg" class="error-banner">
      ⚠️ {{ errorMsg }}
      <button class="btn btn-sm btn-outline ml-8" @click="errorMsg = ''">Dismiss</button>
    </div>

    <!-- Loading saved sessions -->
    <div v-if="loadingStatus" class="sessions-loading">Loading saved suggestions…</div>

    <!-- No sessions yet -->
    <div v-else-if="!loadingStatus && sessions.length === 0 && !generating" class="empty-state card">
      <div class="empty-icon">🍽️</div>
      <div class="empty-text">No suggestions generated yet today.</div>
      <div class="empty-sub">Press "Get New Suggestions" above to generate your first set.</div>
    </div>

    <!-- Latest session (top) -->
    <div v-if="latestSession" class="session-block">
      <div class="session-header">
        <span class="session-title">Latest suggestions</span>
        <span class="session-meta">
          Generated at {{ formatTime(latestSession.generated_at) }}
          · Request {{ latestSession.request_number }}/{{ LIMIT }}
        </span>
      </div>
      <p class="session-snapshot">
        At generation: {{ latestSession.consumed_snapshot }} consumed / {{ latestSession.daily_goal_snapshot }} goal
        · <strong>{{ latestSession.remaining_snapshot }} kcal remaining</strong>
      </p>

      <div
        v-for="item in latestSession.items"
        :key="item.id"
        class="card suggestion-card"
        :class="tagClass(item.category_tag)"
      >
        <div class="suggestion-badge">{{ TAG_LABELS[item.category_tag] || item.category_tag }}</div>
        <div class="suggestion-name">{{ item.name }}</div>
        <div class="suggestion-desc">{{ item.description }}</div>
        <!-- Component breakdown -->
        <ul v-if="item.components && item.components.length" class="component-list">
          <li v-for="(c, ci) in item.components" :key="ci" class="component-row">
            <span class="component-name">{{ c.item }}</span>
            <span class="component-cal">{{ c.calories }} kcal</span>
          </li>
        </ul>
        <div class="suggestion-chips">
          <span class="chip chip-cal">Total ~{{ item.estimated_calories }} kcal</span>
          <span class="chip chip-price">Est. PKR {{ item.price_min_pkr }}–{{ item.price_max_pkr }}</span>
          <span class="chip chip-after">After eating: {{ item.calories_after }} / {{ latestSession.daily_goal_snapshot }} kcal</span>
        </div>
        <div v-if="item.notes" class="suggestion-notes">{{ item.notes }}</div>
      </div>

      <p class="disclaimer">
        * Calorie and price estimates are approximate. Prices reflect typical Lahore market rates (2026) and may vary by vendor.
      </p>
    </div>

    <!-- Earlier sessions today (collapsible) -->
    <div v-if="earlierSessions.length > 0" class="earlier-section">
      <button class="earlier-toggle" @click="showEarlier = !showEarlier">
        {{ showEarlier ? '▾' : '▸' }}
        Earlier today ({{ earlierSessions.length }} session{{ earlierSessions.length > 1 ? 's' : '' }})
      </button>

      <div v-if="showEarlier">
        <div v-for="sess in earlierSessions" :key="sess.id" class="session-block earlier">
          <div class="session-header">
            <span class="session-title">Request {{ sess.request_number }}/{{ LIMIT }}</span>
            <span class="session-meta">{{ formatTime(sess.generated_at) }}</span>
          </div>
          <p class="session-snapshot">
            At generation: {{ sess.consumed_snapshot }} / {{ sess.daily_goal_snapshot }} kcal
            · {{ sess.remaining_snapshot }} kcal remaining
          </p>
          <div
            v-for="item in sess.items"
            :key="item.id"
            class="card suggestion-card suggestion-card-sm"
            :class="tagClass(item.category_tag)"
          >
            <div class="suggestion-badge">{{ TAG_LABELS[item.category_tag] || item.category_tag }}</div>
            <div class="suggestion-name">{{ item.name }}</div>
            <ul v-if="item.components && item.components.length" class="component-list component-list-sm">
              <li v-for="(c, ci) in item.components" :key="ci" class="component-row">
                <span class="component-name">{{ c.item }}</span>
                <span class="component-cal">{{ c.calories }} kcal</span>
              </li>
            </ul>
            <div class="suggestion-chips">
              <span class="chip chip-cal">Total ~{{ item.estimated_calories }} kcal</span>
              <span class="chip chip-price">PKR {{ item.price_min_pkr }}–{{ item.price_max_pkr }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Limit reached -->
    <div v-if="usageCount >= LIMIT && !generating && sessions.length > 0" class="limit-card card">
      🚫 You've used all {{ LIMIT }} AI food suggestions for today. Try again tomorrow!
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'

const LIMIT = 5

const TAG_LABELS = {
  budget:     '💰 Budget',
  balanced:   '🍛 Balanced',
  restaurant: '🏪 Restaurant',
  snack:      '🫖 Snack',
  protein:    '💪 High Protein',
}

const loadingStatus = ref(true)
const generating    = ref(false)
const errorMsg      = ref('')
const showEarlier   = ref(false)

const dailyGoal  = ref(2000)
const consumed   = ref(0)
const usageCount = ref(0)
const sessions   = ref([])   // all today's sessions, newest first

const remaining   = computed(() => Math.max(0, dailyGoal.value - consumed.value))
const consumedPct = computed(() => dailyGoal.value > 0 ? Math.round((consumed.value / dailyGoal.value) * 100) : 0)

const remainingClass = computed(() => {
  if (remaining.value <= 0) return 'cal-zero'
  if (remaining.value < 200) return 'cal-low'
  return 'cal-ok'
})

const generateDisabled = computed(() =>
  generating.value || remaining.value <= 0 || usageCount.value >= LIMIT
)

const latestSession  = computed(() => sessions.value[0] ?? null)
const earlierSessions = computed(() => sessions.value.slice(1))

function tagClass(tag) {
  const map = {
    budget: 'card-budget',
    balanced: 'card-balanced',
    restaurant: 'card-restaurant',
    snack: 'card-snack',
    protein: 'card-protein',
  }
  return map[tag] || ''
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  const dt = new Date(isoStr)
  return dt.toLocaleTimeString('en-PK', { hour: '2-digit', minute: '2-digit', hour12: true })
}

async function loadAll() {
  loadingStatus.value = true
  try {
    const [summary, todaySessions] = await Promise.all([
      api.getTodaySummary(),
      api.getTodayFoodSuggestionSessions(),
    ])
    dailyGoal.value  = summary.calorie_goal
    consumed.value   = summary.total_calories
    sessions.value   = todaySessions.sessions ?? []
    usageCount.value = todaySessions.requests_used_today
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
    // Prepend new session to the list
    sessions.value   = [data.session, ...sessions.value]
    usageCount.value = data.requests_used_today
  } catch (e) {
    if (e?.status === 429) {
      usageCount.value = LIMIT
      errorMsg.value = e?.message || 'Daily limit reached. Try again tomorrow.'
    } else {
      errorMsg.value = e?.message || 'AI service is temporarily unavailable. Please try again.'
    }
  } finally {
    generating.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.page-sub {
  color: var(--text-muted);
  font-size: 14px;
  margin-top: 4px;
}

.ai-eval-link {
  display: inline-block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--green-600);
  font-weight: 600;
  text-decoration: none;
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
.calorie-bar-fill { height: 100%; border-radius: 99px; transition: width 0.4s ease; background: var(--green-500); }
.calorie-bar-fill.cal-low  { background: #d97706; }
.calorie-bar-fill.cal-zero { background: var(--text-muted); }
.calorie-bar-label { font-size: 11px; color: var(--text-light); margin-top: 6px; }

/* Usage indicator */
.usage-row { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
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
.generate-btn { width: 100%; justify-content: center; padding: 14px; font-size: 15px; margin-bottom: 16px; }

/* Error */
.error-banner {
  display: flex; align-items: center; gap: 8px;
  background: #fff7ed; border: 1px solid #fed7aa; color: #c2410c;
  border-radius: var(--radius-sm); padding: 12px 14px;
  font-size: 13px; margin-bottom: 16px; flex-wrap: wrap;
}

/* Empty state */
.sessions-loading { text-align: center; color: var(--text-muted); padding: 24px; font-size: 14px; }
.empty-state {
  text-align: center; padding: 32px 20px;
}
.empty-icon { font-size: 36px; margin-bottom: 10px; }
.empty-text { font-size: 15px; font-weight: 600; color: var(--text); margin-bottom: 6px; }
.empty-sub  { font-size: 13px; color: var(--text-muted); }

/* Session block */
.session-block { margin-bottom: 20px; }
.session-block.earlier { opacity: 0.85; }

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 4px;
  flex-wrap: wrap;
  gap: 4px;
}
.session-title { font-size: 15px; font-weight: 700; color: var(--text); }
.session-meta  { font-size: 12px; color: var(--text-muted); }
.session-snapshot { font-size: 13px; color: var(--text-muted); margin-bottom: 10px; line-height: 1.4; }

/* Suggestion cards */
.suggestion-card { padding: 16px; margin-bottom: 10px; border-left: 4px solid var(--border); }
.suggestion-card-sm { padding: 12px; }
.card-budget     { border-left-color: var(--green-500); }
.card-balanced   { border-left-color: var(--orange-500); }
.card-restaurant { border-left-color: #6366f1; }
.card-snack      { border-left-color: #0ea5e9; }
.card-protein    { border-left-color: #ef4444; }

.suggestion-badge {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--text-light); margin-bottom: 6px;
}
.suggestion-name { font-size: 16px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
.suggestion-desc { font-size: 13px; color: var(--text-muted); margin-bottom: 10px; line-height: 1.45; }

/* Component breakdown */
.component-list {
  list-style: none;
  margin: 0 0 10px;
  padding: 0;
  border-left: 2px solid var(--border-light);
  padding-left: 10px;
}
.component-list-sm { margin-bottom: 8px; }
.component-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  padding: 2px 0;
  font-size: 13px;
  color: var(--text-muted);
}
.component-name { flex: 1; line-height: 1.35; }
.component-cal  { font-weight: 600; white-space: nowrap; color: var(--text-light); font-size: 12px; }

.suggestion-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.chip { font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 99px; }
.chip-cal   { background: var(--green-50);  color: var(--green-700); }
.chip-price { background: #fef3c7; color: #92400e; }
.chip-after { background: var(--bg-subtle, #f5f5f5); color: var(--text-muted); font-weight: 500; }

.suggestion-notes { font-size: 12px; color: var(--text-light); font-style: italic; line-height: 1.4; }

.disclaimer { font-size: 11px; color: var(--text-light); margin-top: 12px; line-height: 1.5; }

/* Earlier sessions */
.earlier-section { margin-top: 4px; }
.earlier-toggle {
  width: 100%; text-align: left;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 10px 14px;
  font-size: 13px; font-weight: 600; color: var(--text-muted);
  cursor: pointer; margin-bottom: 12px;
}
.earlier-toggle:hover { background: var(--bg-hover, #f9f9f9); }

.limit-card { text-align: center; padding: 18px; color: var(--text-muted); font-size: 14px; margin-top: 8px; }
.ml-8 { margin-left: 8px; }
</style>
