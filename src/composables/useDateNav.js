import { ref, computed } from 'vue'

/**
 * Shared Pakistan-time date navigation composable.
 * Used by FoodLog.vue and AiEvaluation.vue.
 *
 * All date calculations use PKT (UTC+5) so they stay consistent
 * with the backend's TZ=Asia/Karachi server time.
 */

export function pktDateStr(offsetDays = 0) {
  const pkt = new Date(Date.now() + 5 * 60 * 60 * 1000)
  pkt.setUTCDate(pkt.getUTCDate() + offsetDays)
  return pkt.toISOString().split('T')[0]
}

/**
 * @param {number} initialOffset  Starting offset in days from today (0 = today, -1 = yesterday).
 * @param {number} maxOffset      Maximum allowed offset (0 = cannot go past today).
 */
export function useDateNav(initialOffset = 0, maxOffset = 0) {
  const offset = ref(initialOffset)

  const isToday     = computed(() => offset.value === maxOffset)
  const targetDate  = computed(() => pktDateStr(offset.value))

  const dateLabel = computed(() => {
    if (offset.value === 0)  return 'Today'
    if (offset.value === -1) return 'Yesterday'
    const d = new Date(pktDateStr(offset.value) + 'T00:00:00Z')
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
  })

  const prevDay = () => { offset.value-- }
  const nextDay = () => { if (offset.value < maxOffset) offset.value++ }

  return { offset, isToday, targetDate, dateLabel, prevDay, nextDay }
}
