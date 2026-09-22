<template>
  <div class="calorie-progress card">
    <div class="cp-header">
      <div class="section-title" style="margin-bottom:0">Calorie Progress</div>
      <div class="cp-pct-badge" :style="{ background: pctBg, color: arcColor }">
        {{ pct }}%
      </div>
    </div>

    <VChart
      :option="gaugeOption"
      :autoresize="true"
      class="gauge-chart"
    />

    <div class="legend">
      <div class="legend-item">
        <div class="legend-dot" style="background:#f97316"></div>
        <span>Eaten</span>
        <strong :style="{ color: '#f97316' }">{{ consumed.toLocaleString() }}</strong>
      </div>
      <div class="legend-item">
        <div class="legend-dot" style="background:#22c55e"></div>
        <span>Burned</span>
        <strong :style="{ color: '#22c55e' }">{{ burned }}</strong>
      </div>
      <div class="legend-item">
        <div class="legend-dot" style="background:#e2e8f0"></div>
        <span>Remaining</span>
        <strong>{{ remaining.toLocaleString() }}</strong>
      </div>
    </div>

    <div class="mini-bar-wrap">
      <div class="mini-bar-track">
        <div
          class="mini-bar-fill"
          :style="{ width: Math.min(pct, 100) + '%', background: arcColor }"
        />
        <div
          v-if="burned > 0"
          class="mini-bar-burned"
          :style="{ width: Math.min(burnedPct, 100 - Math.min(pct, 100)) + '%' }"
        />
      </div>
      <div class="mini-bar-labels">
        <span style="color:var(--text-light)">0</span>
        <span class="goal-label">{{ goal.toLocaleString() }} cal goal</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'

const props = defineProps({
  consumed: { type: Number, default: 0 },
  burned:   { type: Number, default: 0 },
  goal:     { type: Number, default: 2000 },
})

const pct       = computed(() => Math.min(Math.round((props.consumed / props.goal) * 100), 100))
const burnedPct = computed(() => Math.round((props.burned / props.goal) * 100))
const remaining = computed(() => Math.max(props.goal - props.consumed + props.burned, 0))

const arcColor = computed(() =>
  pct.value >= 100 ? '#ef4444'
  : pct.value >= 90 ? '#f97316'
  : pct.value >= 70 ? '#fb923c'
  : '#22c55e'
)
const pctBg = computed(() =>
  pct.value >= 100 ? '#fef2f2'
  : pct.value >= 70 ? '#fff7ed'
  : '#f0fdf4'
)

const gaugeOption = computed(() => {
  const color = arcColor.value
  const pctVal = Math.min((props.consumed / props.goal) * 100, 100)

  return {
    animation: true,
    animationDuration: 900,
    animationEasing: 'cubicOut',

    tooltip: {
      show: true,
      trigger: 'item',
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      borderRadius: 12,
      padding: [12, 16],
      extraCssText: 'box-shadow:0 8px 32px rgba(0,0,0,0.10);font-family:Inter,-apple-system,sans-serif;',
      formatter: () => `
        <div style="min-width:190px">
          <div style="font-weight:700;font-size:14px;color:#0f172a;margin-bottom:10px">
            🔥 Calorie Summary
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;text-align:center">
            <div>
              <div style="font-size:10px;color:#94a3b8;font-weight:600;letter-spacing:.5px;margin-bottom:3px">EATEN</div>
              <div style="font-size:16px;font-weight:800;color:#f97316">${props.consumed.toLocaleString()}</div>
              <div style="font-size:10px;color:#94a3b8">cal</div>
            </div>
            <div>
              <div style="font-size:10px;color:#94a3b8;font-weight:600;letter-spacing:.5px;margin-bottom:3px">BURNED</div>
              <div style="font-size:16px;font-weight:800;color:#22c55e">${props.burned}</div>
              <div style="font-size:10px;color:#94a3b8">cal</div>
            </div>
            <div>
              <div style="font-size:10px;color:#94a3b8;font-weight:600;letter-spacing:.5px;margin-bottom:3px">NET</div>
              <div style="font-size:16px;font-weight:800;color:#0f172a">${(props.consumed - props.burned).toLocaleString()}</div>
              <div style="font-size:10px;color:#94a3b8">cal</div>
            </div>
          </div>
          <div style="margin-top:10px;padding-top:10px;border-top:1px solid #f1f5f9;font-size:12px;color:#64748b;text-align:center">
            ${pct.value}% of ${props.goal.toLocaleString()} kcal daily goal
          </div>
        </div>`,
    },

    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '28%',
        style: {
          text: props.consumed.toLocaleString(),
          fontSize: 34,
          fontWeight: '800',
          fill: color,
          fontFamily: 'Inter, -apple-system, sans-serif',
        },
      },
      {
        type: 'text',
        left: 'center',
        top: '47%',
        style: {
          text: 'cal eaten',
          fontSize: 12,
          fill: '#64748b',
          fontFamily: 'Inter, -apple-system, sans-serif',
          fontWeight: '500',
        },
      },
      {
        type: 'text',
        left: 'center',
        top: '57%',
        style: {
          text: `${pct.value}% of goal`,
          fontSize: 13,
          fill: '#0f172a',
          fontFamily: 'Inter, -apple-system, sans-serif',
          fontWeight: '700',
        },
      },
    ],

    series: [
      {
        type: 'gauge',
        startAngle: 90,
        endAngle: -270,
        radius: '88%',
        center: ['50%', '50%'],
        pointer: { show: false },
        progress: {
          show: true,
          roundCap: true,
          width: 22,
          itemStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: color },
                { offset: 1, color: color + 'bb' },
              ],
            },
          },
        },
        axisLine: {
          roundCap: true,
          lineStyle: {
            width: 22,
            color: [[1, '#f1f5f9']],
          },
        },
        axisTick:  { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail:    { show: false },
        data: [{ value: +pctVal.toFixed(2) }],
      },
    ],
  }
})
</script>

<style scoped>
.calorie-progress { padding: 20px; }

.cp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.cp-pct-badge {
  font-size: 13px;
  font-weight: 800;
  padding: 3px 10px;
  border-radius: 20px;
  letter-spacing: 0.3px;
}

.gauge-chart { height: 200px; width: 100%; }

.legend {
  display: flex;
  justify-content: space-between;
  margin-bottom: 14px;
}
.legend-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-muted);
}
.legend-item strong { font-size: 14px; font-weight: 700; color: var(--text); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; }

.mini-bar-track {
  position: relative;
  height: 8px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 4px;
}
.mini-bar-fill {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  border-radius: 4px;
  transition: width 0.6s cubic-bezier(0.4,0,0.2,1);
}
.mini-bar-burned {
  position: absolute;
  top: 0; bottom: 0;
  background: rgba(34, 197, 94, 0.35);
  border-radius: 0 4px 4px 0;
  transition: width 0.6s cubic-bezier(0.4,0,0.2,1);
  left: var(--burned-left, 0);
}
.mini-bar-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-light);
}
.goal-label { font-weight: 600; color: var(--text-muted); }
</style>
