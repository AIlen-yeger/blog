import { ApiError, get, post, put, del } from '@/api/http'
import type {
  ArchiveMonthItem,
  LifeItem,
  NoteItem,
  ProfileData,
  SearchResult,
  TagCountItem,
  TimelineItem,
  TopicItem,
} from '@/data/mockContent'

export interface PageResult<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}

export interface ContentListParams {
  keyword?: string
  tag?: string
  yearMonth?: string
  status?: 'published' | 'draft'
  topicId?: string
}

function unwrapList<T>(data: PageResult<T> | T[]): T[] {
  return Array.isArray(data) ? data : (data.list ?? [])
}

function buildListQuery(
  base: Record<string, string>,
  params?: ContentListParams,
): URLSearchParams {
  const q = new URLSearchParams(base)
  if (params?.keyword) q.set('keyword', params.keyword)
  if (params?.tag) q.set('tag', params.tag)
  if (params?.yearMonth) q.set('yearMonth', params.yearMonth)
  if (params?.status) q.set('status', params.status)
  if (params?.topicId) q.set('topicId', params.topicId)
  return q
}

export async function fetchProfile(): Promise<ProfileData> {
  return get<ProfileData>('/profile')
}

/** 着陆页 / 游客读取管理员公开资料（无需登录） */
export async function fetchPublicProfile(): Promise<ProfileData> {
  try {
    return await get<ProfileData>('/profile/public', { auth: false })
  } catch (e) {
    if (e instanceof ApiError && (e.code === 40404 || e.code === 404 || e.code === 405)) {
      return get<ProfileData>('/profile', { auth: false })
    }
    throw e
  }
}

/** 指定用户的公开资料（后续多用户主页） */
export async function fetchUserProfile(userId: number): Promise<ProfileData> {
  return get<ProfileData>(`/profile/users/${userId}`, { auth: false })
}

export async function updateProfileApi(
  data: Partial<ProfileData>,
): Promise<ProfileData> {
  return put<ProfileData>('/profile', data)
}

export async function uploadProfileAvatar(
  file: File,
): Promise<{ avatarUrl: string }> {
  const form = new FormData()
  form.append('file', file)
  return post<{ avatarUrl: string }>('/profile/avatar', form)
}

export async function uploadContentImage(file: File): Promise<{ url: string }> {
  const form = new FormData()
  form.append('file', file)
  return post<{ url: string }>('/uploads/images', form)
}

export async function fetchTopics(): Promise<TopicItem[]> {
  return get<TopicItem[]>('/topics')
}

export async function fetchNotes(params?: ContentListParams): Promise<NoteItem[]> {
  const q = buildListQuery({ page: '1', pageSize: '200', sort: 'date_desc' }, params)
  const data = await get<PageResult<NoteItem> | NoteItem[]>(`/notes?${q.toString()}`)
  return unwrapList(data)
}

export async function createNoteApi(
  body: Omit<NoteItem, 'id' | 'date' | 'topicId'> & {
    topicId?: string
    topicTitle?: string
    agentSessionId?: string
  },
): Promise<NoteItem> {
  return post<NoteItem>('/notes', body)
}

export async function updateNoteApi(
  id: string,
  body: Partial<NoteItem> & { topicTitle?: string; agentSessionId?: string },
): Promise<NoteItem> {
  return put<NoteItem>(`/notes/${id}`, body)
}

export async function deleteNoteApi(id: string): Promise<void> {
  await del<null>(`/notes/${id}`)
}

export async function pinNoteApi(id: string): Promise<NoteItem> {
  return post<NoteItem>(`/notes/${id}/pin`, {})
}

export async function fetchLife(params?: ContentListParams): Promise<LifeItem[]> {
  const q = buildListQuery({ page: '1', pageSize: '200', sort: 'date_desc' }, params)
  const data = await get<PageResult<LifeItem> | LifeItem[]>(`/life?${q.toString()}`)
  return unwrapList(data)
}

export async function pinLifeApi(id: string): Promise<LifeItem> {
  return post<LifeItem>(`/life/${id}/pin`, {})
}

export async function createLifeApi(
  body: Omit<LifeItem, 'id' | 'date'>,
): Promise<LifeItem> {
  return post<LifeItem>('/life', body)
}

export async function updateLifeApi(
  id: string,
  body: Partial<LifeItem>,
): Promise<LifeItem> {
  return put<LifeItem>(`/life/${id}`, body)
}

export async function deleteLifeApi(id: string): Promise<void> {
  await del<null>(`/life/${id}`)
}

export async function fetchTimeline(): Promise<TimelineItem[]> {
  return get<TimelineItem[]>('/timeline')
}

export async function searchContent(q: string, limit = 30): Promise<SearchResult> {
  const params = new URLSearchParams({ q, limit: String(limit) })
  return get<SearchResult>(`/search?${params.toString()}`)
}

export async function fetchTagCloud(): Promise<TagCountItem[]> {
  return get<TagCountItem[]>('/meta/tags')
}

export async function fetchArchiveMonths(): Promise<ArchiveMonthItem[]> {
  return get<ArchiveMonthItem[]>('/meta/archive-months')
}
