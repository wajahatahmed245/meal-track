<template>
  <div class="overlay-backdrop" @click.self="$emit('close')">
    <div class="modal-sheet">
      <div class="modal-header">
        <h2 class="modal-title">{{ isEdit ? '✏️ Edit Food' : '🍽️ Add Food' }}</h2>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>

      <form @submit.prevent="submit">
        <div class="form-group">
          <label class="form-label">Food Name *</label>
          <input
            class="form-input"
            v-model="form.name"
            placeholder="e.g. Chicken Curry, Banana…"
            required
            autofocus
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Calories *</label>
            <input
              class="form-input"
              v-model.number="form.calories"
              type="number"
              min="1"
              placeholder="kcal"
              required
            />
          </div>
          <div class="form-group">
            <label class="form-label">Emoji</label>
            <input
              class="form-input"
              v-model="form.emoji"
              placeholder="🍽️"
              maxlength="2"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Meal Type</label>
            <select class="form-select" v-model="form.meal_type">
              <option v-for="mt in mealTypes" :key="mt" :value="mt">{{ mt }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Time</label>
            <input class="form-input" type="time" v-model="form.time" />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Serving size (optional)</label>
          <input
            class="form-input"
            v-model="form.serving_size"
            placeholder="e.g. 1 cup, 200g, 1 medium"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Note (optional)</label>
          <textarea
            class="form-input"
            v-model="form.note"
            rows="2"
            placeholder="Any extra detail…"
            style="resize: none;"
          />
        </div>

        <!-- Quick cal lookup -->
        <div class="cal-hint" v-if="calHint">
          <span>💡 Typical: <strong>{{ calHint.typical_calories }} cal</strong> for {{ calHint.per }}</span>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-outline" @click="$emit('close')">Cancel</button>
          <button type="submit" class="btn btn-primary" :disabled="!form.name || !form.calories">
            {{ isEdit ? 'Update' : 'Add Food' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { mealTypes, foodDatabase } from '../data/mock.js'

const props = defineProps({
  entry: { type: Object, default: null }, // null = add mode
})
const emit = defineEmits(['save', 'close'])

const isEdit = computed(() => !!props.entry)

const form = ref({
  name:         props.entry?.name         || '',
  calories:     props.entry?.calories     || '',
  emoji:        props.entry?.emoji        || '🍽️',
  meal_type:    props.entry?.meal_type    || 'Breakfast',
  time:         props.entry?.time         || nowTime(),
  serving_size: props.entry?.serving_size || '',
  note:         props.entry?.note         || '',
})

function nowTime() {
  const d = new Date(Date.now() + 5 * 60 * 60 * 1000)
  return `${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}`
}

const calHint = computed(() => {
  if (!form.value.name) return null
  return foodDatabase.find(f =>
    f.name.toLowerCase().includes(form.value.name.toLowerCase()) ||
    form.value.name.toLowerCase().includes(f.name.toLowerCase().split(' ')[0])
  ) || null
})

watch(calHint, (hint) => {
  if (hint && !form.value.calories) {
    form.value.calories = hint.calories
    form.value.emoji    = form.value.emoji || hint.emoji
  }
})

function submit() {
  emit('save', { ...form.value, calories: Number(form.value.calories) })
}
</script>

<style scoped>
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

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.cal-hint {
  padding: 10px 12px;
  background: var(--blue-50);
  border-radius: var(--radius-xs);
  font-size: 13px;
  color: var(--blue-600);
  margin-bottom: 14px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding-top: 4px;
}
</style>
