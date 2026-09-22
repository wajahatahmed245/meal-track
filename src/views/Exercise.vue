<template>
  <div class="page-content">
    <h1 class="page-title">🏃 Exercise</h1>
    <p class="page-sub">Did you move your body today?</p>

    <!-- Today's status card -->
    <div class="status-card card" :class="store.exercise.completed ? 'done' : 'pending'">
      <div class="status-icon">{{ store.exercise.completed ? '🏆' : '💤' }}</div>
      <div class="status-info">
        <div class="status-heading">{{ store.exercise.completed ? "Today's Workout" : 'No Exercise Yet' }}</div>
        <div v-if="store.exercise.completed" class="status-details">
          <span class="s-tag">{{ store.exercise.type }}</span>
          <span class="s-tag">{{ store.exercise.duration_minutes }} min</span>
          <span class="s-tag burn">🔥 {{ store.exercise.calories_burned }} cal burned</span>
        </div>
        <div v-else class="status-prompt">Log your workout to earn your daily streak! 💪</div>
      </div>
      <button
        class="toggle-btn"
        :class="store.exercise.completed ? 'btn btn-outline' : 'btn btn-primary'"
        @click="store.toggleExercise()"
      >
        {{ store.exercise.completed ? 'Mark Undone' : 'Mark Complete ✓' }}
      </button>
    </div>

    <!-- Log form -->
    <div class="card log-form">
      <div class="section-title">📝 Log Details</div>
      <div class="form-group">
        <label class="form-label">Exercise Type</label>
        <div class="exercise-types">
          <button
            v-for="type in exerciseTypes"
            :key="type.name"
            class="type-btn"
            :class="{ selected: exForm.type === type.name }"
            @click="exForm.type = type.name"
          >
            {{ type.emoji }} {{ type.name }}
          </button>
        </div>
      </div>

      <div class="form-row-3">
        <div class="form-group">
          <label class="form-label">Duration (min)</label>
          <input class="form-input" type="number" v-model.number="exForm.duration_minutes" min="1" max="300" />
        </div>
        <div class="form-group">
          <label class="form-label">Cal Burned (est.)</label>
          <input class="form-input" type="number" v-model.number="exForm.calories_burned" min="0" />
        </div>
        <div class="form-group">
          <label class="form-label">Time</label>
          <input class="form-input" type="time" v-model="exForm.time" />
        </div>
      </div>

      <button class="btn btn-primary" @click="saveExercise">
        💾 Save Exercise Log
      </button>
    </div>

    <!-- Weekly streak -->
    <div class="card">
      <div class="section-title">🔥 This Week's Streak</div>
      <div class="streak-week">
        <div
          v-for="(day, i) in weekDays"
          :key="i"
          class="streak-day"
          :class="{ done: day.done, today: day.isToday }"
        >
          <div class="streak-circle">{{ day.done ? '✓' : '' }}</div>
          <div class="streak-label">{{ day.label }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { store } from '../store/index.js'

const exerciseTypes = [
  { name: 'Morning Walk', emoji: '🚶' },
  { name: 'Running',      emoji: '🏃' },
  { name: 'Cycling',      emoji: '🚴' },
  { name: 'Gym',          emoji: '💪' },
  { name: 'Swimming',     emoji: '🏊' },
  { name: 'Yoga',         emoji: '🧘' },
  { name: 'Home Workout', emoji: '🏠' },
  { name: 'Sports',       emoji: '⚽' },
]

const exForm = ref({ ...store.exercise })

function saveExercise() {
  store.setExercise({ ...exForm.value, completed: true })
}

const weekDays = [
  { label: 'Mon', done: true,  isToday: false },
  { label: 'Tue', done: true,  isToday: false },
  { label: 'Wed', done: false, isToday: false },
  { label: 'Thu', done: true,  isToday: false },
  { label: 'Fri', done: false, isToday: false },
  { label: 'Sat', done: true,  isToday: false },
  { label: 'Sun', done: store.exercise.completed, isToday: true },
]
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.page-sub   { font-size: 13px; color: var(--text-muted); margin-bottom: 20px; }

.status-card {
  display: flex; align-items: center; gap: 16px;
  padding: 22px; margin-bottom: 20px; flex-wrap: wrap;
}
.status-card.done    { border: 2px solid var(--green-100); background: var(--green-50); }
.status-card.pending { border: 2px solid var(--border); }

.status-icon    { font-size: 40px; }
.status-info    { flex: 1; }
.status-heading { font-size: 16px; font-weight: 700; color: var(--text); margin-bottom: 6px; }
.status-details { display: flex; gap: 8px; flex-wrap: wrap; }
.s-tag {
  padding: 3px 10px; border-radius: 12px;
  font-size: 12px; font-weight: 600;
  background: #fff; border: 1px solid var(--border); color: var(--text-muted);
}
.s-tag.burn { color: var(--orange-500); border-color: var(--orange-100); background: var(--orange-50); }
.status-prompt { font-size: 13px; color: var(--text-muted); }
.toggle-btn { white-space: nowrap; }

.log-form { padding: 20px; margin-bottom: 20px; }
.exercise-types { display: flex; flex-wrap: wrap; gap: 8px; }
.type-btn {
  padding: 7px 14px; border-radius: 20px;
  border: 1.5px solid var(--border); background: #fff;
  font-size: 13px; font-weight: 500; color: var(--text-muted); cursor: pointer;
  transition: all 0.13s var(--ease);
}
.type-btn:hover, .type-btn.selected {
  border-color: var(--green-500); background: var(--green-50); color: var(--green-700);
}
.form-row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
@media (max-width: 480px) { .form-row-3 { grid-template-columns: 1fr 1fr; } }

/* Streak */
.streak-week {
  display: flex; justify-content: space-around; gap: 6px;
  padding: 0 4px;
}
.streak-day { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.streak-circle {
  width: 38px; height: 38px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700;
  background: var(--border-light); color: var(--text-light);
  transition: all 0.15s var(--ease);
}
.streak-day.done .streak-circle {
  background: var(--green-500); color: #fff;
  box-shadow: 0 2px 8px rgba(34,197,94,0.4);
}
.streak-day.today .streak-circle {
  border: 2px solid var(--green-500);
}
.streak-label { font-size: 11px; font-weight: 600; color: var(--text-muted); }
.streak-day.today .streak-label { color: var(--green-600); }
</style>
