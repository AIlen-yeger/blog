import { post } from '@/api/http'
import type { NoteItem } from '@/api/blog'

export interface PublishNoteActionRequest {
  title: string
  content: string
  topicTitle?: string
  sessionId?: string
  status?: string
}

export async function publishNoteAction(body: PublishNoteActionRequest): Promise<NoteItem> {
  return post<NoteItem>('/agent/actions/publish-note', body)
}
