<template>
  <div class="app-root" v-if="authed">
    <AppSidebar v-if="!isMobile" />
    <div class="main-area">
      <router-view />
    </div>
    <BottomNav v-if="isMobile" />
  </div>

  <!-- Login screen -->
  <div v-else class="login-page">
    <div class="login-card">
      <div class="login-logo">
        <span class="login-icon">🌿</span>
        <div>
          <div class="login-app"><span class="green">Meal</span>Track</div>
          <div class="login-tagline">Better Food · Healthier You</div>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Email</label>
        <input class="form-input" type="email" v-model="email" placeholder="you@example.com"
          @keydown.enter="login" :disabled="loggingIn" />
      </div>
      <div class="form-group">
        <label class="form-label">Password</label>
        <input class="form-input" type="password" v-model="password" placeholder="••••••••"
          @keydown.enter="login" :disabled="loggingIn" />
      </div>

      <div v-if="loginError" class="login-error">{{ loginError }}</div>

      <button class="btn btn-primary login-btn" @click="login" :disabled="loggingIn || !email || !password">
        {{ loggingIn ? 'Signing in…' : 'Sign In' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import AppSidebar from './components/AppSidebar.vue'
import BottomNav  from './components/BottomNav.vue'
import { api }    from './api.js'
import { store }  from './store/index.js'

const isMobile   = ref(window.innerWidth < 768)
const authed     = ref(false)
const email      = ref('')
const password   = ref('')
const loginError = ref('')
const loggingIn  = ref(false)

const onResize = () => { isMobile.value = window.innerWidth < 768 }
onMounted(()  => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

let pollTimer = null

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => store.loadToday().catch(() => {}), 15_000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function onVisibilityChange() {
  if (authed.value && document.visibilityState === 'visible') {
    store.loadToday().catch(() => {})
  }
}

onMounted(async () => {
  document.addEventListener('visibilitychange', onVisibilityChange)

  const token = localStorage.getItem('mt_token')
  if (token) {
    try {
      await store.loadToday()
      authed.value = true
      startPolling()
    } catch {
      localStorage.removeItem('mt_token')
    }
  }
})

onUnmounted(() => {
  stopPolling()
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

async function login() {
  if (!email.value || !password.value) return
  loggingIn.value  = true
  loginError.value = ''
  try {
    const { access_token } = await api.login(email.value, password.value)
    localStorage.setItem('mt_token', access_token)
    await store.loadToday()
    authed.value = true
    startPolling()
  } catch (e) {
    loginError.value = e.status === 401 ? 'Invalid email or password.' : 'Could not connect. Try again.'
  } finally {
    loggingIn.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  padding: 24px;
}

.login-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  padding: 36px 32px;
  width: 100%;
  max-width: 380px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.login-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.login-icon    { font-size: 36px; }
.login-app     { font-size: 24px; font-weight: 800; line-height: 1; }
.login-app .green { color: var(--green-600); }
.login-tagline { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.login-error {
  background: #fff0f0;
  border: 1px solid #fca5a5;
  color: #dc2626;
  border-radius: var(--radius-xs);
  padding: 10px 12px;
  font-size: 13px;
}

.login-btn { width: 100%; justify-content: center; }
</style>
