import './plugins/echarts.js'
import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import './assets/main.css'

import Dashboard  from './views/Dashboard.vue'
import FoodLog    from './views/FoodLog.vue'
import Hydration  from './views/Hydration.vue'
import Exercise   from './views/Exercise.vue'
import Insights   from './views/Insights.vue'
import Progress   from './views/Progress.vue'
import Goals      from './views/Goals.vue'
import Settings   from './views/Settings.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/',           component: Dashboard,  name: 'dashboard'  },
    { path: '/food',       component: FoodLog,    name: 'food'       },
    { path: '/hydration',  component: Hydration,  name: 'hydration'  },
    { path: '/exercise',   component: Exercise,   name: 'exercise'   },
    { path: '/insights',   component: Insights,   name: 'insights'   },
    { path: '/progress',   component: Progress,   name: 'progress'   },
    { path: '/goals',      component: Goals,      name: 'goals'      },
    { path: '/settings',   component: Settings,   name: 'settings'   },
  ],
})

createApp(App).use(router).mount('#app')
