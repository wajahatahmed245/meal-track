<template>
  <div class="page-content">
    <h1 class="page-title">⚙️ Settings</h1>
    <p class="page-sub">Personalize your MealTrack experience</p>

    <!-- Profile -->
    <div class="card settings-card">
      <div class="section-title">👤 Profile</div>
      <div class="avatar-row">
        <div class="avatar">{{ initials }}</div>
        <div>
          <div class="av-name">{{ form.name }}</div>
          <div class="av-sub">MealTrack Member</div>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Display Name</label>
        <input class="form-input" v-model="form.name" />
      </div>
    </div>

    <!-- Daily Goals -->
    <div class="card settings-card">
      <div class="section-title">🎯 Daily Goals</div>
      <div class="form-group">
        <label class="form-label">Calorie Goal (kcal)</label>
        <input class="form-input" type="number" v-model.number="form.calorie_goal" min="1000" max="5000" />
      </div>
      <div class="form-group">
        <label class="form-label">Water Goal (ml)</label>
        <input class="form-input" type="number" v-model.number="form.water_goal_ml" min="500" max="8000" />
      </div>
    </div>

    <!-- MCP Integration -->
    <div class="card settings-card mcp-card">
      <div class="section-title">🤖 MCP / AI Integration</div>
      <p class="mcp-desc">
        Connect ChatGPT or Claude to MealTrack via the Model Context Protocol.
        Once configured, ask your AI assistant things like:<br>
        <em>"Log a banana to breakfast"</em> or <em>"How many calories today?"</em>
      </p>
      <div class="mcp-status">
        <span class="mcp-dot inactive" />
        <span class="mcp-label">MCP Server: Not configured (backend required)</span>
      </div>
      <div class="mcp-tools">
        <div class="mt-title">Available Tools (once connected):</div>
        <div class="mt-list">
          <span v-for="t in mcpTools" :key="t" class="mt-tag">{{ t }}</span>
        </div>
      </div>
    </div>

    <!-- About -->
    <div class="card settings-card about-card">
      <div class="section-title">ℹ️ About</div>
      <div class="about-logo">
        <span class="about-icon">🌿</span>
        <div>
          <div class="about-app-name"><span class="green">Meal</span>Track</div>
          <div class="about-tagline">Better Food · Healthier You · Brighter Tomorrow</div>
        </div>
      </div>
      <div class="about-version">Version 1.0.0 · September 2026</div>
      <div class="made-by-badge">
        <span>💚</span>
        <div>
          <div class="mb-made">Made with care by</div>
          <div class="mb-name">Wajahat Ahmed</div>
        </div>
      </div>
    </div>

    <div class="save-bar">
      <button class="btn btn-primary" @click="save">💾 Save Settings</button>
      <span v-if="saved" class="saved-msg">✅ Settings saved!</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { store } from '../store/index.js'

const form = ref({
  name:          store.user.name,
  calorie_goal:  store.user.calorie_goal,
  water_goal_ml: store.user.water_goal_ml,
})
const saved = ref(false)
const initials = computed(() => form.value.name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase())

function save() {
  store.user.name          = form.value.name
  store.user.calorie_goal  = form.value.calorie_goal
  store.user.water_goal_ml = form.value.water_goal_ml
  saved.value = true
  setTimeout(() => { saved.value = false }, 2500)
}

const mcpTools = [
  'get_today_summary', 'add_food_entry', 'delete_food_entry',
  'add_drink_entry', 'mark_exercise', 'get_weekly_summary',
  'get_food_log', 'get_insights', 'search_food',
]
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.page-sub   { font-size: 13px; color: var(--text-muted); margin-bottom: 20px; }

.settings-card { padding: 20px; margin-bottom: 16px; }

.avatar-row { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; }
.avatar {
  width: 52px; height: 52px; border-radius: 50%;
  background: linear-gradient(135deg, var(--green-500), var(--green-700));
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 800; color: #fff;
  flex-shrink: 0;
}
.av-name { font-size: 16px; font-weight: 700; }
.av-sub  { font-size: 12px; color: var(--text-muted); }

/* MCP card */
.mcp-card { background: linear-gradient(135deg, #f8fafc, #f0fdf4); }
.mcp-desc { font-size: 13px; color: var(--text-muted); line-height: 1.6; margin-bottom: 12px; }
.mcp-status { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
.mcp-dot    { width: 10px; height: 10px; border-radius: 50%; }
.mcp-dot.inactive { background: var(--text-light); }
.mcp-dot.active   { background: var(--green-500); box-shadow: 0 0 0 3px rgba(34,197,94,0.2); }
.mcp-label  { font-size: 13px; color: var(--text-muted); }

.mt-title { font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 8px; }
.mt-list  { display: flex; flex-wrap: wrap; gap: 6px; }
.mt-tag {
  padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600;
  background: var(--green-100); color: var(--green-700); font-family: monospace;
}

/* About */
.about-card {}
.about-logo {
  display: flex; align-items: center; gap: 12px; margin-bottom: 12px;
}
.about-icon     { font-size: 32px; }
.about-app-name { font-size: 22px; font-weight: 800; }
.about-app-name .green { color: var(--green-600); }
.about-tagline  { font-size: 12px; color: var(--text-muted); }
.about-version  { font-size: 12px; color: var(--text-light); margin-bottom: 16px; }

.made-by-badge {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 12px 16px; background: var(--green-50);
  border-radius: var(--radius-sm); border: 1px solid var(--green-100);
  font-size: 13px;
}
.mb-made { font-size: 11px; color: var(--text-light); }
.mb-name { font-size: 15px; font-weight: 800; color: var(--green-700); }

.save-bar { display: flex; align-items: center; gap: 14px; margin-top: 8px; }
.saved-msg { font-size: 13px; color: var(--green-600); font-weight: 600; }
</style>
