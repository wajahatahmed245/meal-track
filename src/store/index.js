import { reactive, computed } from 'vue'
import { api } from '../api.js'

const EMPTY_EXERCISE = { id: null, completed: false, type: '', duration_minutes: 30, calories_burned: 0, time: '06:00' }

function mapExercise(ex) {
  if (!ex) return { ...EMPTY_EXERCISE }
  return { ...ex, type: ex.exercise_type || ex.type || '' }
}

function mapWeeklyDay(d) {
  return { ...d, isToday: d.is_today }
}

export const store = reactive({
  user:        { name: 'Wajahat Ahmed', calorie_goal: 2000, water_goal_ml: 2500, exercise_goal_days: 4 },
  meals:       [],
  drinks:      [],
  exercise:    { ...EMPTY_EXERCISE },
  weeklyTrend: [],
  loading:     false,

  // ── Computed getters ──────────────────────────────────────────
  get totalCalories()  { return this.meals.reduce((s, m) => s + m.calories, 0) },
  get totalWaterMl()   { return this.drinks.reduce((s, d) => s + d.amount_ml, 0) },
  get caloriesBurned() { return this.exercise.completed ? (this.exercise.calories_burned || 0) : 0 },
  get netCalories()    { return this.totalCalories - this.caloriesBurned },
  get mealsLogged()    { return new Set(this.meals.map(m => m.meal_type)).size },
  get caloriePct()     { return Math.min(Math.round((this.totalCalories / this.user.calorie_goal) * 100), 100) },
  get waterPct()       { return Math.min(Math.round((this.totalWaterMl  / this.user.water_goal_ml)  * 100), 100) },

  get groupedMeals() {
    const groups = {}
    this.meals.forEach(m => {
      if (!groups[m.meal_type]) groups[m.meal_type] = { time: m.time, items: [], total: 0 }
      groups[m.meal_type].items.push(m)
      groups[m.meal_type].total += m.calories
    })
    return groups
  },

  // ── User ─────────────────────────────────────────────────────
  async updateMe(data) {
    const updated = await api.updateMe(data)
    Object.assign(this.user, updated)
  },

  // ── Bootstrap ─────────────────────────────────────────────────
  async loadToday() {
    this.loading = true
    try {
      const [summary, weekly, user] = await Promise.all([
        api.getTodaySummary(),
        api.getWeeklySummary(),
        api.getMe(),
      ])
      this.user        = user
      this.meals       = summary.meals
      this.drinks      = summary.drinks
      this.exercise    = mapExercise(summary.exercise)
      this.weeklyTrend = weekly.days.map(mapWeeklyDay)
    } finally {
      this.loading = false
    }
  },

  // ── Meals ────────────────────────────────────────────────────
  async addMeal(entry) {
    const created = await api.addMeal(entry)
    this.meals.push(created)
    this._syncWeeklyToday()
  },

  async updateMeal(id, patch) {
    const updated = await api.updateMeal(id, patch)
    const idx = this.meals.findIndex(m => m.id === id)
    if (idx !== -1) this.meals[idx] = updated
    this._syncWeeklyToday()
  },

  async deleteMeal(id) {
    await api.deleteMeal(id)
    this.meals = this.meals.filter(m => m.id !== id)
    this._syncWeeklyToday()
  },

  // ── Drinks ───────────────────────────────────────────────────
  async addDrink(entry) {
    const created = await api.addDrink(entry)
    this.drinks.push(created)
  },

  async deleteDrink(id) {
    await api.deleteDrink(id)
    this.drinks = this.drinks.filter(d => d.id !== id)
  },

  // ── Exercise ─────────────────────────────────────────────────
  async toggleExercise() {
    if (!this.exercise.id) return
    const updated = await api.updateExercise(this.exercise.id, { completed: !this.exercise.completed })
    this.exercise = mapExercise(updated)
  },

  async setExercise(data) {
    const payload = {
      exercise_type:    data.type,
      duration_minutes: data.duration_minutes,
      calories_burned:  data.calories_burned,
      time:             data.time,
      completed:        true,
    }
    if (this.exercise.id) {
      const updated = await api.updateExercise(this.exercise.id, payload)
      this.exercise = mapExercise(updated)
    } else {
      const created = await api.logExercise({ ...payload, date: todayStr() })
      this.exercise = mapExercise(created)
    }
  },

  // ── Helpers ──────────────────────────────────────────────────
  _syncWeeklyToday() {
    const entry = this.weeklyTrend.find(d => d.isToday)
    if (entry) entry.calories = this.totalCalories
  },
})

function todayStr() {
  // Use PKT (UTC+5) date, not UTC — server is also configured for Asia/Karachi
  const pkt = new Date(Date.now() + 5 * 60 * 60 * 1000)
  return pkt.toISOString().split('T')[0]
}

// Keep these named exports so existing views importing them still work
export const totalCalories  = computed(() => store.meals.reduce((s, m) => s + m.calories, 0))
export const totalWaterMl   = computed(() => store.drinks.reduce((s, d) => s + d.amount_ml, 0))
export const caloriesBurned = computed(() => store.exercise.completed ? (store.exercise.calories_burned || 0) : 0)
export const netCalories    = computed(() => totalCalories.value - caloriesBurned.value)
export const mealsLogged    = computed(() => new Set(store.meals.map(m => m.meal_type)).size)
export const caloriePct     = computed(() => Math.min(Math.round((totalCalories.value / store.user.calorie_goal) * 100), 100))
export const waterPct       = computed(() => Math.min(Math.round((totalWaterMl.value  / store.user.water_goal_ml)  * 100), 100))
export const groupedMeals   = computed(() => {
  const groups = {}
  store.meals.forEach(m => {
    if (!groups[m.meal_type]) groups[m.meal_type] = { time: m.time, items: [], total: 0 }
    groups[m.meal_type].items.push(m)
    groups[m.meal_type].total += m.calories
  })
  return groups
})
