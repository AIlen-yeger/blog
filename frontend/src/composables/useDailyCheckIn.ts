import { ref } from 'vue'
import {
  checkInTodayApi,
  fetchMyCheckInBoard,
  fetchSiteOwnerCheckInBoard,
  type CheckInBoard,
} from '@/api/checkIn'
import { useMockApi } from '@/api/http'
import { hasValidSession } from '@/composables/useSession'

/** 与 useLandingCheckIn 共享的展示状态 */
export const checkInDates = ref<Set<string>>(new Set())
export const checkInTotalDays = ref(0)
export const checkInCheckedToday = ref(false)
export const checkInBoardUserId = ref(0)
export const checkInLoading = ref(false)

export function toCheckInDateKey(d = new Date()) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function applyBoard(board: CheckInBoard) {
  checkInBoardUserId.value = board.userId ?? 0
  checkInTotalDays.value = board.totalDays ?? 0
  checkInCheckedToday.value = !!board.checkedInToday
  checkInDates.value = new Set(
    (board.dates ?? []).filter((d) => /^\d{4}-\d{2}-\d{2}$/.test(d)),
  )
}

/** 游客：站点主人公开签到板 */
export async function loadSiteOwnerCheckInBoard() {
  if (useMockApi()) return
  checkInLoading.value = true
  try {
    const board = await fetchSiteOwnerCheckInBoard()
    applyBoard(board)
  } catch {
    /* 保留上次展示 */
  } finally {
    checkInLoading.value = false
  }
}

/** 着陆页：已登录展示自己的签到；游客看站点主人 */
export async function loadLandingCheckInBoard() {
  if (useMockApi()) return
  checkInLoading.value = true
  try {
    if (hasValidSession()) {
      try {
        const mine = await fetchMyCheckInBoard()
        applyBoard(mine)
        return
      } catch {
        /* 回退到签到并拉取 */
      }
      const mine = await checkInTodayApi()
      applyBoard(mine)
      return
    }
    const board = await fetchSiteOwnerCheckInBoard()
    applyBoard(board)
  } catch {
    /* 保留上次展示 */
  } finally {
    checkInLoading.value = false
  }
}

let checkInFlight: Promise<void> | null = null

/**
 * 当前登录用户今日签到（后端 INSERT IGNORE，同日幂等），并刷新签到板。
 */
export function triggerDailyCheckIn(): Promise<void> {
  if (!hasValidSession() || useMockApi()) return Promise.resolve()
  if (checkInFlight) return checkInFlight

  checkInFlight = (async () => {
    checkInLoading.value = true
    try {
      const mine = await checkInTodayApi()
      applyBoard(mine)
    } catch {
      await loadLandingCheckInBoard()
    } finally {
      checkInLoading.value = false
      checkInFlight = null
    }
  })()

  return checkInFlight
}
