<template>
  <div class="weekly-chart card">
    <div class="chart-header">
      <div>
        <div class="chart-title">📊 Weekly Intake</div>
        <div class="chart-sub">Calories consumed vs {{ goal.toLocaleString() }} kcal goal</div>
      </div>
      <div class="chart-legend-row">
        <span class="leg-dot" style="background:#22c55e"></span><span class="leg-txt">Under</span>
        <span class="leg-dot" style="background:#f97316"></span><span class="leg-txt">Over</span>
        <span class="leg-dot" style="background:#3b82f6"></span><span class="leg-txt">Today</span>
      </div>
    </div>
    <VChart
      :option="chartOption"
      :autoresize="true"
      class="echart"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'

const props = defineProps({
  data: { type: Array, required: true },
  goal: { type: Number, default: 2000 },
})

const yMax = computed(() => {
  const mx = Math.max(...props.data.map(d => d.calories), props.goal)
  return Math.ceil((mx * 1.18) / 500) * 500
})

const chartOption = computed(() => ({
  animation: true,
  animationDuration: 700,
  animationEasing: 'cubicOut',

  grid: {
    top: 16,
    right: 84,
    bottom: 8,
    left: 0,
    containLabel: true,
  },

  tooltip: {
    trigger: 'axis',
    backgroundColor: '#ffffff',
    borderColor: '#e2e8f0',
    borderWidth: 1,
    borderRadius: 12,
    padding: [12, 16],
    extraCssText: 'box-shadow:0 8px 32px rgba(0,0,0,0.10);font-family:Inter,-apple-system,sans-serif;',
    axisPointer: {
      type: 'shadow',
      shadowStyle: { color: 'rgba(241,245,249,0.8)' },
    },
    formatter(params) {
      const d    = props.data[params[0].dataIndex]
      const diff = d.calories - props.goal
      const pct  = Math.round((d.calories / props.goal) * 100)
      const col  = d.isToday ? '#3b82f6' : diff > 0 ? '#f97316' : '#22c55e'
      const badge = d.isToday
        ? `<span style="font-size:10px;color:#3b82f6;background:#eff6ff;padding:2px 7px;border-radius:4px;font-weight:700;margin-left:6px">TODAY</span>`
        : ''
      return `
        <div style="min-width:170px">
          <div style="font-weight:700;font-size:14px;color:#0f172a;margin-bottom:8px;display:flex;align-items:center">
            ${d.day}${badge}
          </div>
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
            <span style="width:10px;height:10px;border-radius:50%;background:${col};display:inline-block;flex-shrink:0"></span>
            <span style="font-size:18px;font-weight:800;color:${col}">${d.calories.toLocaleString()}</span>
            <span style="font-size:12px;color:#94a3b8;font-weight:500">cal</span>
          </div>
          <div style="font-size:12px;font-weight:600;color:${diff > 0 ? '#f97316' : '#22c55e'};margin-bottom:3px">
            ${diff > 0 ? '▲' : '▼'} ${Math.abs(diff).toLocaleString()} ${diff > 0 ? 'over' : 'under'} goal
          </div>
          <div style="font-size:11px;color:#94a3b8">${pct}% of ${props.goal.toLocaleString()} kcal daily goal</div>
        </div>`
    },
  },

  xAxis: {
    type: 'category',
    data: props.data.map(d => d.day),
    axisLine: { lineStyle: { color: '#e2e8f0', width: 1 } },
    axisTick: { show: false },
    axisLabel: {
      fontFamily: 'Inter, -apple-system, sans-serif',
      color: '#64748b',
      fontSize: 12,
      fontWeight: '600',
      rich: {
        today: {
          color: '#3b82f6',
          fontWeight: '700',
          fontSize: 12,
        },
      },
      formatter(val, idx) {
        return props.data[idx]?.isToday ? `{today|${val}}` : val
      },
    },
    boundaryGap: true,
  },

  yAxis: {
    type: 'value',
    min: 0,
    max: yMax.value,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: {
      lineStyle: { color: '#f1f5f9', type: 'dashed', dashOffset: 2 },
    },
    axisLabel: {
      fontFamily: 'Inter, -apple-system, sans-serif',
      color: '#94a3b8',
      fontSize: 11,
      formatter: v => v === 0 ? '' : v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v),
    },
  },

  series: [
    {
      type: 'bar',
      barWidth: '52%',
      barMaxWidth: 52,
      data: props.data.map(d => ({
        value: d.calories,
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: d.isToday
            ? { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{ offset: 0, color: '#93c5fd' }, { offset: 1, color: '#3b82f6' }] }
            : d.calories > props.goal
            ? { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{ offset: 0, color: '#fdba74' }, { offset: 1, color: '#f97316' }] }
            : { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{ offset: 0, color: '#86efac' }, { offset: 1, color: '#22c55e' }] },
        },
      })),
      emphasis: {
        itemStyle: {
          shadowBlur: 14,
          shadowOffsetY: 4,
          shadowColor: 'rgba(0,0,0,0.10)',
        },
      },
      markLine: {
        silent: false,
        symbol: ['none', 'none'],
        lineStyle: { type: 'dashed', color: '#94a3b8', width: 1.5 },
        label: {
          show: true,
          position: 'insideEndTop',
          formatter: `Goal: ${props.goal.toLocaleString()}`,
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
        data: [{ yAxis: props.goal }],
      },
    },
  ],
}))
</script>

<style scoped>
.weekly-chart { padding: 18px 20px 14px; }

.chart-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.chart-title { font-size: 14px; font-weight: 700; color: var(--text); }
.chart-sub   { font-size: 11px; color: var(--text-muted); margin-top: 1px; }

.chart-legend-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.leg-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.leg-txt {
  font-size: 11px;
  color: var(--text-muted);
  margin-right: 6px;
}

.echart { height: 180px; width: 100%; }
</style>
