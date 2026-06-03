import { fetchNoteApi } from '@/api/blog'
import { useMockApi } from '@/api/http'
import type { NoteItem } from '@/data/mockContent'
import {
  markNoteFresh,
  patchNoteInStore,
  reloadBlogData,
} from '@/composables/useBlogStore'

const activePolls = new Map<string, ReturnType<typeof setTimeout>>()

function schedule(noteId: string, fn: () => void, delayMs: number) {
  const prev = activePolls.get(noteId)
  if (prev) clearTimeout(prev)
  activePolls.set(
    noteId,
    setTimeout(() => {
      activePolls.delete(noteId)
      fn()
    }, delayMs),
  )
}

function stopPoll(noteId: string) {
  const t = activePolls.get(noteId)
  if (t) clearTimeout(t)
  activePolls.delete(noteId)
}

/** 发布后轮询，有回复或任务结束时刷新列表 */
export function watchNoteAgentReply(noteId: string, opts?: { scrollToCard?: boolean }) {
  if (!noteId || useMockApi()) return

  let attempts = 0
  const maxAttempts = 60

  async function tick() {
    attempts += 1
    let note: NoteItem | null = null
    try {
      note = await fetchNoteApi(noteId)
      patchNoteInStore(note)
    } catch (e) {
      console.warn('[agent-reply] poll failed', noteId, e)
    }

    const reply = (note?.agentReply || '').trim()
    const st = (note?.agentReplyStatus || '').toLowerCase()

    if (reply) {
      stopPoll(noteId)
      if (opts?.scrollToCard) {
        requestAnimationFrame(() => {
          document.getElementById(`note-${noteId}`)?.scrollIntoView({
            behavior: 'smooth',
            block: 'nearest',
          })
        })
      }
      return
    }

    if (st === 'done' || st === 'failed' || st === 'none') {
      await reloadBlogData().catch(() => {})
      stopPoll(noteId)
      return
    }

    if (attempts % 4 === 0) {
      await reloadBlogData().catch(() => {})
    }

    if (attempts >= maxAttempts) {
      await reloadBlogData().catch(() => {})
      stopPoll(noteId)
      return
    }

    schedule(noteId, () => void tick(), 2000)
  }

  markNoteFresh(noteId)
  schedule(noteId, () => void tick(), 600)
}
