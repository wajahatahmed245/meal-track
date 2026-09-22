<template>
  <div class="timeline">
    <div v-if="Object.keys(groups).length === 0" class="empty-state">
      <div class="empty-icon">🍽️</div>
      <p>No meals logged yet today.<br>Tap the food chips below to get started!</p>
    </div>

    <div
      v-for="(group, mealType) in groups"
      :key="mealType"
      class="timeline-group"
    >
      <!-- Meal header -->
      <div class="group-header">
        <div class="group-dot" />
        <div class="group-time">{{ group.time }}</div>
        <span class="badge" :class="mealBadgeClass(mealType)">
          {{ mealTypeEmoji[mealType] || '🍽️' }} {{ mealType }}
        </span>
        <span class="group-total">{{ group.total }} cal</span>
      </div>

      <!-- Food items -->
      <div class="group-items">
        <div v-for="item in group.items" :key="item.id" class="food-item">
          <span class="food-emoji">{{ item.emoji }}</span>
          <span class="food-name">{{ item.name }}</span>
          <span class="food-cal">{{ item.calories }} cal</span>
          <div class="food-actions">
            <button class="btn-icon" @click="$emit('edit', item)" title="Edit">✏️</button>
            <button class="btn-icon delete" @click="$emit('delete', item.id)" title="Delete">🗑️</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { mealTypeEmoji } from '../data/mock.js'

defineProps({
  groups: { type: Object, required: true },
})
defineEmits(['edit', 'delete'])

const mealBadgeClass = (type) => {
  const map = {
    'Breakfast': 'badge-orange',
    'Morning Snack': 'badge-purple',
    'Lunch': 'badge-green',
    'Afternoon Snack': 'badge-blue',
    'Dinner': 'badge-orange',
    'Late Snack': 'badge-gray',
  }
  return map[type] || 'badge-gray'
}
</script>

<style scoped>
.timeline { display: flex; flex-direction: column; gap: 0; }

.timeline-group { position: relative; padding-left: 28px; margin-bottom: 4px; }
.timeline-group::before {
  content: '';
  position: absolute;
  left: 7px; top: 28px; bottom: 0;
  width: 2px;
  background: var(--border-light);
}
.timeline-group:last-child::before { display: none; }

.group-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.group-dot {
  position: absolute;
  left: 2px; top: 8px;
  width: 12px; height: 12px;
  border-radius: 50%;
  background: var(--green-500);
  border: 2px solid #fff;
  box-shadow: 0 0 0 2px var(--green-100);
}
.group-time {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  min-width: 40px;
}
.group-total {
  margin-left: auto;
  font-size: 12px;
  font-weight: 700;
  color: var(--orange-500);
  background: var(--orange-50);
  padding: 2px 8px;
  border-radius: 10px;
}

.group-items {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
  background: var(--bg);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.food-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  background: #fff;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xs);
  transition: all 0.12s var(--ease);
}
.food-item:hover { border-color: var(--green-100); background: var(--green-50); }

.food-emoji { font-size: 18px; width: 24px; text-align: center; }
.food-name  { flex: 1; font-size: 13px; font-weight: 500; color: var(--text); }
.food-cal   { font-size: 12px; font-weight: 600; color: var(--orange-500); white-space: nowrap; }

.food-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.12s var(--ease);
}
.food-item:hover .food-actions { opacity: 1; }

.btn-icon {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px;
  font-size: 13px;
  border: 1px solid var(--border);
  cursor: pointer;
  background: #fff;
  transition: all 0.12s var(--ease);
}
.btn-icon:hover { background: var(--green-50); border-color: var(--green-200); }
.btn-icon.delete:hover { background: #fff0f0; border-color: #fca5a5; }
</style>
