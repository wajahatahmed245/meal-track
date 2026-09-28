<template>
  <div class="page-content">
    <!-- Header + date nav -->
    <div class="page-header">
      <h1 class="page-title">🤖 Artificial Intelligence Evaluation</h1>
      <div class="date-nav">
        <button class="btn btn-outline btn-sm" @click="prevDay">‹ Prev</button>
        <span class="date-label">{{ dateLabel }}</span>
        <button class="btn btn-outline btn-sm" @click="nextDay" :disabled="isToday">Next ›</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="status-card card">
      <div class="status-spinner">⏳</div>
      <div class="status-text">Running AI evaluation…</div>
      <div class="status-sub">This may take a few seconds</div>
    </div>

    <!-- No meals logged -->
    <div v-else-if="noMeals" class="status-card card">
      <div class="status-icon">🍽️</div>
      <div class="status-text">No meals logged</div>
      <div class="status-sub">No food was logged for {{ dateLabel }}. Log meals first to generate an AI evaluation.</div>
    </div>

    <!-- API / Gemini error -->
    <div v-else-if="errorMsg" class="status-card card error-card">
      <div class="status-icon">⚠️</div>
      <div class="status-text">Evaluation failed</div>
      <div class="status-sub">{{ errorMsg }}</div>
      <button class="btn btn-primary mt-12" @click="runEvaluation(false)">Try Again</button>
    </div>

    <!-- No evaluation yet -->
    <div v-else-if="!evaluation" class="status-card card">
      <div class="status-icon">🤖</div>
      <div class="status-text">No evaluation yet</div>
      <div class="status-sub">AI evaluation has not been generated for {{ dateLabel }}.</div>
      <button class="btn btn-primary mt-12" @click="runEvaluation(false)" :disabled="loading">
        Run AI Evaluation
      </button>
    </div>

    <!-- Evaluation display -->
    <template v-else>
      <!-- Stale warning -->
      <div v-if="isStale" class="stale-banner">
        ⚠️ Meals for this date have changed since this evaluation was generated.
        <button class="btn btn-secondary btn-sm ml-8" @click="confirmReEval">Re-evaluate</button>
      </div>

      <!-- Score card -->
      <div class="card score-card">
        <div class="score-circle" :class="scoreClass">
          <span class="score-num">{{ evaluation.overall_score }}</span>
          <span class="score-denom">/10</span>
        </div>
        <div class="score-right">
          <div class="score-label">Overall Score</div>
          <p class="score-assessment">{{ evaluation.evaluation.overall_assessment }}</p>
          <div class="score-meta">
            <span class="meta-chip">{{ evaluation.trigger_source === 'scheduled' ? '🕐 Auto' : '👆 Manual' }}</span>
            <span class="meta-chip">{{ evaluation.model_name }}</span>
            <span class="meta-chip">Confidence: {{ evaluation.evaluation.confidence }}</span>
            <span class="meta-chip">{{ formatDate(evaluation.updated_at) }}</span>
          </div>
        </div>
      </div>

      <!-- What went well -->
      <div class="card eval-section">
        <h3 class="section-title">✅ What You Did Well</h3>
        <ul class="bullet-list green">
          <li v-for="(item, i) in evaluation.evaluation.what_went_well" :key="i">{{ item }}</li>
        </ul>
      </div>

      <!-- Things to watch -->
      <div class="card eval-section">
        <h3 class="section-title">👀 Things to Watch</h3>
        <ul class="bullet-list orange">
          <li v-for="(item, i) in evaluation.evaluation.things_to_watch" :key="i">{{ item }}</li>
        </ul>
      </div>

      <!-- Meal by meal -->
      <div class="card eval-section">
        <h3 class="section-title">🍽️ Meal-by-Meal Evaluation</h3>
        <div
          v-for="(meal, i) in evaluation.evaluation.meal_evaluations"
          :key="i"
          class="meal-eval-row"
        >
          <div class="meal-eval-header">
            <span class="meal-eval-name">{{ meal.food_name }}</span>
            <span class="meal-eval-meta">{{ meal.meal_type }} · {{ meal.time }} · {{ meal.logged_calories }} kcal</span>
          </div>
          <p class="meal-eval-assessment">{{ meal.assessment }}</p>
          <div class="meal-eval-lists">
            <div v-if="meal.likely_benefits.length" class="mini-list green">
              <div class="mini-list-title">Benefits</div>
              <ul><li v-for="(b, j) in meal.likely_benefits" :key="j">{{ b }}</li></ul>
            </div>
            <div v-if="meal.things_to_watch.length" class="mini-list orange">
              <div class="mini-list-title">Watch</div>
              <ul><li v-for="(w, j) in meal.things_to_watch" :key="j">{{ w }}</li></ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Daily benefits + concerns -->
      <div class="two-col">
        <div class="card eval-section">
          <h3 class="section-title">💚 Daily Benefits</h3>
          <ul class="bullet-list green">
            <li v-for="(item, i) in evaluation.evaluation.daily_benefits" :key="i">{{ item }}</li>
          </ul>
        </div>
        <div class="card eval-section">
          <h3 class="section-title">🔶 Daily Concerns</h3>
          <ul class="bullet-list orange">
            <li v-for="(item, i) in evaluation.evaluation.daily_concerns" :key="i">{{ item }}</li>
          </ul>
        </div>
      </div>

      <!-- Improve tomorrow -->
      <div class="card eval-section">
        <h3 class="section-title">📈 What to Improve Tomorrow</h3>
        <ul class="bullet-list blue">
          <li v-for="(item, i) in evaluation.evaluation.improve_tomorrow" :key="i">{{ item }}</li>
        </ul>
      </div>

      <!-- Reduce/avoid -->
      <div class="card eval-section">
        <h3 class="section-title">⬇️ Reduce or Avoid Repeating Tomorrow</h3>
        <ul class="bullet-list red">
          <li v-for="(item, i) in evaluation.evaluation.reduce_or_avoid_repeating_tomorrow" :key="i">{{ item }}</li>
        </ul>
      </div>

      <!-- Final recommendation -->
      <div class="card eval-section final-rec">
        <h3 class="section-title">💡 Final Recommendation</h3>
        <p class="final-rec-text">{{ evaluation.evaluation.final_recommendation }}</p>
      </div>

      <!-- Re-evaluate -->
      <div class="re-eval-row">
        <button class="btn btn-secondary" @click="confirmReEval" :disabled="loading">
          🔄 Re-evaluate
        </button>
        <span class="re-eval-note">Will call Gemini again and replace this evaluation.</span>
      </div>

      <!-- Re-eval confirm modal -->
      <div v-if="showReEvalConfirm" class="modal-overlay" @click.self="showReEvalConfirm = false">
        <div class="modal-card">
          <h3>Re-evaluate this day?</h3>
          <p>This will call Gemini again and replace the stored evaluation for {{ dateLabel }}. The previous result will be overwritten.</p>
          <div class="modal-actions">
            <button class="btn btn-outline" @click="showReEvalConfirm = false">Cancel</button>
            <button class="btn btn-primary" @click="doReEval">Yes, Re-evaluate</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { api } from '../api.js'
import { useDateNav, pktDateStr } from '../composables/useDateNav.js'

// Default to yesterday (offset -1) — most recently completed day
const { offset, isToday, targetDate, dateLabel, prevDay, nextDay } = useDateNav(-1, 0)

const evaluation       = ref(null)
const loading          = ref(false)
const noMeals          = ref(false)
const errorMsg         = ref('')
const currentInputHash = ref('')
const showReEvalConfirm = ref(false)

const isStale = computed(() => {
  if (!evaluation.value || !currentInputHash.value) return false
  return evaluation.value.input_hash !== currentInputHash.value
})

const scoreClass = computed(() => {
  const s = evaluation.value?.overall_score ?? 0
  if (s >= 8) return 'score-great'
  if (s >= 6) return 'score-good'
  if (s >= 4) return 'score-fair'
  return 'score-poor'
})

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

async function fetchCurrentHash() {
  try {
    const summary = await api.getDaySummary(targetDate.value)
    if (summary.meals && summary.meals.length > 0) {
      // Compute hash client-side (same logic as backend build_input_hash)
      const parts = summary.meals
        .slice()
        .sort((a, b) => a.id - b.id)
        .map(m => `${m.id}|${m.name}|${m.calories}|${m.meal_type}|${m.time}|${m.note || ''}`)
      parts.push(`goal:${summary.calorie_goal}`)
      currentInputHash.value = await sha256(parts.join('\n'))
    } else {
      currentInputHash.value = ''
    }
  } catch {
    currentInputHash.value = ''
  }
}

async function sha256(str) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str))
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('')
}

async function loadEvaluation() {
  loading.value  = false
  noMeals.value  = false
  errorMsg.value = ''
  evaluation.value = null

  try {
    const data = await api.getAiEvaluation(targetDate.value)
    evaluation.value = data
    // Fetch current meal hash in background to detect staleness
    fetchCurrentHash()
  } catch (e) {
    if (e.status === 404) {
      // No evaluation yet — check if meals exist
      try {
        const summary = await api.getDaySummary(targetDate.value)
        noMeals.value = !summary.meals || summary.meals.length === 0
      } catch {
        noMeals.value = false
      }
    } else {
      errorMsg.value = e.message || 'Failed to load evaluation'
    }
  }
}

async function runEvaluation(force) {
  loading.value  = true
  noMeals.value  = false
  errorMsg.value = ''
  try {
    const data = await api.generateAiEvaluation(targetDate.value, force)
    evaluation.value = data
    fetchCurrentHash()
  } catch (e) {
    if (e.status === 422) {
      noMeals.value = true
    } else {
      errorMsg.value = e.message || 'AI evaluation service unavailable. Please try again.'
    }
  } finally {
    loading.value = false
    showReEvalConfirm.value = false
  }
}

function confirmReEval() {
  showReEvalConfirm.value = true
}

function doReEval() {
  runEvaluation(true)
}

watch(offset, () => loadEvaluation(), { immediate: true })
</script>

<style scoped>
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px; margin-bottom: 20px;
}
.page-title { font-size: 22px; font-weight: 700; }
.date-nav { display: flex; align-items: center; gap: 10px; }
.date-label { font-size: 14px; font-weight: 600; color: var(--text); min-width: 80px; text-align: center; }

/* Status cards */
.status-card {
  display: flex; flex-direction: column; align-items: center;
  padding: 48px 24px; text-align: center; gap: 10px;
}
.status-icon  { font-size: 48px; }
.status-spinner { font-size: 36px; animation: spin 1.5s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.status-text  { font-size: 18px; font-weight: 700; color: var(--text); }
.status-sub   { font-size: 13px; color: var(--text-muted); max-width: 360px; }
.error-card   { border: 1px solid #fca5a5; background: #fff8f8; }

.mt-12 { margin-top: 12px; }

/* Stale banner */
.stale-banner {
  background: #fffbeb; border: 1px solid #fcd34d;
  border-radius: var(--radius-xs); padding: 10px 16px;
  font-size: 13px; color: #92400e;
  display: flex; align-items: center; gap: 8px;
  flex-wrap: wrap; margin-bottom: 16px;
}
.ml-8 { margin-left: 8px; }

/* Score card */
.score-card {
  display: flex; align-items: flex-start; gap: 24px;
  padding: 24px; margin-bottom: 16px;
  flex-wrap: wrap;
}
.score-circle {
  display: flex; align-items: baseline; gap: 2px;
  width: 80px; height: 80px; border-radius: 50%;
  justify-content: center; align-items: center;
  flex-shrink: 0; font-weight: 900;
  border: 3px solid currentColor;
}
.score-num   { font-size: 32px; }
.score-denom { font-size: 14px; opacity: 0.7; }
.score-great { color: var(--green-600); background: var(--green-50); }
.score-good  { color: #16a34a; background: #f0fdf4; }
.score-fair  { color: #d97706; background: #fffbeb; }
.score-poor  { color: #dc2626; background: #fff0f0; }

.score-right { flex: 1; }
.score-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 600; }
.score-assessment { font-size: 14px; color: var(--text); margin: 6px 0 10px; line-height: 1.5; }
.score-meta { display: flex; flex-wrap: wrap; gap: 6px; }
.meta-chip {
  font-size: 11px; padding: 2px 8px; border-radius: 10px;
  background: var(--bg); border: 1px solid var(--border-light);
  color: var(--text-muted);
}

/* Section cards */
.eval-section { margin-bottom: 14px; padding: 20px 22px; }
.section-title { font-size: 15px; font-weight: 700; margin: 0 0 12px; }

/* Bullet lists */
.bullet-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }
.bullet-list li { font-size: 13px; line-height: 1.5; padding-left: 20px; position: relative; color: var(--text); }
.bullet-list.green li::before { content: '✓'; position: absolute; left: 0; color: var(--green-600); font-weight: 700; }
.bullet-list.orange li::before { content: '›'; position: absolute; left: 0; color: #d97706; font-weight: 700; }
.bullet-list.blue li::before { content: '→'; position: absolute; left: 0; color: #2563eb; font-weight: 700; }
.bullet-list.red li::before { content: '↓'; position: absolute; left: 0; color: #dc2626; font-weight: 700; }

/* Meal eval rows */
.meal-eval-row {
  border: 1px solid var(--border-light); border-radius: var(--radius-xs);
  padding: 14px; margin-bottom: 10px; background: #fff;
}
.meal-eval-row:last-child { margin-bottom: 0; }
.meal-eval-header { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
.meal-eval-name { font-size: 14px; font-weight: 700; color: var(--text); }
.meal-eval-meta { font-size: 12px; color: var(--text-muted); }
.meal-eval-assessment { font-size: 13px; color: var(--text); line-height: 1.5; margin: 0 0 10px; }
.meal-eval-lists { display: flex; gap: 16px; flex-wrap: wrap; }
.mini-list { flex: 1; min-width: 140px; }
.mini-list-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
.mini-list.green .mini-list-title { color: var(--green-600); }
.mini-list.orange .mini-list-title { color: #d97706; }
.mini-list ul { list-style: disc; padding-left: 16px; margin: 0; }
.mini-list ul li { font-size: 12px; color: var(--text); line-height: 1.5; }

/* Two-column layout */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
@media (max-width: 640px) { .two-col { grid-template-columns: 1fr; } }

/* Final recommendation */
.final-rec-text { font-size: 14px; line-height: 1.6; color: var(--text); margin: 0; font-style: italic; }

/* Re-evaluate row */
.re-eval-row {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 0; flex-wrap: wrap;
}
.re-eval-note { font-size: 12px; color: var(--text-muted); }

/* Confirm modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 200; padding: 20px;
}
.modal-card {
  background: #fff; border-radius: var(--radius); padding: 28px 24px;
  max-width: 400px; width: 100%;
  box-shadow: var(--shadow-lg);
}
.modal-card h3 { font-size: 16px; font-weight: 700; margin: 0 0 10px; }
.modal-card p  { font-size: 13px; color: var(--text-muted); line-height: 1.5; margin: 0 0 20px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; }
</style>
