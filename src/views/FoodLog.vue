<template>
  <div class="page-content">
    <div class="page-header">
      <h1 class="page-title">🍽️ Food Log</h1>
      <div class="date-nav">
        <button class="btn btn-outline btn-sm" @click="prevDay">‹ Prev</button>
        <span class="date-label">{{ dateLabel }}</span>
        <button class="btn btn-outline btn-sm" @click="nextDay" :disabled="isToday">Next ›</button>
      </div>
    </div>

    <!-- Summary bar -->
    <div class="summary-bar card">
      <div class="summary-item">
        <span class="s-icon">🔥</span>
        <div><div class="s-val">{{ dayTotalCal.toLocaleString() }}</div><div class="s-label">Calories</div></div>
      </div>
      <div class="summary-sep" />
      <div class="summary-item">
        <span class="s-icon">🍽️</span>
        <div><div class="s-val">{{ dayMeals.length }}</div><div class="s-label">Items</div></div>
      </div>
      <div class="summary-sep" />
      <div class="summary-item">
        <span class="s-icon">💧</span>
        <div><div class="s-val">{{ (dayTotalWater / 1000).toFixed(1) }}L</div><div class="s-label">Water</div></div>
      </div>
      <div class="summary-sep" />
      <div class="summary-item">
        <span class="s-icon">{{ dayExerciseDone ? '✅' : '⬜' }}</span>
        <div><div class="s-val">{{ dayExerciseDone ? 'Done' : 'None' }}</div><div class="s-label">Exercise</div></div>
      </div>
    </div>

    <!-- Meal sections -->
    <div class="meal-sections">
      <div v-for="mealType in mealTypeOrder" :key="mealType" class="meal-section card">
        <div class="meal-section-header">
          <span class="ms-icon">{{ mealTypeEmoji[mealType] || '🍽️' }}</span>
          <span class="ms-name">{{ mealType }}</span>
          <span v-if="dayGrouped[mealType]" class="ms-cal">{{ dayGrouped[mealType].total }} cal</span>
          <button class="btn btn-secondary btn-sm" style="margin-left: auto;" @click="openModal(mealType)">+ Add</button>
        </div>

        <div v-if="dayGrouped[mealType]" class="ms-items">
          <div v-for="item in dayGrouped[mealType].items" :key="item.id" class="ms-item">
            <span class="ms-emoji">{{ item.emoji }}</span>
            <span class="ms-item-name">{{ item.name }}</span>
            <span class="ms-item-cal">{{ item.calories }} cal</span>
            <div class="ms-actions">
              <button class="icon-btn" @click="editItem = item; showModal = true">✏️</button>
              <button class="icon-btn del" @click="removeMeal(item.id)">🗑️</button>
            </div>
          </div>
        </div>
        <div v-else class="ms-empty">Nothing logged for {{ mealType.toLowerCase() }} yet</div>
      </div>
    </div>

    <MealModal v-if="showModal" :entry="editItem" @save="save" @close="showModal = false" />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { store } from '../store/index.js'
import { api }   from '../api.js'
import MealModal from '../components/MealModal.vue'
import { mealTypeEmoji, mealTypeOrder as mto } from '../data/mock.js'

const mealTypeOrder = Object.keys(mto).sort((a, b) => mto[a] - mto[b])

const offset = ref(0)
const isToday = computed(() => offset.value === 0)

const dayMeals    = ref([])
const dayDrinks   = ref([])
const dayExercise = ref(null)

// Returns YYYY-MM-DD in PKT (UTC+5). offsetDays shifts by that many calendar days.
function pktDateStr(offsetDays = 0) {
  const pkt = new Date(Date.now() + 5 * 60 * 60 * 1000)
  pkt.setUTCDate(pkt.getUTCDate() + offsetDays)
  return pkt.toISOString().split('T')[0]
}

const targetDate = computed(() => pktDateStr(offset.value))

const dateLabel = computed(() => {
  if (offset.value === 0)  return 'Today'
  if (offset.value === -1) return 'Yesterday'
  const d = new Date(pktDateStr(offset.value) + 'T00:00:00Z')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
})

const prevDay = () => { offset.value-- }
const nextDay = () => { if (offset.value < 0) offset.value++ }

// Sync today's slot with the reactive store; fetch past days from API
watch(offset, async () => {
  if (offset.value === 0) {
    dayMeals.value    = store.meals
    dayDrinks.value   = store.drinks
    dayExercise.value = store.exercise
  } else {
    const summary = await api.getDaySummary(targetDate.value)
    dayMeals.value    = summary.meals
    dayDrinks.value   = summary.drinks
    dayExercise.value = summary.exercise
  }
}, { immediate: true })

// Keep today slot live when store updates
watch(() => [store.meals, store.drinks, store.exercise], () => {
  if (offset.value === 0) {
    dayMeals.value    = store.meals
    dayDrinks.value   = store.drinks
    dayExercise.value = store.exercise
  }
}, { deep: true })

const dayTotalCal   = computed(() => dayMeals.value.reduce((s, m) => s + m.calories, 0))
const dayTotalWater = computed(() => dayDrinks.value.reduce((s, d) => s + d.amount_ml, 0))
const dayExerciseDone = computed(() => dayExercise.value?.completed || false)

const dayGrouped = computed(() => {
  const groups = {}
  dayMeals.value.forEach(m => {
    if (!groups[m.meal_type]) groups[m.meal_type] = { time: m.time, items: [], total: 0 }
    groups[m.meal_type].items.push(m)
    groups[m.meal_type].total += m.calories
  })
  return groups
})

const showModal   = ref(false)
const editItem    = ref(null)
const defaultMeal = ref('Breakfast')

function openModal(mealType) {
  defaultMeal.value = mealType
  editItem.value    = null
  showModal.value   = true
}

async function save(data) {
  const entry = { ...data, meal_type: data.meal_type || defaultMeal.value, date: targetDate.value }
  if (editItem.value) {
    if (offset.value === 0) {
      await store.updateMeal(editItem.value.id, entry)
    } else {
      const updated = await api.updateMeal(editItem.value.id, entry)
      const idx = dayMeals.value.findIndex(m => m.id === editItem.value.id)
      if (idx !== -1) dayMeals.value[idx] = updated
    }
  } else {
    if (offset.value === 0) {
      await store.addMeal(entry)
    } else {
      const created = await api.addMeal(entry)
      dayMeals.value.push(created)
    }
  }
  showModal.value = false
  editItem.value  = null
}

async function removeMeal(id) {
  if (offset.value === 0) {
    await store.deleteMeal(id)
  } else {
    await api.deleteMeal(id)
    dayMeals.value = dayMeals.value.filter(m => m.id !== id)
  }
}
</script>

<style scoped>
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px; margin-bottom: 20px;
}
.page-title { font-size: 22px; font-weight: 700; }
.date-nav { display: flex; align-items: center; gap: 10px; }
.date-label { font-size: 14px; font-weight: 600; color: var(--text); min-width: 80px; text-align: center; }

.summary-bar {
  display: flex; align-items: center;
  padding: 16px 20px; margin-bottom: 20px; gap: 0;
}
.summary-item { display: flex; align-items: center; gap: 10px; flex: 1; }
.s-icon { font-size: 22px; }
.s-val  { font-size: 18px; font-weight: 800; color: var(--text); }
.s-label{ font-size: 11px; color: var(--text-muted); }
.summary-sep { width: 1px; height: 32px; background: var(--border-light); margin: 0 4px; }

.meal-sections { display: flex; flex-direction: column; gap: 14px; }
.meal-section { overflow: hidden; }
.meal-section-header {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 18px; border-bottom: 1px solid var(--border-light);
}
.ms-icon { font-size: 18px; }
.ms-name { font-size: 14px; font-weight: 600; }
.ms-cal  { font-size: 13px; font-weight: 700; color: var(--orange-500);
           background: var(--orange-50); padding: 2px 8px; border-radius: 10px; }

.ms-items { padding: 8px 12px 12px; display: flex; flex-direction: column; gap: 4px; }
.ms-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 10px; border-radius: var(--radius-xs);
  border: 1px solid var(--border-light); background: #fff;
  transition: background 0.12s;
}
.ms-item:hover { background: var(--bg); }
.ms-emoji     { font-size: 17px; }
.ms-item-name { flex: 1; font-size: 13px; }
.ms-item-cal  { font-size: 12px; font-weight: 600; color: var(--orange-500); }
.ms-actions   { display: flex; gap: 4px; opacity: 0; transition: opacity 0.12s; }
.ms-item:hover .ms-actions { opacity: 1; }
.icon-btn {
  width: 26px; height: 26px; display: flex; align-items: center; justify-content: center;
  border-radius: 6px; font-size: 12px; border: 1px solid var(--border);
  cursor: pointer; background: #fff; transition: all 0.12s;
}
.icon-btn:hover { background: var(--green-50); }
.icon-btn.del:hover { background: #fff0f0; }
.ms-empty { padding: 12px 18px; font-size: 13px; color: var(--text-light); }
</style>
