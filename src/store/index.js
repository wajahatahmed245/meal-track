import { reactive, computed } from 'vue'
import {
  mockUser, todayMeals, todayDrinks, todayExercise,
  weeklyTrend, insights,
} from '../data/mock.js'

export const store = reactive({
  // Populated below — defined first so computed refs can reference it
  user:        { ...mockUser },
  meals:       todayMeals.map(m => ({ ...m })),
  drinks:      todayDrinks.map(d => ({ ...d })),
  exercise:    { ...todayExercise },
  weeklyTrend: weeklyTrend.map(d => ({ ...d })),
  insights:    [...insights],

  // ── Computed getters ──────────────────────
  get totalCalories()  { return this.meals.reduce((s, m) => s + m.calories, 0) },
  get totalWaterMl()   { return this.drinks.reduce((s, d) => s + d.amount_ml, 0) },
  get caloriesBurned() { return this.exercise.completed ? (this.exercise.calories_burned || 0) : 0 },
  get netCalories()    { return this.totalCalories - this.caloriesBurned },
  get mealsLogged()    { return new Set(this.meals.map(m => m.meal_type)).size },
  get caloriePct()     { return Math.min(Math.round((this.totalCalories / this.user.calorie_goal) * 100), 100) },
  get waterPct()       { return Math.min(Math.round((this.totalWaterMl  / this.user.water_goal_ml) * 100), 100) },

  get groupedMeals() {
    const groups = {}
    this.meals.forEach(m => {
      if (!groups[m.meal_type]) groups[m.meal_type] = { time: m.time, items: [], total: 0 }
      groups[m.meal_type].items.push(m)
      groups[m.meal_type].total += m.calories
    })
    return groups
  },

  // ── Actions ────────────────────────────────
  addMeal(entry) {
    this.meals.push({ ...entry, id: Date.now() })
    this._syncWeeklyToday()
  },

  updateMeal(id, patch) {
    const idx = this.meals.findIndex(m => m.id === id)
    if (idx !== -1) { this.meals[idx] = { ...this.meals[idx], ...patch } }
    this._syncWeeklyToday()
  },

  deleteMeal(id) {
    this.meals = this.meals.filter(m => m.id !== id)
    this._syncWeeklyToday()
  },

  addDrink(entry) {
    this.drinks.push({ ...entry, id: Date.now() })
  },

  deleteDrink(id) {
    this.drinks = this.drinks.filter(d => d.id !== id)
  },

  toggleExercise() {
    this.exercise.completed = !this.exercise.completed
  },

  setExercise(data) {
    this.exercise = { ...this.exercise, ...data }
  },

  _syncWeeklyToday() {
    const todayEntry = this.weeklyTrend.find(d => d.isToday)
    if (todayEntry) todayEntry.calories = this.totalCalories
  },
})

// Standalone computed refs — reliable Vue 3 reactivity for chart components
export const totalCalories  = computed(() => store.meals.reduce((s, m) => s + m.calories, 0))
export const totalWaterMl   = computed(() => store.drinks.reduce((s, d) => s + d.amount_ml, 0))
export const caloriesBurned = computed(() => store.exercise.completed ? (store.exercise.calories_burned || 0) : 0)
export const netCalories    = computed(() => totalCalories.value - caloriesBurned.value)
export const mealsLogged    = computed(() => new Set(store.meals.map(m => m.meal_type)).size)
export const caloriePct     = computed(() => Math.min(Math.round((totalCalories.value / store.user.calorie_goal) * 100), 100))
export const waterPct       = computed(() => Math.min(Math.round((totalWaterMl.value  / store.user.water_goal_ml) * 100), 100))
export const groupedMeals   = computed(() => {
  const groups = {}
  store.meals.forEach(m => {
    if (!groups[m.meal_type]) groups[m.meal_type] = { time: m.time, items: [], total: 0 }
    groups[m.meal_type].items.push(m)
    groups[m.meal_type].total += m.calories
  })
  return groups
})
