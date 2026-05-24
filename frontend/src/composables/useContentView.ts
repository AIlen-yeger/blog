import { ref, watch, type Ref } from 'vue'
import { recordContentViewApi } from '@/api/views'
import type { ContentKind } from '@/types/views'

const SESSION_KEY = 'personal-blog-view-session'

function sessionMark(kind: ContentKind, id: string) {
  const key = `${kind}:${id}`
  const set = new Set<string>(JSON.parse(sessionStorage.getItem(SESSION_KEY) || '[]'))
  set.add(key)
  sessionStorage.setItem(SESSION_KEY, JSON.stringify([...set]))
}

function hasSessionMark(kind: ContentKind, id: string): boolean {
  const key = `${kind}:${id}`
  const list: string[] = JSON.parse(sessionStorage.getItem(SESSION_KEY) || '[]')
  return list.includes(key)
}

/**
 * 卡片展开时上报浏览；同一会话内不重复请求。
 */
export function useContentViewTracking(
  kind: ContentKind,
  getId: () => string,
  getInitialCount: () => number | undefined,
  expanded: Ref<boolean>,
) {
  const viewCount = ref(getInitialCount() ?? 0)

  watch(
    () => getInitialCount(),
    (value) => {
      if (value != null) viewCount.value = value
    },
  )

  watch(expanded, async (open) => {
    if (!open) return
    const id = getId()
    if (!id || hasSessionMark(kind, id)) return

    try {
      const result = await recordContentViewApi(kind, id)
      viewCount.value = result.viewCount
      sessionMark(kind, id)
    } catch (error) {
      console.warn('[personal-blog] 记录浏览失败', error)
    }
  })

  return { viewCount }
}
