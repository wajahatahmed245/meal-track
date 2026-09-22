<template>
  <div class="meal-dist card">
    <div class="md-header">
      <div>
        <div class="chart-title">🍽️ Meal Distribution</div>
        <div class="chart-sub">Calories by meal type today</div>
      </div>
      <div class="total-badge">{{ totalCal.toLocaleString() }} <span>cal total</span></div>
    </div>

    <VChart
      :option="donutOption"
      :autoresize="true"
      class="donut-chart"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'

const props = defineProps({
  groups: { type: Object, default: () => ({}) },
})

const COLORS = {
  'Breakfast':         '#f97316',
  'Morning Snack':     '#8b5cf6',
  'Lunch':             '#22c55e',
  'Afternoon Snack':   '#0ea5e9',
  'Dinner':            '#3b82f6',
  'Evening Snack':     '#ec4899',
}
const fallbackColors = ['#f59e0b', '#10b981', '#6366f1', '#ef4444', '#14b8a6', '#f43f5e']

const distributionData = computed(() => {
  return Object.entries(props.groups)
    .filter(([, g]) => g.total > 0)
    .map(([type, g], i) => ({
      name: type,
      value: g.total,
      itemStyle: {
        color: COLORS[type] || fallbackColors[i % fallbackColors.length],
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2,
      },
    }))
})

const totalCal = computed(() =>
  distributionData.value.reduce((s, d) => s + d.value, 0)
)

const donutOption = computed(() => ({
  animation: true,
  animationDuration: 700,
  animationEasing: 'cubicOut',

  tooltip: {
    trigger: 'item',
    backgroundColor: '#ffffff',
    borderColor: '#e2e8f0',
    borderWidth: 1,
    borderRadius: 12,
    padding: [12, 16],
    extraCssText: 'box-shadow:0 8px 32px rgba(0,0,0,0.10);font-family:Inter,-apple-system,sans-serif;',
    formatter(params) {
      const pct = params.percent.toFixed(1)
      return `
        <div style="min-width:150px">
          <div style="font-weight:700;font-size:14px;color:#0f172a;margin-bottom:8px;display:flex;align-items:center;gap:8px">
            <span style="width:10px;height:10px;border-radius:50%;background:${params.color};display:inline-block"></span>
            ${params.name}
          </div>
          <div style="font-size:22px;font-weight:800;color:${params.color};margin-bottom:3px">
            ${params.value.toLocaleString()}
          </div>
          <div style="font-size:12px;color:#94a3b8">cal · ${pct}% of total</div>
        </div>`
    },
  },

  legend: {
    orient: 'horizontal',
    bottom: 0,
    left: 'center',
    textStyle: {
      fontFamily: 'Inter, -apple-system, sans-serif',
      fontSize: 11,
      color: '#64748b',
    },
    icon: 'circle',
    itemWidth: 8,
    itemHeight: 8,
    itemGap: 12,
    selectedMode: true,
  },

  graphic: [
    {
      type: 'text',
      left: 'center',
      top: '32%',
      style: {
        text: totalCal.value.toLocaleString(),
        fontSize: 22,
        fontWeight: '800',
        fill: '#f97316',
        fontFamily: 'Inter, -apple-system, sans-serif',
      },
    },
    {
      type: 'text',
      left: 'center',
      top: '46%',
      style: {
        text: 'total cal',
        fontSize: 11,
        fill: '#94a3b8',
        fontFamily: 'Inter, -apple-system, sans-serif',
        fontWeight: '500',
      },
    },
  ],

  series: [
    {
      type: 'pie',
      radius: ['48%', '68%'],
      center: ['50%', '44%'],
      avoidLabelOverlap: true,
      padAngle: 2,
      label: { show: false },
      emphasis: {
        scale: true,
        scaleSize: 6,
        itemStyle: {
          shadowBlur: 14,
          shadowOffsetY: 3,
          shadowColor: 'rgba(0,0,0,0.12)',
        },
      },
      selectedMode: 'single',
      data: distributionData.value,
    },
  ],
}))
</script>

<style scoped>
.meal-dist { padding: 18px 20px 14px; }

.md-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.chart-title { font-size: 14px; font-weight: 700; color: var(--text); }
.chart-sub   { font-size: 11px; color: var(--text-muted); margin-top: 1px; }

.total-badge {
  font-size: 15px;
  font-weight: 800;
  color: #f97316;
  white-space: nowrap;
}
.total-badge span {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
}

.donut-chart { height: 220px; width: 100%; }
</style>
