<template>
  <aside class="sidebar">
    <!-- Logo -->
    <div class="sidebar-logo">
      <div class="logo-icon">🌿</div>
      <div class="logo-text">
        <span class="logo-meal">Meal</span><span class="logo-track">Track</span>
      </div>
    </div>
    <p class="sidebar-tagline">Better Food · Healthier You</p>

    <div class="sidebar-divider" />

    <!-- Navigation -->
    <nav class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: $route.path === item.path || ($route.path === '/' && item.path === '/') }"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
        <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
      </router-link>
    </nav>

    <!-- Footer -->
    <div class="sidebar-footer">
      <div class="sidebar-divider" />
      <div class="made-by">
        <span class="made-by-heart">💚</span>
        <div>
          <div class="made-by-title">Made by</div>
          <div class="made-by-name">Wajahat Ahmed</div>
        </div>
      </div>
      <div class="app-version">MealTrack v1.0 · 2026</div>
    </div>
  </aside>
</template>

<script setup>
const navItems = [
  { path: '/',          icon: '🏠', label: 'Dashboard'  },
  { path: '/food',      icon: '🍽️', label: 'Food Log'   },
  { path: '/hydration', icon: '💧', label: 'Hydration'  },
  { path: '/exercise',  icon: '🏃', label: 'Exercise'   },
  { path: '/insights',  icon: '💡', label: 'Insights'   },
  { path: '/progress',  icon: '📈', label: 'Progress'   },
  { path: '/goals',     icon: '🎯', label: 'Goals'      },
  { path: '/settings',  icon: '⚙️', label: 'Settings'   },
]
</script>

<style scoped>
.sidebar {
  position: fixed;
  top: 0; left: 0; bottom: 0;
  width: var(--sidebar-w);
  background: #fff;
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  z-index: 50;
  overflow: hidden;
}

/* Logo */
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 22px 20px 6px;
}
.logo-icon {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, var(--green-50), var(--green-100));
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
}
.logo-text { font-size: 20px; line-height: 1; letter-spacing: -0.5px; }
.logo-meal  { font-weight: 800; color: var(--green-600); }
.logo-track { font-weight: 800; color: var(--text); }

.sidebar-tagline {
  padding: 0 20px;
  font-size: 11px;
  color: var(--text-light);
  font-weight: 500;
  letter-spacing: 0.01em;
}

.sidebar-divider {
  height: 1px;
  background: var(--border-light);
  margin: 14px 0;
}

/* Nav */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s var(--ease);
  position: relative;
}
.nav-item:hover {
  background: var(--green-50);
  color: var(--green-600);
}
.nav-item.active {
  background: var(--green-50);
  color: var(--green-600);
  font-weight: 600;
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0; top: 50%;
  transform: translateY(-50%);
  width: 3px; height: 20px;
  background: var(--green-600);
  border-radius: 0 3px 3px 0;
}

.nav-icon { font-size: 17px; width: 22px; text-align: center; }
.nav-label { flex: 1; }
.nav-badge {
  background: var(--orange-500);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 10px;
}

/* Footer */
.sidebar-footer { padding: 0 12px 16px; }

.made-by {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 10px;
  background: var(--green-50);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
}
.made-by-heart { font-size: 18px; }
.made-by-title { font-size: 10px; color: var(--text-light); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
.made-by-name  { font-size: 13px; color: var(--green-700); font-weight: 700; }

.app-version {
  text-align: center;
  font-size: 10px;
  color: var(--text-light);
  padding: 0 10px;
}
</style>
