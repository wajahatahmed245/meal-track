<template>
  <div class="quick-add card">
    <div class="section-title">
      <span>⚡ Quick Add</span>
    </div>

    <!-- Food chips -->
    <div class="chips-label">What did you eat?</div>
    <div class="chips">
      <button
        v-for="chip in quickChips"
        :key="chip.name"
        class="chip"
        @click="selectChip(chip)"
        :class="{ selected: selected?.name === chip.name }"
      >
        <span class="chip-emoji">{{ chip.emoji }}</span>
        <span class="chip-name">{{ chip.name }}</span>
      </button>
    </div>

    <!-- Custom input -->
    <div class="custom-row">
      <input
        class="form-input"
        v-model="customName"
        placeholder="Or type a food name…"
        @keydown.enter="quickLog"
      />
      <input
        class="form-input cal-input"
        v-model.number="customCal"
        type="number"
        min="1"
        placeholder="cal"
      />
    </div>

    <div class="select-row">
      <select class="form-select" v-model="mealType">
        <option v-for="mt in mealTypes" :key="mt" :value="mt">{{ mt }}</option>
      </select>
      <input class="form-input time-input" type="time" v-model="mealTime" />
    </div>

    <div class="action-row">
      <button class="btn btn-primary" @click="quickLog" :disabled="!canLog">
        🍽️ Add Food
      </button>
      <button class="btn btn-secondary" @click="$emit('addDrink')">
        💧 Add Drink
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { quickFoodChips, mealTypes } from '../data/mock.js'

const emit = defineEmits(['logged', 'addDrink'])

const quickChips  = quickFoodChips
const selected    = ref(null)
const customName  = ref('')
const customCal   = ref('')
const mealType    = ref('Breakfast')
const mealTime    = ref(nowTime())

function nowTime() {
  const d = new Date(Date.now() + 5 * 60 * 60 * 1000)
  return `${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}`
}

function selectChip(chip) {
  selected.value  = chip
  customName.value = chip.name
  customCal.value  = chip.calories
  mealType.value   = chip.meal_type
}

const canLog = computed(() => (customName.value.trim() || selected.value) && customCal.value > 0)

function quickLog() {
  if (!canLog.value) return
  emit('logged', {
    name:      customName.value.trim() || selected.value.name,
    calories:  Number(customCal.value),
    emoji:     selected.value?.emoji || '🍽️',
    meal_type: mealType.value,
    time:      mealTime.value,
  })
  customName.value = ''
  customCal.value  = ''
  selected.value   = null
}
</script>

<style scoped>
.quick-add { padding: 20px; }

.chips-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-bottom: 14px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: 20px;
  border: 1.5px solid var(--border);
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  transition: all 0.13s var(--ease);
}
.chip:hover, .chip.selected {
  border-color: var(--green-500);
  background: var(--green-50);
  color: var(--green-700);
}
.chip-emoji { font-size: 15px; }

.custom-row {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}
.cal-input { max-width: 80px; }

.select-row {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.time-input { max-width: 110px; }

.action-row {
  display: flex;
  gap: 10px;
}
.action-row .btn { flex: 1; justify-content: center; }
</style>
