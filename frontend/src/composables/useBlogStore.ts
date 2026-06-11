import { reactive, ref, toRefs, watch } from 'vue'
import type {
  ArchiveMonthItem,
  ContentPublishStatus,
  LifeItem,
  NoteItem,
  ProfileData,
  SearchResult,
  TagCountItem,
  TimelineItem,
  TopicItem,
} from '@/data/mockContent'
import {
  defaultProfile,
  mockLife as seedLife,
  mockNotes as seedNotes,
  mockTimeline as seedTimeline,
  mockTopics as seedTopics,
} from '@/data/mockContent'
import { genId, todayISO } from '@/utils/id'
import { toUserErrorMessage } from '@/utils/userErrorMessage'
import { hasValidSession } from '@/composables/useSession'
import { useMockApi } from '@/api/http'
import * as blogApi from '@/api/blog'
import { getAgentSessionId } from '@/utils/agentSession'
import type { ContentListParams } from '@/api/blog'
import { useAgentReplySettings } from '@/composables/useAgentReplySettings'
import { useContentViewer } from '@/composables/useContentViewer'

const STORAGE_KEY = 'personal-blog-data'

interface BlogState {
  profile: ProfileData
  notes: NoteItem[]
  life: LifeItem[]
  topics: TopicItem[]
  timeline: TimelineItem[]
}

const state = reactive<BlogState>({
  profile: { ...defaultProfile },
  notes: [],
  life: [],
  topics: [],
  timeline: [],
})

const loading = ref(false)
const loadError = ref('')
const freshNoteIds = ref(new Set<string>())
const tagCloud = ref<TagCountItem[]>([])
const archiveMonths = ref<ArchiveMonthItem[]>([])
const searchResult = ref<SearchResult | null>(null)

const contentFilters = reactive<ContentListParams>({
  keyword: '',
  tag: undefined,
  yearMonth: undefined,
  status: undefined,
})

let hydrated = false
let loadPromise: Promise<void> | null = null

function resolveMockTopicId(topicId?: string, topicTitle?: string): string {
  if (topicId && state.topics.some((t) => t.id === topicId)) return topicId
  const title = (topicTitle ?? topicId ?? '').trim()
  if (!title) return state.topics[0]?.id ?? genId('t')
  const existing = state.topics.find((t) => t.title.toLowerCase() === title.toLowerCase())
  if (existing) return existing.id
  const id = genId('t')
  state.topics.push({
    id,
    title,
    excerpt: title.length > 48 ? `${title.slice(0, 48)}…` : title,
    tag: '专题',
    date: todayISO(),
  })
  return id
}

function loadLocal(): Partial<BlogState> | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as Partial<BlogState>
  } catch {
    return null
  }
}

function persistLocal() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      profile: state.profile,
      notes: state.notes,
      life: state.life,
      topics: state.topics,
      timeline: state.timeline,
    }),
  )
}

function hydrateLocal() {
  const saved = loadLocal()
  state.profile = { ...defaultProfile, ...saved?.profile }
  state.notes = saved?.notes?.length ? saved.notes : [...seedNotes]
  state.life = saved?.life?.length ? saved.life : [...seedLife]
  state.topics = saved?.topics?.length ? saved.topics : [...seedTopics]
  state.timeline = saved?.timeline?.length ? saved.timeline : [...seedTimeline]
  if (!saved) persistLocal()
}

function scrubAgentReplyForViewer<T extends NoteItem | LifeItem>(
  item: T,
  kind: 'note' | 'life',
): T {
  const { canViewAgentReply } = useAgentReplySettings()
  if (canViewAgentReply(kind)) return item
  return {
    ...item,
    agentReply: null,
    ...(kind === 'note' ? { agentReplyStatus: 'none' as const } : {}),
  }
}

function normalizeNote(n: NoteItem): NoteItem {
  return scrubAgentReplyForViewer(
    {
      ...n,
      pinned: Boolean(n.pinned),
      status: (n.status ?? 'published') as ContentPublishStatus,
    },
    'note',
  )
}

function filterContentForViewer<T extends NoteItem | LifeItem>(
  items: T[],
  kind: 'note' | 'life',
): T[] {
  const { isManageView } = useContentViewer()
  const normalized = items.map((item) =>
    kind === 'note' ? normalizeNote(item as NoteItem) : normalizeLife(item as LifeItem),
  ) as T[]
  if (isManageView.value) return normalized
  return normalized.filter((item) => item.status !== 'draft')
}

export function patchNoteInStore(note: NoteItem) {
  const normalized = normalizeNote(note)
  const idx = state.notes.findIndex((n) => n.id === normalized.id)
  if (idx >= 0) state.notes[idx] = normalized
  if (searchResult.value) {
    const si = searchResult.value.notes.findIndex((n) => n.id === normalized.id)
    if (si >= 0) searchResult.value.notes[si] = normalized
  }
}

export function markNoteFresh(noteId: string) {
  const next = new Set(freshNoteIds.value)
  next.add(noteId)
  freshNoteIds.value = next
  window.setTimeout(() => {
    const trimmed = new Set(freshNoteIds.value)
    trimmed.delete(noteId)
    freshNoteIds.value = trimmed
  }, 2600)
}

export function isNoteFresh(noteId: string): boolean {
  return freshNoteIds.value.has(noteId)
}

function normalizeLife(l: LifeItem): LifeItem {
  return scrubAgentReplyForViewer(
    {
      ...l,
      pinned: Boolean(l.pinned),
      status: (l.status ?? 'published') as ContentPublishStatus,
    },
    'life',
  )
}

function listParamsFromFilters(): ContentListParams | undefined {
  const p: ContentListParams = {}
  if (contentFilters.tag) p.tag = contentFilters.tag
  if (contentFilters.yearMonth) p.yearMonth = contentFilters.yearMonth
  if (contentFilters.status) p.status = contentFilters.status
  return Object.keys(p).length ? p : undefined
}

function filterMockNotes(notes: NoteItem[]) {
  const { isManageView } = useContentViewer()
  let list = [...notes]
  if (!isManageView.value) {
    list = list.filter((n) => n.status !== 'draft')
  }
  const kw = contentFilters.keyword?.trim().toLowerCase()
  if (kw) {
    list = list.filter(
      (n) =>
        n.title.toLowerCase().includes(kw) ||
        n.excerpt.toLowerCase().includes(kw) ||
        n.content.toLowerCase().includes(kw),
    )
  }
  if (contentFilters.tag) list = list.filter((n) => n.tag === contentFilters.tag)
  if (contentFilters.yearMonth) {
    list = list.filter((n) => n.date.startsWith(contentFilters.yearMonth!))
  }
  if (contentFilters.status) list = list.filter((n) => n.status === contentFilters.status)
  return list
}

function filterMockLife(items: LifeItem[]) {
  const { isManageView } = useContentViewer()
  let list = [...items]
  if (!isManageView.value) {
    list = list.filter((l) => l.status !== 'draft')
  }
  const kw = contentFilters.keyword?.trim().toLowerCase()
  if (kw) {
    list = list.filter(
      (l) =>
        l.title.toLowerCase().includes(kw) ||
        l.excerpt.toLowerCase().includes(kw) ||
        l.content.toLowerCase().includes(kw),
    )
  }
  if (contentFilters.tag) list = list.filter((l) => l.tag === contentFilters.tag)
  if (contentFilters.yearMonth) {
    list = list.filter((l) => l.date.startsWith(contentFilters.yearMonth!))
  }
  if (contentFilters.status) list = list.filter((l) => l.status === contentFilters.status)
  return list
}

function buildMockMeta() {
  const tagMap = new Map<string, number>()
  const monthMap = new Map<string, number>()
  for (const n of state.notes) {
    if (n.status === 'draft') continue
    tagMap.set(n.tag, (tagMap.get(n.tag) ?? 0) + 1)
    const m = n.date.slice(0, 7)
    monthMap.set(m, (monthMap.get(m) ?? 0) + 1)
  }
  for (const l of state.life) {
    if (l.status === 'draft') continue
    tagMap.set(l.tag, (tagMap.get(l.tag) ?? 0) + 1)
    const m = l.date.slice(0, 7)
    monthMap.set(m, (monthMap.get(m) ?? 0) + 1)
  }
  tagCloud.value = [...tagMap.entries()]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count)
  archiveMonths.value = [...monthMap.entries()]
    .map(([month, count]) => ({ month, count }))
    .sort((a, b) => b.month.localeCompare(a.month))
}

async function loadFromServer() {
  const listParams = listParamsFromFilters()
  const kw = contentFilters.keyword?.trim()
  const { usePublicContentApi } = useContentViewer()
  /** 预览模式不带 JWT，与真实访客看到的内容一致（无 Agent 回复、无草稿） */
  const publicContentOpts = usePublicContentApi.value ? { auth: false as const } : undefined

  const profileReq = hasValidSession()
    ? blogApi.fetchProfile()
    : blogApi.fetchPublicProfile()

  const [profile, topics, timeline, tags, months] = await Promise.all([
    profileReq,
    blogApi.fetchTopics(),
    blogApi.fetchTimeline(),
    blogApi.fetchTagCloud(publicContentOpts),
    blogApi.fetchArchiveMonths(publicContentOpts),
  ])

  tagCloud.value = tags
  archiveMonths.value = months
  state.profile = { ...defaultProfile, ...profile }
  state.topics = topics
  state.timeline = timeline

  if (kw) {
    const res = await blogApi.searchContent(kw, 30, publicContentOpts)
    searchResult.value = {
      notes: filterContentForViewer(res.notes, 'note'),
      life: filterContentForViewer(res.life, 'life'),
      noteTotal: res.noteTotal,
      lifeTotal: res.lifeTotal,
    }
  } else {
    searchResult.value = null
  }

  const [notes, life] = await Promise.all([
    blogApi.fetchNotes(listParams, publicContentOpts),
    blogApi.fetchLife(listParams, publicContentOpts),
  ])
  state.notes = filterContentForViewer(notes, 'note')
  state.life = filterContentForViewer(life, 'life')
}

async function ensureLoaded() {
  if (hydrated) return

  loading.value = true
  loadError.value = ''

  try {
    if (useMockApi()) {
      hydrateLocal()
      const allNotes = state.notes.map(normalizeNote)
      const allLife = state.life.map(normalizeLife)
      state.notes = allNotes
      state.life = allLife
      buildMockMeta()
      const kw = contentFilters.keyword?.trim().toLowerCase()
      if (kw) {
        const matchText = (s: string) => s.toLowerCase().includes(kw)
        searchResult.value = {
          notes: filterMockNotes(allNotes).filter(
            (n) => matchText(n.title) || matchText(n.excerpt) || matchText(n.content),
          ),
          life: filterMockLife(allLife).filter(
            (l) => matchText(l.title) || matchText(l.excerpt) || matchText(l.content),
          ),
          noteTotal: 0,
          lifeTotal: 0,
        }
      } else {
        searchResult.value = null
        state.notes = filterMockNotes(allNotes)
        state.life = filterMockLife(allLife)
      }
    } else {
      await loadFromServer()
    }
    hydrated = true
  } catch (e) {
    loadError.value = toUserErrorMessage(e, '内容加载失败，请稍后重试')
    console.warn('[personal-blog] 数据加载失败', e)
    if (!useMockApi()) {
      state.notes = []
      state.life = []
      state.topics = []
      state.timeline = []
    }
  } finally {
    loading.value = false
  }
}

/** 登录成功后强制从服务端重新拉取 */
export async function reloadBlogData() {
  hydrated = false
  loadPromise = null
  return startLoad()
}

let landingProfilePromise: Promise<void> | null = null

/** 着陆页加载管理员头像、昵称与签名 */
export function loadLandingProfile(): Promise<void> {
  if (landingProfilePromise) return landingProfilePromise

  landingProfilePromise = loadLandingProfileOnce().finally(() => {
    landingProfilePromise = null
  })
  return landingProfilePromise
}

async function loadLandingProfileOnce() {
  if (useMockApi()) {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<BlogState>
        if (parsed.profile) {
          state.profile = { ...defaultProfile, ...parsed.profile }
        }
      }
    } catch {
      /* 忽略本地缓存解析错误 */
    }
    return
  }

  try {
    const profile = await blogApi.fetchPublicProfile()
    state.profile = { ...defaultProfile, ...profile }
  } catch (e) {
    console.warn('[personal-blog] 着陆页资料加载失败', e)
  }
}

/** 退出登录时重置缓存，避免下一账号看到旧数据 */
export function resetBlogStore() {
  hydrated = false
  loadPromise = null
  loading.value = false
  loadError.value = ''
  state.profile = { ...defaultProfile }
  state.notes = []
  state.life = []
  state.topics = []
  state.timeline = []
  tagCloud.value = []
  archiveMonths.value = []
  searchResult.value = null
  contentFilters.keyword = ''
  contentFilters.tag = undefined
  contentFilters.yearMonth = undefined
  contentFilters.status = undefined
}

/** 返回着陆页时清除博客加载错误，避免再次进入仍显示红条 */
export function clearBlogLoadError() {
  loadError.value = ''
}

function startLoad() {
  if (!loadPromise) loadPromise = ensureLoaded()
  return loadPromise
}

if (useMockApi()) {
  watch(state, persistLocal, { deep: true })
}

export function useBlogStore() {
  async function updateProfile(patch: Partial<ProfileData>) {
    Object.assign(state.profile, patch)
    if (!useMockApi()) {
      const updated = await blogApi.updateProfileApi(patch)
      Object.assign(state.profile, updated)
    }
  }

  async function saveNote(
    payload: Omit<NoteItem, 'id' | 'date' | 'topicId'> & {
      id?: string
      date?: string
      topicId?: string
      topicTitle?: string
    },
  ) {
    if (payload.id) {
      const noteId = payload.id
      const existing = state.notes.find((n) => n.id === noteId)
      const nextStatus = (payload.status ?? existing?.status ?? 'published') as ContentPublishStatus
      const isPublishing = nextStatus === 'published'
      const wasDraft = existing?.status === 'draft'
      if (!useMockApi()) {
        const { id: _id, agentSessionId: _ignored, ...rest } = payload as typeof payload & {
          agentSessionId?: string
        }
        const updated = await blogApi.updateNoteApi(noteId, {
          ...rest,
          status: nextStatus,
          regenerateAgentReply: isPublishing && wasDraft,
          ...(isPublishing && wasDraft ? { agentSessionId: getAgentSessionId() } : {}),
        })
        const normalized = normalizeNote({
          ...updated,
          agentReplyStatus:
            updated.agentReplyStatus ||
            (isPublishing && !updated.agentReply?.trim() ? 'pending' : updated.agentReplyStatus),
        })
        const idx = state.notes.findIndex((n) => n.id === payload.id)
        if (idx >= 0) state.notes[idx] = normalized
        else if (isPublishing) state.notes.unshift(normalized)
        state.topics = await blogApi.fetchTopics()
        if (isPublishing && (wasDraft || !(updated.agentReply || '').trim())) {
          const { watchNoteAgentReply } = await import('@/composables/useNoteAgentReplyPoll')
          watchNoteAgentReply(noteId, { scrollToCard: wasDraft })
        }
        return payload.id
      }
      const idx = state.notes.findIndex((n) => n.id === payload.id)
      if (idx >= 0) {
        const resolvedTopicId = resolveMockTopicId(payload.topicId, payload.topicTitle)
        state.notes[idx] = {
          ...state.notes[idx],
          ...payload,
          id: payload.id,
          topicId: resolvedTopicId,
          date: payload.date ?? state.notes[idx].date,
        }
        return payload.id
      }
    }
    if (!useMockApi()) {
      const raw = await blogApi.createNoteApi({
        title: payload.title,
        excerpt: payload.excerpt,
        tag: payload.tag,
        ...(payload.topicId ? { topicId: payload.topicId } : {}),
        ...(payload.topicTitle ? { topicTitle: payload.topicTitle } : {}),
        content: payload.content,
        images: payload.images ?? [],
        status: payload.status,
        agentSessionId: getAgentSessionId(),
      })
      const isPublished = (payload.status ?? 'published') === 'published'
      const created = normalizeNote({
        ...raw,
        agentReplyStatus:
          raw.agentReplyStatus ||
          (isPublished && !raw.agentReply?.trim() ? 'pending' : raw.agentReplyStatus),
      })
      state.notes.unshift(created)
      state.topics = await blogApi.fetchTopics()
      if (isPublished) {
        const { watchNoteAgentReply } = await import('@/composables/useNoteAgentReplyPoll')
        watchNoteAgentReply(created.id, { scrollToCard: true })
      }
      return created.id
    }
    const topicId = resolveMockTopicId(payload.topicId, payload.topicTitle)
    const id = genId('n')
    const note: NoteItem = {
      id,
      title: payload.title,
      excerpt: payload.excerpt,
      tag: payload.tag,
      topicId,
      content: payload.content,
      images: payload.images ? [...payload.images] : [],
      date: payload.date ?? todayISO(),
      status: payload.status ?? 'published',
    }
    state.notes.unshift(note)
    return id
  }

  async function deleteNote(id: string) {
    if (!useMockApi()) await blogApi.deleteNoteApi(id)
    state.notes = state.notes.filter((n) => n.id !== id)
  }

  async function saveLife(
    payload: Omit<LifeItem, 'id' | 'date'> & { id?: string; date?: string },
  ) {
    if (payload.id) {
      if (!useMockApi()) {
        const updated = await blogApi.updateLifeApi(payload.id, payload)
        const idx = state.life.findIndex((l) => l.id === payload.id)
        if (idx >= 0) state.life[idx] = updated
        return payload.id
      }
      const idx = state.life.findIndex((l) => l.id === payload.id)
      if (idx >= 0) {
        state.life[idx] = {
          ...state.life[idx],
          ...payload,
          id: payload.id,
          date: payload.date ?? state.life[idx].date,
        }
        return payload.id
      }
    }
    if (!useMockApi()) {
      const created = await blogApi.createLifeApi({
        title: payload.title,
        excerpt: payload.excerpt,
        tag: payload.tag,
        content: payload.content,
        images: payload.images ?? [],
        status: payload.status,
      })
      state.life.unshift(created)
      return created.id
    }
    const id = genId('l')
    const item: LifeItem = {
      id,
      title: payload.title,
      excerpt: payload.excerpt,
      tag: payload.tag,
      content: payload.content,
      images: payload.images ? [...payload.images] : [],
      date: payload.date ?? todayISO(),
      status: payload.status ?? 'published',
    }
    state.life.unshift(item)
    return id
  }

  async function deleteLife(id: string) {
    if (!useMockApi()) await blogApi.deleteLifeApi(id)
    state.life = state.life.filter((l) => l.id !== id)
  }

  function getNotesByTopicId(topicId: string) {
    return state.notes
      .filter((n) => n.topicId === topicId)
      .sort((a, b) => Number(!!b.pinned) - Number(!!a.pinned))
  }

  function sortLifeByPinned(items: LifeItem[]) {
    return [...items].sort((a, b) => Number(!!b.pinned) - Number(!!a.pinned))
  }

  async function pinNote(id: string) {
    if (!useMockApi()) {
      const updated = await blogApi.pinNoteApi(id)
      const pinned = Boolean(updated.pinned)
      state.notes = state.notes.map((n) => {
        if (n.id === updated.id) return { ...updated, pinned }
        if (pinned) return { ...n, pinned: false }
        return n
      })
      return
    }
    const target = state.notes.find((n) => n.id === id)
    if (!target) return
    const nextPinned = !target.pinned
    state.notes = state.notes.map((n) => ({
      ...n,
      pinned: n.id === id ? nextPinned : false,
    }))
  }

  async function pinLife(id: string) {
    if (!useMockApi()) {
      const updated = await blogApi.pinLifeApi(id)
      const pinned = Boolean(updated.pinned)
      state.life = sortLifeByPinned(
        state.life.map((l) => {
          if (l.id === updated.id) return { ...updated, pinned }
          if (pinned) return { ...l, pinned: false }
          return l
        }),
      )
      return
    }
    const target = state.life.find((l) => l.id === id)
    if (!target) return
    const nextPinned = !target.pinned
    state.life = sortLifeByPinned(
      state.life.map((l) => ({
        ...l,
        pinned: l.id === id ? nextPinned : false,
      })),
    )
  }

  async function applyContentFilters(patch: Partial<ContentListParams>) {
    if (patch.keyword !== undefined) contentFilters.keyword = patch.keyword
    if (patch.tag !== undefined) contentFilters.tag = patch.tag || undefined
    if (patch.yearMonth !== undefined) contentFilters.yearMonth = patch.yearMonth || undefined
    if (patch.status !== undefined) contentFilters.status = patch.status
    hydrated = false
    loadPromise = null
    await startLoad()
  }

  async function clearContentFilters() {
    contentFilters.keyword = ''
    contentFilters.tag = undefined
    contentFilters.yearMonth = undefined
    contentFilters.status = undefined
    searchResult.value = null
    hydrated = false
    loadPromise = null
    await startLoad()
  }

  function getVisibleNotes(topicId: string) {
    if (searchResult.value) {
      return searchResult.value.notes
        .filter((n) => n.topicId === topicId)
        .sort((a, b) => Number(!!b.pinned) - Number(!!a.pinned))
    }
    return getNotesByTopicId(topicId)
  }

  function getVisibleLife() {
    if (searchResult.value) {
      return sortLifeByPinned(searchResult.value.life)
    }
    return sortLifeByPinned(state.life)
  }

  return {
    ...toRefs(state),
    loading,
    loadError,
    tagCloud,
    archiveMonths,
    searchResult,
    contentFilters,
    ensureLoaded: startLoad,
    reloadBlogData,
    applyContentFilters,
    clearContentFilters,
    updateProfile,
    saveNote,
    deleteNote,
    pinNote,
    pinLife,
    saveLife,
    deleteLife,
    getNotesByTopicId,
    getVisibleNotes,
    getVisibleLife,
    sortLifeByPinned,
  }
}
