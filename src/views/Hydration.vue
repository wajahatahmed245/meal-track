<template>
  <div class="page-content">
    <div class="page-header">
      <div>
        <h1 class="page-title">💧 Hydration</h1>
        <p class="page-sub">Track your daily water intake</p>
      </div>
      <button class="btn btn-blue" @click="showModal = true">+ Add Drink</button>
    </div>

    <!-- Big water meter -->
    <div class="water-hero card">
      <div class="water-visual">
        <div class="water-drop-wrap">
          <div class="water-drop-bg">
            <div class="water-fill" :style="{ height: waterPct + '%' }">
              <div class="water-wave" />
            </div>
          </div>
          <div class="water-pct-label">{{ waterPct }}%</div>
        </div>
      </div>
      <div class="water-info">
        <div class="water-title">Today's Hydration</div>
        <div class="water-val">{{ (store.totalWaterMl / 1000).toFixed(2) }} <span class="water-unit">L</span></div>
        <div class="water-goal">Goal: {{ (store.user.water_goal_ml / 1000).toFixed(1) }}L</div>
        <div class="water-remaining">
          {{ Math.max(store.user.water_goal_ml - store.totalWaterMl, 0) }}ml more to go
        </div>

        <!-- Quick add buttons -->
        <div class="quick-water-btns">
          <button
            v-for="amt in [150, 250, 350, 500]"
            :key="amt"
            class="water-btn"
            @click="quickAdd(amt)"
          >+{{ amt }}ml</button>
        </div>
      </div>
    </div>

    <!-- Drink log -->
    <div class="card">
      <div class="section-title" style="padding: 18px 20px 0;">
        <span>Today's Drinks ({{ store.drinks.length }})</span>
        <span class="text-muted" style="font-size:12px; font-weight:400;">{{ store.totalWaterMl }}ml total</span>
      </div>
      <div class="drink-list">
        <div v-for="drink in store.drinks" :key="drink.id" class="drink-row">
          <span class="dr-emoji">{{ drink.emoji }}</span>
          <div class="dr-info">
            <div class="dr-name">{{ drink.name }}</div>
            <div class="dr-time">{{ drink.time }}</div>
          </div>
          <div class="dr-amount">{{ drink.amount_ml }}ml</div>
          <button class="icon-btn del" @click="store.deleteDrink(drink.id)">🗑️</button>
        </div>
        <div v-if="store.drinks.length === 0" class="empty-state">
          <div class="empty-icon">💧</div>
          <p>No drinks logged yet. Start tracking!</p>
        </div>
      </div>
    </div>

    <!-- Add drink modal -->
    <div v-if="showModal" class="overlay-backdrop" @click.self="showModal = false">
      <div class="modal-sheet">
        <div class="modal-header">
          <h2 class="modal-title">💧 Log a Drink</h2>
          <button class="close-btn" @click="showModal = false">✕</button>
        </div>
        <div class="form-group">
          <label class="form-label">Drink</label>
          <input class="form-input" v-model="form.name" placeholder="Water, Tea, Juice…" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Amount (ml)</label>
            <input class="form-input" v-model.number="form.amount_ml" type="number" min="1" />
          </div>
          <div class="form-group">
            <label class="form-label">Emoji</label>
            <input class="form-input" v-model="form.emoji" maxlength="2" />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-outline" @click="showModal = false">Cancel</button>
          <button class="btn btn-blue" @click="addDrink">Log Drink</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { store } from '../store/index.js'

const showModal = ref(false)
const form = ref({ name: 'Water', amount_ml: 250, emoji: '💧' })

const waterPct = computed(() =>
  Math.min(Math.round((store.totalWaterMl / store.user.water_goal_ml) * 100), 100)
)

function quickAdd(ml) {
  store.addDrink({ name: 'Water', amount_ml: ml, emoji: '💧', time: nowTime() })
}

function addDrink() {
  store.addDrink({ ...form.value, time: nowTime() })
  showModal.value = false
  form.value = { name: 'Water', amount_ml: 250, emoji: '💧' }
}

function nowTime() {
  const d = new Date(Date.now() + 5 * 60 * 60 * 1000)
  return `${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}`
}
</script>

<style scoped>
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 20px; }
.page-title  { font-size: 22px; font-weight: 700; }
.page-sub    { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

.water-hero { display: flex; gap: 24px; padding: 24px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }

/* Water meter */
.water-drop-wrap { position: relative; width: 100px; height: 140px; }
.water-drop-bg {
  width: 100px; height: 140px;
  background: #e0f2fe;
  border-radius: 50% 50% 45% 45% / 40% 40% 60% 60%;
  overflow: hidden;
  position: relative;
}
.water-fill {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: linear-gradient(180deg, #38bdf8, #0ea5e9);
  transition: height 0.6s var(--ease);
  border-radius: 50% 50% 0 0 / 20% 20% 0 0;
}
.water-wave {
  position: absolute;
  top: -8px; left: -20%; width: 140%;
  height: 16px;
  background: rgba(255,255,255,0.4);
  border-radius: 50%;
  animation: wave 2s ease-in-out infinite;
}
@keyframes wave { 0%,100% { transform: translateX(0); } 50% { transform: translateX(-10%); } }

.water-pct-label {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 800; color: #fff;
  text-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.water-info { flex: 1; }
.water-title     { font-size: 13px; font-weight: 600; color: var(--text-muted); margin-bottom: 4px; }
.water-val       { font-size: 40px; font-weight: 800; color: var(--blue-500); line-height: 1; }
.water-unit      { font-size: 20px; }
.water-goal      { font-size: 14px; color: var(--text-muted); margin-top: 6px; }
.water-remaining { font-size: 13px; color: var(--text-muted); margin-top: 2px; }

.quick-water-btns { display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; }
.water-btn {
  padding: 8px 16px; border-radius: 20px;
  border: 1.5px solid var(--blue-100); background: var(--blue-50);
  color: var(--blue-600); font-size: 13px; font-weight: 600; cursor: pointer;
  transition: all 0.13s var(--ease);
}
.water-btn:hover { background: var(--blue-100); border-color: var(--blue-500); }

/* Drink list */
.drink-list { padding: 12px 16px 16px; display: flex; flex-direction: column; gap: 6px; }
.drink-row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px; border-radius: var(--radius-xs);
  border: 1px solid var(--border-light); background: #fff;
  transition: background 0.12s;
}
.drink-row:hover { background: var(--bg); }
.dr-emoji  { font-size: 20px; }
.dr-info   { flex: 1; }
.dr-name   { font-size: 13px; font-weight: 600; }
.dr-time   { font-size: 11px; color: var(--text-light); }
.dr-amount { font-size: 14px; font-weight: 700; color: var(--blue-500); }
.icon-btn {
  width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
  border-radius: 6px; font-size: 13px; border: 1px solid var(--border);
  cursor: pointer; background: #fff; transition: all 0.12s;
}
.icon-btn.del:hover { background: #fff0f0; border-color: #fca5a5; }

.modal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.modal-title  { font-size: 18px; font-weight: 700; }
.close-btn    { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 8px; font-size: 14px; color: var(--text-muted); border: 1px solid var(--border); cursor: pointer; background: #fff; }
.form-row     { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; padding-top: 4px; }
</style>
