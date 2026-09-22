<template>
  <div class="page-content">
    <h1 class="page-title">🎯 Goals</h1>
    <p class="page-sub">Set your daily targets and let MealTrack keep you on track</p>

    <!-- Goals form -->
    <div class="card goals-form">
      <div class="section-title">Daily Targets</div>

      <div class="goal-item">
        <div class="gi-header">
          <span>🔥</span>
          <span>Calorie Goal</span>
          <strong class="gi-val">{{ form.calorie_goal }} kcal</strong>
        </div>
        <input type="range" class="goal-slider" v-model.number="form.calorie_goal"
          min="1200" max="4000" step="50" />
        <div class="slider-labels"><span>1,200</span><span>2,500</span><span>4,000</span></div>
      </div>

      <div class="goal-item">
        <div class="gi-header">
          <span>💧</span>
          <span>Daily Water Goal</span>
          <strong class="gi-val">{{ (form.water_goal_ml / 1000).toFixed(1) }}L</strong>
        </div>
        <input type="range" class="goal-slider" v-model.number="form.water_goal_ml"
          min="1000" max="5000" step="250" />
        <div class="slider-labels"><span>1L</span><span>2.5L</span><span>5L</span></div>
      </div>

      <div class="goal-item">
        <div class="gi-header">
          <span>🏃</span>
          <span>Exercise Days / Week</span>
          <strong class="gi-val">{{ form.exercise_days }} days</strong>
        </div>
        <div class="day-selector">
          <button
            v-for="n in 7" :key="n"
            class="day-btn"
            :class="{ active: form.exercise_days >= n }"
            @click="form.exercise_days = n"
          >{{ n }}</button>
        </div>
      </div>

      <div class="save-row">
        <button class="btn btn-primary" @click="saveGoals">💾 Save Goals</button>
        <span v-if="saved" class="saved-msg">✅ Saved!</span>
      </div>
    </div>

    <!-- Current progress -->
    <div class="card">
      <div class="section-title">📊 Today vs Goals</div>
      <div class="progress-list">
        <div class="pl-item" v-for="g in goalProgress" :key="g.label">
          <div class="pli-header">
            <span>{{ g.icon }} {{ g.label }}</span>
            <span class="pli-pct">{{ g.pct }}%</span>
          </div>
          <div class="pli-track">
            <div class="pli-fill" :style="{ width: Math.min(g.pct, 100) + '%', background: g.color }" />
          </div>
          <div class="pli-sub">{{ g.current }} / {{ g.target }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { store, totalCalories, totalWaterMl } from '../store/index.js'

const form = ref({
  calorie_goal:   store.user.calorie_goal,
  water_goal_ml:  store.user.water_goal_ml,
  exercise_days:  store.user.exercise_goal_days || 5,
})
const saved = ref(false)

function saveGoals() {
  store.user.calorie_goal  = form.value.calorie_goal
  store.user.water_goal_ml = form.value.water_goal_ml
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}

const goalProgress = computed(() => [
  {
    icon: '🔥', label: 'Calories',
    current: totalCalories.value.toLocaleString() + ' cal',
    target:  form.value.calorie_goal.toLocaleString() + ' cal',
    pct:     Math.round((totalCalories.value / form.value.calorie_goal) * 100),
    color:   '#f97316',
  },
  {
    icon: '💧', label: 'Water',
    current: (totalWaterMl.value / 1000).toFixed(1) + 'L',
    target:  (form.value.water_goal_ml / 1000).toFixed(1) + 'L',
    pct:     Math.round((totalWaterMl.value / form.value.water_goal_ml) * 100),
    color:   '#0ea5e9',
  },
  {
    icon: '🏃', label: 'Exercise',
    current: store.exercise.completed ? 'Done' : 'Not yet',
    target:  'Complete today',
    pct:     store.exercise.completed ? 100 : 0,
    color:   '#22c55e',
  },
])
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.page-sub   { font-size: 13px; color: var(--text-muted); margin-bottom: 20px; }

.goals-form { padding: 20px; margin-bottom: 20px; }

.goal-item { margin-bottom: 22px; }
.gi-header {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; font-weight: 600; margin-bottom: 10px; color: var(--text);
}
.gi-val { margin-left: auto; color: var(--green-600); font-size: 15px; }

.goal-slider {
  width: 100%; height: 6px; appearance: none;
  background: linear-gradient(to right, var(--green-500) var(--pct, 50%), #e2e8f0 0);
  border-radius: 3px; cursor: pointer; outline: none;
}
.goal-slider::-webkit-slider-thumb {
  appearance: none; width: 18px; height: 18px;
  border-radius: 50%; background: var(--green-600);
  border: 2px solid #fff; box-shadow: var(--shadow-xs);
  cursor: pointer;
}
.slider-labels { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-light); margin-top: 4px; }

.day-selector { display: flex; gap: 8px; }
.day-btn {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  border: 2px solid var(--border); background: #fff;
  font-size: 13px; font-weight: 700; color: var(--text-muted); cursor: pointer;
  transition: all 0.13s var(--ease);
}
.day-btn.active { border-color: var(--green-500); background: var(--green-50); color: var(--green-700); }

.save-row { display: flex; align-items: center; gap: 12px; }
.saved-msg { font-size: 13px; color: var(--green-600); font-weight: 600; }

/* Progress list */
.progress-list { padding: 4px 0; display: flex; flex-direction: column; gap: 18px; }
.pli-header { display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.pli-pct    { color: var(--text-muted); }
.pli-track  { height: 8px; background: #f1f5f9; border-radius: 4px; overflow: hidden; margin-bottom: 4px; }
.pli-fill   { height: 100%; border-radius: 4px; transition: width 0.5s var(--ease); }
.pli-sub    { font-size: 12px; color: var(--text-muted); }
</style>
