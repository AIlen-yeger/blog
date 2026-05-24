import { post, useMockApi } from '@/api/http'
import { mockRecordContentView } from '@/api/mock/views'
import type { ContentKind, ViewRecordResult } from '@/types/views'

/**
 * 记录一次浏览（展开阅读时调用）。
 * 已登录时携带 JWT，按账号去重；未登录时服务端按匿名访客去重。
 */
export async function recordContentViewApi(
  kind: ContentKind,
  id: string,
): Promise<ViewRecordResult> {
  if (useMockApi()) {
    return mockRecordContentView(kind, id)
  }
  const path = kind === 'note' ? `/notes/${encodeURIComponent(id)}/views` : `/life/${encodeURIComponent(id)}/views`
  return post<ViewRecordResult>(path, {})
}
