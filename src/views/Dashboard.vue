<template>
  <div class="page-content dashboard">
    <!-- ── Header ─────────────────────────────────────────── -->
    <div class="dash-header">
      <div class="dash-greeting">
        <h1 class="greeting-text">{{ greeting }}, {{ store.user.name.split(' ')[0] }}! 👋</h1>
        <p class="greeting-sub">Fuel your day, one healthy choice at a time.</p>
      </div>
      <div class="dash-date-block">
        <div class="dash-date">{{ formattedDate }}</div>
        <div class="dash-day">{{ formattedDay }}</div>
      </div>
    </div>

    <!-- ── Metric Cards ────────────────────────────────────── -->
    <div class="metrics-row">
      <MetricCard
        icon="🔥"
        :value="totalCalories.toLocaleString()"
        :sub="`/ ${store.user.calorie_goal.toLocaleString()} kcal goal · ${caloriePct}%`"
        label="Calories Consumed"
        color="orange"
      />
      <MetricCard
        icon="🍽️"
        :value="mealsLogged"
        sub="meal types logged"
        label="Meals Logged"
        color="purple"
      />
      <MetricCard
        icon="💧"
        :value="(totalWaterMl / 1000).toFixed(1)"
        unit="L"
        :sub="`/ ${(store.user.water_goal_ml / 1000).toFixed(1)}L goal · ${waterPct}%`"
        label="Water Intake"
        color="blue"
      />
      <MetricCard
        :icon="store.exercise.completed ? '✅' : '❌'"
        :value="store.exercise.completed ? 'Completed' : 'Not Yet'"
        :sub="store.exercise.completed ? `${store.exercise.type}, ${store.exercise.duration_minutes} min` : 'Mark your workout'"
        label="Exercise"
        color="green"
      />
    </div>

    <!-- ── Main Grid ───────────────────────────────────────── -->
    <div class="dash-grid">
      <!-- Left column: Food Log + Quick Add -->
      <div class="dash-left">
        <div class="card dash-log-card">
          <div class="section-title" style="padding: 20px 20px 0;">
            <span>🗓️ Today's Food &amp; Drink Log</span>
            <button class="btn btn-primary btn-sm" @click="openAddModal">+ Add Food</button>
          </div>
          <div class="log-scroll">
            <FoodTimeline
              :groups="groupedMeals"
              @edit="openEditModal"
              @delete="deleteMeal"
            />

            <!-- Drink entries -->
            <div v-if="store.drinks.length > 0" class="drink-section">
              <div class="drink-header">
                <span>💧</span>
                <span>Drinks Today</span>
                <span class="group-total">{{ (totalWaterMl / 1000).toFixed(1) }}L</span>
              </div>
              <div class="drink-pills">
                <span
                  v-for="d in store.drinks"
                  :key="d.id"
                  class="drink-pill"
                >
                  {{ d.emoji }} {{ d.name }}
                  <span class="drink-ml">{{ d.amount_ml }}ml</span>
                  <span class="drink-time">{{ d.time }}</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        <QuickAddPanel @logged="addMeal" @add-drink="openDrinkModal" />
      </div>

      <!-- Right column: Progress + Chart + Insights -->
      <div class="dash-right">
        <CalorieProgress
          :consumed="totalCalories"
          :burned="caloriesBurned"
          :goal="store.user.calorie_goal"
        />
        <MealDistributionChart :groups="groupedMeals" />
        <WeeklyChart
          :data="store.weeklyTrend"
          :goal="store.user.calorie_goal"
        />
        <InsightsPanel :items="store.insights" />
      </div>
    </div>

    <!-- ── Modals ──────────────────────────────────────────── -->
    <MealModal
      v-if="showMealModal"
      :entry="editingEntry"
      @save="saveMeal"
      @close="closeMealModal"
    />

    <!-- Drink quick-add modal -->
    <div v-if="showDrinkModal" class="overlay-backdrop" @click.self="showDrinkModal = false">
      <div class="modal-sheet">
        <div class="modal-header">
          <h2 class="modal-title">💧 Log a Drink</h2>
          <button class="close-btn" @click="showDrinkModal = false">✕</button>
        </div>
        <div class="form-group">
          <label class="form-label">Drink Name</label>
          <input class="form-input" v-model="drinkForm.name" placeholder="Water, Tea, Juice…" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Amount (ml)</label>
            <input class="form-input" v-model.number="drinkForm.amount_ml" type="number" min="1" placeholder="500" />
          </div>
          <div class="form-group">
            <label class="form-label">Emoji</label>
            <input class="form-input" v-model="drinkForm.emoji" placeholder="💧" maxlength="2" />
          </div>
        </div>
        <div class="drink-presets">
          <button
            v-for="p in drinkPresets"
            :key="p.label"
            class="preset-btn"
            @click="drinkForm = { ...p }"
          >{{ p.emoji }} {{ p.label }}</button>
        </div>
        <div class="modal-actions">
          <button class="btn btn-outline" @click="showDrinkModal = false">Cancel</button>
          <button class="btn btn-blue" @click="addDrink" :disabled="!drinkForm.name || !drinkForm.amount_ml">
            Log Drink
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { store, totalCalories, totalWaterMl, mealsLogged, caloriePct, waterPct, caloriesBurned, groupedMeals } from '../store/index.js'
import MetricCard             from '../components/MetricCard.vue'
import FoodTimeline           from '../components/FoodTimeline.vue'
import QuickAddPanel          from '../components/QuickAddPanel.vue'
import CalorieProgress        from '../components/CalorieProgress.vue'
import WeeklyChart            from '../components/WeeklyChart.vue'
import MealDistributionChart  from '../components/MealDistributionChart.vue'
import InsightsPanel          from '../components/InsightsPanel.vue'
import MealModal              from '../components/MealModal.vue'

// ── Greeting ──────────────────────────────────
const greeting = computed(() => {
  const h = new Date(Date.now() + 5 * 60 * 60 * 1000).getUTCHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  if (h < 20) return 'Good evening'
  return 'Good night'
})

const formattedDate = computed(() => {
  const d = new Date(Date.now() + 5 * 60 * 60 * 1000)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
})

const formattedDay = computed(() => {
  const d = new Date(Date.now() + 5 * 60 * 60 * 1000)
  return d.toLocaleDateString('en-US', { weekday: 'long', timeZone: 'UTC' })
})

// ── Meal modal ────────────────────────────────
const showMealModal = ref(false)
const editingEntry  = ref(null)

const openAddModal  = () => { editingEntry.value = null;  showMealModal.value = true }
const openEditModal = (entry) => { editingEntry.value = entry; showMealModal.value = true }
const closeMealModal = () => { showMealModal.value = false; editingEntry.value = null }

function saveMeal(data) {
  if (editingEntry.value) {
    store.updateMeal(editingEntry.value.id, data)
  } else {
    store.addMeal(data)
  }
  closeMealModal()
}

function deleteMeal(id) {
  store.deleteMeal(id)
}

function addMeal(data) {
  store.addMeal(data)
}

// ── Drink modal ───────────────────────────────
const showDrinkModal = ref(false)
const drinkForm = ref({ name: 'Water', amount_ml: 250, emoji: '💧' })

const drinkPresets = [
  { name: 'Water',     amount_ml: 250,  emoji: '💧', label: 'Water 250ml' },
  { name: 'Water',     amount_ml: 500,  emoji: '💧', label: 'Water 500ml' },
  { name: 'Green Tea', amount_ml: 240,  emoji: '🍵', label: 'Green Tea' },
  { name: 'Coffee',    amount_ml: 240,  emoji: '☕', label: 'Coffee' },
  { name: 'Juice',     amount_ml: 250,  emoji: '🍹', label: 'Juice' },
]

function openDrinkModal() {
  drinkForm.value = { name: 'Water', amount_ml: 250, emoji: '💧' }
  showDrinkModal.value = true
}

function addDrink() {
  store.addDrink({
    ...drinkForm.value,
    time: new Date(Date.now() + 5 * 60 * 60 * 1000).toISOString().substr(11, 5),
  })
  showDrinkModal.value = false
}
</script>

<style scoped>
.dashboard { padding-bottom: 32px; }

/* Header */
.dash-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.greeting-text {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.2;
}
.greeting-sub { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

.dash-date-block { text-align: right; }
.dash-date { font-size: 14px; font-weight: 600; color: var(--text); }
.dash-day  { font-size: 12px; color: var(--text-muted); }

/* Metric cards */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  margin-bottom: 24px;
}
@media (min-width: 900px) {
  .metrics-row { grid-template-columns: repeat(4, 1fr); }
}

/* Main grid */
.dash-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}
@media (min-width: 1100px) {
  .dash-grid { grid-template-columns: 1.3fr 1fr; }
}

.dash-left  { display: flex; flex-direction: column; gap: 16px; }
.dash-right { display: flex; flex-direction: column; gap: 16px; }

/* Log card */
.dash-log-card { overflow: hidden; }
.log-scroll {
  padding: 16px 20px 20px;
  max-height: 480px;
  overflow-y: auto;
}

/* Drink section */
.drink-section { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--border-light); }
.drink-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 10px;
}
.drink-header .group-total {
  margin-left: auto;
  font-size: 12px;
  font-weight: 700;
  color: var(--blue-500);
  background: var(--blue-50);
  padding: 2px 8px;
  border-radius: 10px;
}
.drink-pills { display: flex; flex-wrap: wrap; gap: 6px; }
.drink-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--blue-50);
  color: var(--blue-600);
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}
.drink-ml   { font-weight: 700; }
.drink-time { color: var(--text-light); font-size: 11px; }

/* Drink modal extras */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.modal-title { font-size: 18px; font-weight: 700; }
.close-btn {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-muted);
  border: 1px solid var(--border);
  cursor: pointer;
  background: #fff;
}
.close-btn:hover { background: #f8fafc; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; padding-top: 4px; }

.drink-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.preset-btn {
  padding: 6px 12px;
  border-radius: 20px;
  border: 1.5px solid var(--blue-100);
  background: var(--blue-50);
  color: var(--blue-600);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.13s var(--ease);
}
.preset-btn:hover { background: var(--blue-100); border-color: var(--blue-500); }
</style>
