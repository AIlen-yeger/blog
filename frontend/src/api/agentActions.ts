import { post, put } from '@/api/http'
import type { NoteItem } from '@/api/blog'

export interface PublishNoteActionRequest {
  title: string
  content: string
  topicTitle?: string
  sessionId?: string
  status?: string
}

export interface UpdateNoteActionRequest {
  noteId: string
  title: string
  content: string
  topicTitle?: string
  status?: string
}

export async function publishNoteAction(body: PublishNoteActionRequest): Promise<NoteItem> {
  return post<NoteItem>('/agent/actions/publish-note', body)
}

/** 更新笔记，不触发 Agent 回复 */
export async function updateNoteAction(body: UpdateNoteActionRequest): Promise<NoteItem> {
  return put<NoteItem>('/agent/actions/update-note', body)
}
