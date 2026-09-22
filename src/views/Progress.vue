<template>
  <div class="page-content">
    <h1 class="page-title">📈 Progress</h1>
    <p class="page-sub">Your long-term nutrition and wellness trends</p>

    <!-- Summary stats -->
    <div class="stat-row">
      <div class="stat-card card" v-for="s in stats" :key="s.label">
        <div class="stat-icon">{{ s.icon }}</div>
        <div class="stat-val">{{ s.val }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </div>
    </div>

    <!-- 30-day ECharts line chart -->
    <div class="card chart-card">
      <div class="chart-hd">
        <div>
          <div class="chart-title">📅 30-Day Calorie Trend</div>
          <div class="chart-sub">Daily intake vs 2,000 kcal goal · Aug 22 – Sep 21</div>
        </div>
        <div class="chart-avg-badge">
          Avg <strong>{{ avgCal.toLocaleString() }}</strong> cal/day
        </div>
      </div>
      <VChart :option="trendOption" :autoresize="true" class="trend-chart" />
    </div>

    <!-- Weekly breakdown bar chart -->
    <div class="card chart-card">
      <div class="chart-hd">
        <div>
          <div class="chart-title">📊 Last 4 Weeks</div>
          <div class="chart-sub">Average daily calories per week</div>
        </div>
      </div>
      <VChart :option="weeklyOption" :autoresize="true" class="weekly-chart" />
    </div>

    <!-- Streak calendar -->
    <div class="card">
      <div class="section-title">🗓️ Logging Streak — September 2026</div>
      <div class="calendar-grid">
        <div v-for="(day, i) in calendarDays" :key="i"
          class="cal-day" :class="day.cls"
        >{{ day.n }}</div>
      </div>
      <div class="streak-legend">
        <span class="sl-item"><span class="sl-dot green" /> Logged</span>
        <span class="sl-item"><span class="sl-dot gray"  /> Not Logged</span>
        <span class="sl-item"><span class="sl-dot blue"  /> Today</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'

// ── Mock 30-day data (Aug 22 – Sep 21 2026) ─────────────────────────
const calData = [
  1740, 1890, 1620, 2050, 1980, 1710, 2180,  // week 1: Aug 22-28
  1830, 1660, 1940, 2100, 1770, 2020, 1590,  // week 2: Aug 29 – Sep 4
  1850, 2230, 1720, 1980, 1640, 2080, 1760,  // week 3: Sep 5-11
  1820, 1650, 2150, 1780, 1920, 2200, 1439,  // week 4: Sep 12-21 (last = today)
  1920, 2200, 1439,
].slice(0, 30)

// Labels: last 30 days
const dayLabels = computed(() => {
  const labels = []
  for (let i = 29; i >= 0; i--) {
    const d = new Date('2026-09-21')
    d.setDate(d.getDate() - i)
    labels.push(d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }))
  }
  return labels
})

const goal = 2000
const avgCal = computed(() => Math.round(calData.reduce((s, v) => s + v, 0) / calData.length))

// ── 30-day line/area chart option ─────────────────────────────────────
const trendOption = computed(() => ({
  animation: true,
  animationDuration: 800,
  animationEasing: 'cubicOut',

  grid: { top: 20, right: 20, bottom: 32, left: 10, containLabel: true },

  tooltip: {
    trigger: 'axis',
    backgroundColor: '#ffffff',
    borderColor: '#e2e8f0',
    borderWidth: 1,
    borderRadius: 12,
    padding: [12, 16],
    extraCssText: 'box-shadow:0 8px 32px rgba(0,0,0,0.10);font-family:Inter,-apple-system,sans-serif;',
    axisPointer: { type: 'cross', crossStyle: { color: '#94a3b8' }, lineStyle: { type: 'dashed' } },
    formatter(params) {
      const p    = params[0]
      const cal  = p.value
      const diff = cal - goal
      const col  = diff > 0 ? '#f97316' : '#22c55e'
      return `
        <div style="min-width:160px">
          <div style="font-weight:700;font-size:13px;color:#64748b;margin-bottom:6px">${p.name}</div>
          <div style="font-size:20px;font-weight:800;color:${col};margin-bottom:4px">${cal.toLocaleString()}</div>
          <div style="font-size:11px;color:${col};font-weight:600">
            ${diff > 0 ? '▲' : '▼'} ${Math.abs(diff).toLocaleString()} ${diff > 0 ? 'over' : 'under'} goal
          </div>
        </div>`
    },
  },

  xAxis: {
    type: 'category',
    data: dayLabels.value,
    axisLine: { lineStyle: { color: '#e2e8f0' } },
    axisTick: { show: false },
    axisLabel: {
      fontFamily: 'Inter, -apple-system, sans-serif',
      color: '#94a3b8',
      fontSize: 11,
      interval: 4,
      rotate: 0,
    },
    boundaryGap: false,
  },

  yAxis: {
    type: 'value',
    min: 1200,
    max: 2600,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
    axisLabel: {
      fontFamily: 'Inter, -apple-system, sans-serif',
      color: '#94a3b8',
      fontSize: 11,
      formatter: v => `${(v / 1000).toFixed(1)}k`,
    },
  },

  series: [
    {
      type: 'line',
      smooth: 0.4,
      data: calData,
      symbol: 'circle',
      symbolSize: 5,
      showSymbol: false,
      lineStyle: { color: '#f97316', width: 2.5 },
      itemStyle: { color: '#f97316' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(249,115,22,0.28)' },
            { offset: 1, color: 'rgba(249,115,22,0.02)' },
          ],
        },
      },
      emphasis: {
        showSymbol: true,
        itemStyle: {
          borderWidth: 3,
          borderColor: '#fff',
          shadowBlur: 8,
          shadowColor: 'rgba(249,115,22,0.4)',
        },
      },
      markLine: {
        silent: true,
        symbol: ['none', 'none'],
        lineStyle: { type: 'dashed', color: '#22c55e', width: 1.5 },
        label: {
          show: true,
          position: 'insideEndTop',
          formatter: 'Goal: 2,000',
          fontFamily: 'Inter, sans-serif',
          fontSize: 11,
          fontWeight: '600',
          color: '#22c55e',
          backgroundColor: '#f0fdf4',
          borderColor: '#bbf7d0',
          borderWidth: 1,
          borderRadius: 4,
          padding: [3, 6],
        },
        data: [{ yAxis: goal }],
      },
      markPoint: {
        symbol: 'pin',
        symbolSize: 36,
        data: [
          {
            type: 'max',
            name: 'Peak',
            itemStyle: { color: '#f97316' },
            label: { color: '#fff', fontFamily: 'Inter', fontSize: 11, fontWeight: '700' },
          },
          {
            type: 'min',
            name: 'Low',
            itemStyle: { color: '#22c55e' },
            label: { color: '#fff', fontFamily: 'Inter', fontSize: 11, fontWeight: '700' },
          },
        ],
      },
    },
  ],
}))

// ── Weekly averages bar chart ─────────────────────────────────────────
const weeklyAverages = computed(() => [
  { week: 'Aug 22–28', avg: Math.round(calData.slice(0, 7).reduce((s, v) => s + v, 0) / 7) },
  { week: 'Aug 29–Sep 4', avg: Math.round(calData.slice(7, 14).reduce((s, v) => s + v, 0) / 7) },
  { week: 'Sep 5–11', avg: Math.round(calData.slice(14, 21).reduce((s, v) => s + v, 0) / 7) },
  { week: 'Sep 12–21', avg: Math.round(calData.slice(21, 30).reduce((s, v) => s + v, 0) / 9) },
])

const weeklyOption = computed(() => ({
  animation: true,
  animationDuration: 600,
  animationEasing: 'cubicOut',

  grid: { top: 20, right: 20, bottom: 10, left: 10, containLabel: true },

  tooltip: {
    trigger: 'axis',
    backgroundColor: '#ffffff',
    borderColor: '#e2e8f0',
    borderWidth: 1,
    borderRadius: 12,
    padding: [12, 16],
    extraCssText: 'box-shadow:0 8px 32px rgba(0,0,0,0.10);font-family:Inter,-apple-system,sans-serif;',
    axisPointer: { type: 'shadow' },
    formatter(params) {
      const w   = weeklyAverages.value[params[0].dataIndex]
      const col = w.avg > goal ? '#f97316' : '#22c55e'
      const diff = w.avg - goal
      return `
        <div style="min-width:160px">
          <div style="font-weight:700;font-size:13px;color:#64748b;margin-bottom:6px">${w.week}</div>
          <div style="font-size:20px;font-weight:800;color:${col};margin-bottom:3px">
            ${w.avg.toLocaleString()}
          </div>
          <div style="font-size:11px;color:${col};font-weight:600">
            ${diff > 0 ? '▲' : '▼'} ${Math.abs(diff).toLocaleString()} ${diff > 0 ? 'over' : 'under'} goal avg
          </div>
        </div>`
    },
  },

  xAxis: {
    type: 'category',
    data: weeklyAverages.value.map(w => w.week),
    axisLine: { lineStyle: { color: '#e2e8f0' } },
    axisTick: { show: false },
    axisLabel: { fontFamily: 'Inter, sans-serif', color: '#64748b', fontSize: 11, fontWeight: '600' },
  },

  yAxis: {
    type: 'value',
    min: 1400,
    max: 2400,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
    axisLabel: {
      fontFamily: 'Inter, sans-serif',
      color: '#94a3b8',
      fontSize: 11,
      formatter: v => v >= 1000 ? `${(v/1000).toFixed(1)}k` : String(v),
    },
  },

  series: [{
    type: 'bar',
    barWidth: '50%',
    data: weeklyAverages.value.map(w => ({
      value: w.avg,
      itemStyle: {
        borderRadius: [8, 8, 0, 0],
        color: w.avg > goal
          ? { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: '#fdba74' }, { offset: 1, color: '#f97316' }] }
          : { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: '#86efac' }, { offset: 1, color: '#22c55e' }] },
      },
    })),
    emphasis: {
      itemStyle: {
        shadowBlur: 12,
        shadowOffsetY: 4,
        shadowColor: 'rgba(0,0,0,0.10)',
      },
    },
    markLine: {
      silent: true,
      symbol: ['none', 'none'],
      lineStyle: { type: 'dashed', color: '#94a3b8', width: 1.5 },
      label: {
        show: true,
        position: 'insideEndTop',
        formatter: 'Goal: 2,000',
        fontFamily: 'Inter, sans-serif',
        fontSize: 11,
        fontWeight: '600',
        color: '#64748b',
        backgroundColor: '#fff',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        borderRadius: 4,
        padding: [3, 6],
      },
      data: [{ yAxis: goal }],
    },
  }],
}))

// ── Stats ─────────────────────────────────────────────────────────────
const stats = computed(() => [
  { icon: '🔥', val: avgCal.value.toLocaleString(), label: 'Avg cal/day (30d)' },
  { icon: '📅', val: '21',   label: 'Days Logged'   },
  { icon: '🏃', val: '16',   label: 'Exercise Days' },
  { icon: '⚡', val: '14d',  label: 'Current Streak' },
])

// ── Calendar ──────────────────────────────────────────────────────────
const logged = [1,2,3,5,6,7,8,9,11,12,14,15,16,17,18,20,21]
const calendarDays = [
  { n: '', cls: 'empty' },
  ...Array.from({ length: 30 }, (_, i) => {
    const n = i + 1
    const isToday  = n === 21
    const isLogged = logged.includes(n)
    return { n, cls: isToday ? 'today' : isLogged ? 'logged' : n <= 21 ? 'missed' : 'future' }
  }),
]
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.page-sub   { font-size: 13px; color: var(--text-muted); margin-bottom: 20px; }

.stat-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-bottom: 20px; }
@media (min-width: 640px) { .stat-row { grid-template-columns: repeat(4, 1fr); } }
.stat-card  { padding: 18px; text-align: center; }
.stat-icon  { font-size: 24px; margin-bottom: 6px; }
.stat-val   { font-size: 24px; font-weight: 800; color: var(--text); }
.stat-label { font-size: 11px; color: var(--text-muted); font-weight: 500; margin-top: 2px; }

.chart-card { padding: 18px 20px 14px; margin-bottom: 20px; }
.chart-hd {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.chart-title { font-size: 14px; font-weight: 700; color: var(--text); }
.chart-sub   { font-size: 11px; color: var(--text-muted); margin-top: 1px; }

.chart-avg-badge {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  padding: 4px 10px;
  background: #fff7ed;
  border-radius: 20px;
  border: 1px solid #fed7aa;
}
.chart-avg-badge strong { color: #f97316; font-weight: 700; }

.trend-chart  { height: 220px; width: 100%; }
.weekly-chart { height: 160px; width: 100%; }

/* Calendar */
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  padding: 0 0 12px;
}
.cal-day {
  aspect-ratio: 1;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}
.cal-day.logged { background: var(--green-100); color: var(--green-700); }
.cal-day.missed { background: #f1f5f9; color: var(--text-light); }
.cal-day.today  { background: var(--blue-500); color: #fff; }
.cal-day.future { color: var(--text-light); }
.cal-day.empty  {}

.streak-legend { display: flex; gap: 14px; padding-top: 8px; border-top: 1px solid var(--border-light); }
.sl-item { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-muted); }
.sl-dot  { width: 10px; height: 10px; border-radius: 50%; }
.sl-dot.green { background: var(--green-400, #4ade80); }
.sl-dot.gray  { background: #e2e8f0; }
.sl-dot.blue  { background: var(--blue-500); }
</style>
