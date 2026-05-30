import { get, post } from '@/api/http'

export interface CheckInBoard {
  userId: number
  totalDays: number
  checkedInToday: boolean
  dates: string[]
}

/** 着陆页签到板：站点主人的公开记录 */
export async function fetchSiteOwnerCheckInBoard(): Promise<CheckInBoard> {
  return get<CheckInBoard>('/check-ins/site-owner', { auth: false })
}

/** 当前登录用户今日签到（幂等） */
export async function checkInTodayApi(): Promise<CheckInBoard> {
  return post<CheckInBoard>('/check-ins/today')
}

/** 当前登录用户签到板（只读） */
export async function fetchMyCheckInBoard(): Promise<CheckInBoard> {
  return get<CheckInBoard>('/check-ins/me')
}
