import { computed, onMounted } from 'vue'
import { useMockApi } from '@/api/http'
import {
  checkInCheckedToday,
  checkInDates,
  checkInLoading,
  checkInTotalDays,
  loadLandingCheckInBoard,
  toCheckInDateKey,
} from '@/composables/useDailyCheckIn'

const STORAGE_KEY = 'blog:landing-check-in'
/** 签到板横向周数（列数），与后端 BOARD_WEEKS 一致 */
export const LANDING_CHECKIN_WEEKS = 12

function loadLocalDates(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return new Set()
    const arr = JSON.parse(raw) as string[]
    return new Set(arr.filter((d) => /^\d{4}-\d{2}-\d{2}$/.test(d)))
  } catch {
    return new Set()
  }
}

function saveLocalDates(set: Set<string>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...set].sort()))
}

function recordLocalVisitToday() {
  const key = toCheckInDateKey()
  if (checkInDates.value.has(key)) {
    checkInCheckedToday.value = true
    return
  }
  const next = new Set(checkInDates.value)
  next.add(key)
  checkInDates.value = next
  checkInTotalDays.value = next.size
  checkInCheckedToday.value = true
  saveLocalDates(next)
}

function dayStamp(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
}

/**
 * GitHub 式热力图：每列一周，行 0–6 固定为 日–六；最右列为「含今天」的那一周。
 */
function buildGrid(weeks: number) {
  const today = new Date()
  today.setHours(12, 0, 0, 0)
  const todayStamp = dayStamp(today)

  const weekSunday = new Date(today)
  weekSunday.setDate(today.getDate() - today.getDay())

  const gridStart = new Date(weekSunday)
  gridStart.setDate(weekSunday.getDate() - (weeks - 1) * 7)

  const cells: { key: string; level: 0 | 1; future: boolean }[] = []
  for (let col = 0; col < weeks; col++) {
    for (let row = 0; row < 7; row++) {
      const d = new Date(gridStart)
      d.setDate(gridStart.getDate() + col * 7 + row)
      const key = toCheckInDateKey(d)
      const stamp = dayStamp(d)
      const future = stamp > todayStamp
      cells.push({
        key,
        level: !future && checkInDates.value.has(key) ? 1 : 0,
        future,
      })
    }
  }
  return cells
}

async function initBoard() {
  if (useMockApi()) {
    checkInDates.value = loadLocalDates()
    checkInTotalDays.value = checkInDates.value.size
    checkInCheckedToday.value = checkInDates.value.has(toCheckInDateKey())
    recordLocalVisitToday()
    return
  }

  await loadLandingCheckInBoard()
}

/** 着陆页签到热力格（站点主人公开数据；登录用户访问时幂等签到） */
export function useLandingCheckIn() {
  onMounted(() => {
    void initBoard()
  })

  const todayKey = computed(() => toCheckInDateKey())
  const grid = computed(() => buildGrid(LANDING_CHECKIN_WEEKS))

  return {
    grid,
    totalDays: checkInTotalDays,
    checkedInToday: checkInCheckedToday,
    todayKey,
    weekCount: LANDING_CHECKIN_WEEKS,
    loading: checkInLoading,
  }
}
