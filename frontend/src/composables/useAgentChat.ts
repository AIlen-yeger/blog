import { computed, ref } from 'vue'
import { ApiError } from '@/api/http'
import { hasValidSession } from '@/composables/useSession'
import {
  streamAgentChat,
  type ChatTurn,
  type PlanStep,
  type PlanStepStatus,
  type PublishNotePreviewData,
} from '@/api/agentChat'
import { publishNoteAction } from '@/api/agentActions'
import {
  createAgentSessionRemote,
  deleteAgentSessionRemote,
  fetchAgentSessions,
  updateSessionTitleRemote,
  type AgentSessionRecord,
} from '@/api/agentSessions'
import { uploadContentImage, uploadDocument } from '@/api/blog'
import {
  stripPlanPrefix,
  type AgentAttachmentPayload,
  type ExecutionMode,
} from '@/utils/agentPayload'
import {
  AGENT_SESSION_NOT_FOUND,
  ensureAgentSessionId,
  loadServerMessages,
  recoverStaleAgentSession,
} from '@/composables/agentSessionBridge'
import {
  refreshMusicTracksAfterAgentAdd,
  replyIndicatesMusicPlaylistSaved,
} from '@/composables/useUserMusicTracks'
import type { ChatAttachmentMeta, AgentChatSession } from '@/utils/agentSessionsStorage'
import {
  createLocalAgentSession,
  deleteLocalAgentSession,
  ensureLocalDefaultSession,
  getActiveSessionId,
  loadAgentSessions,
  setActiveSessionId,
  upsertLocalSession,
} from '@/utils/agentSessionsStorage'
import { genId } from '@/utils/id'
import { toUserErrorMessage } from '@/utils/userErrorMessage'

export interface PendingAttachment {
  id: string
  file: File
  name: string
  type: 'image' | 'text' | 'document'
  mime?: string
  preview?: string
  textContent?: string
}

export interface PendingActionPreview {
  action: string
  data: PublishNotePreviewData
}

export interface AgentChatSendOptions {
  isLoggedIn?: () => boolean
  onLoginRequired?: () => void
}

const sessions = ref<AgentChatSession[]>([])
const activeSessionId = ref(getActiveSessionId() ?? '')
const input = ref('')
const streamingText = ref('')
const isStreaming = ref(false)
const sessionsLoading = ref(false)
const messagesLoading = ref(false)
const error = ref('')
const loginRequired = ref(false)
const pendingAttachments = ref<PendingAttachment[]>([])
const pendingActionPreview = ref<PendingActionPreview | null>(null)
const publishNoteLoading = ref(false)
const planSteps = ref<PlanStep[]>([])

const PLAN_MODE_KEY = 'kohaku-agent-plan-mode'

function loadPlanModeEnabled(): boolean {
  try {
    return localStorage.getItem(PLAN_MODE_KEY) === 'true'
  } catch {
    return false
  }
}

const planModeEnabled = ref(loadPlanModeEnabled())
const sidebarOpen = ref(
  typeof window !== 'undefined' ? window.innerWidth >= 768 : true,
)

let abortCtrl: AbortController | null = null

function fromApiSession(row: AgentSessionRecord): AgentChatSession {
  return {
    sessionId: row.sessionId,
    title: row.title,
    messages: [],
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  }
}

function isLoggedIn(options?: AgentChatSendOptions) {
  return options?.isLoggedIn?.() ?? hasValidSession()
}

const activeSession = computed(() => {
  return (
    sessions.value.find((s) => s.sessionId === activeSessionId.value) ??
    sessions.value[0] ??
    null
  )
})

const messages = computed(() => activeSession.value?.messages ?? [])

async function loadMessagesForSession(sessionId: string) {
  if (!hasValidSession()) return
  messagesLoading.value = true
  try {
    const rows = await loadServerMessages(sessionId)
    const idx = sessions.value.findIndex((s) => s.sessionId === sessionId)
    if (idx >= 0) {
      sessions.value[idx] = { ...sessions.value[idx], messages: rows }
    }
  } catch (e) {
    if (e instanceof ApiError && e.code === AGENT_SESSION_NOT_FOUND) {
      try {
        const newId = await recoverStaleAgentSession()
        await refreshSessions()
        if (newId) await loadMessagesForSession(newId)
        return
      } catch {
        /* fall through */
      }
    }
    error.value = toUserErrorMessage(e, '加载消息失败')
  } finally {
    messagesLoading.value = false
  }
}

async function refreshSessions() {
  if (hasValidSession()) {
    sessionsLoading.value = true
    try {
      const rows = await fetchAgentSessions()
      const prevMessages = new Map(
        sessions.value.map((s) => [s.sessionId, s.messages] as const),
      )
      sessions.value = rows.map((row) => {
        const session = fromApiSession(row)
        const cached = prevMessages.get(session.sessionId)
        if (cached?.length) session.messages = cached
        return session
      })
      const activeId = getActiveSessionId()
      if (activeId && sessions.value.some((s) => s.sessionId === activeId)) {
        activeSessionId.value = activeId
      } else if (sessions.value[0]) {
        activeSessionId.value = sessions.value[0].sessionId
        setActiveSessionId(sessions.value[0].sessionId)
      } else {
        activeSessionId.value = ''
      }
      if (activeSessionId.value) {
        await loadMessagesForSession(activeSessionId.value)
      }
    } catch (e) {
      error.value = toUserErrorMessage(e, '加载对话列表失败')
    } finally {
      sessionsLoading.value = false
    }
    return
  }

  sessions.value = loadAgentSessions()
  const active = getActiveSessionId()
  if (active) activeSessionId.value = active
  else if (sessions.value[0]) {
    activeSessionId.value = sessions.value[0].sessionId
    setActiveSessionId(sessions.value[0].sessionId)
  }
}

async function selectSession(id: string) {
  activeSessionId.value = id
  setActiveSessionId(id)
  clearError()
  streamingText.value = ''
  if (hasValidSession()) {
    await loadMessagesForSession(id)
  }
}

async function startNewSession() {
  clearError()
  input.value = ''
  pendingAttachments.value = []
  if (hasValidSession()) {
    sessionsLoading.value = true
    try {
      const created = await createAgentSessionRemote()
      const session = fromApiSession(created)
      sessions.value = [session, ...sessions.value.filter((s) => s.sessionId !== session.sessionId)]
      await selectSession(session.sessionId)
    } catch (e) {
      error.value = toUserErrorMessage(e, '创建对话失败')
    } finally {
      sessionsLoading.value = false
    }
    return
  }
  const session = createLocalAgentSession()
  sessions.value = loadAgentSessions()
  await selectSession(session.sessionId)
}

async function removeSession(id: string) {
  clearError()
  if (hasValidSession()) {
    try {
      await deleteAgentSessionRemote(id)
      await refreshSessions()
    } catch (e) {
      error.value = toUserErrorMessage(e, '删除对话失败')
      return
    }
  } else {
    deleteLocalAgentSession(id)
    sessions.value = loadAgentSessions()
  }
  if (!activeSessionId.value || !sessions.value.some((s) => s.sessionId === activeSessionId.value)) {
    if (sessions.value[0]) {
      await selectSession(sessions.value[0].sessionId)
    } else if (hasValidSession()) {
      await startNewSession()
    } else {
      const fallback = ensureLocalDefaultSession()
      sessions.value = loadAgentSessions()
      await selectSession(fallback.sessionId)
    }
  }
}

function clearError() {
  error.value = ''
  loginRequired.value = false
}

function deriveTitle(text: string, currentTitle: string) {
  if (currentTitle !== '新对话' && currentTitle !== '对话') return currentTitle
  const trimmed = text.trim()
  if (!trimmed) return currentTitle
  return trimmed.length > 24 ? `${trimmed.slice(0, 24)}…` : trimmed
}

const TEXT_FILE_RE = /\.(txt|json|csv|log|xml|yaml|yml|js|ts|py|java|html|css)$/i
const MARKDOWN_FILE_RE = /\.(md|markdown)$/i
const DOCUMENT_FILE_RE = /\.(pdf|docx?)$/i

async function prepareAttachment(file: File): Promise<PendingAttachment> {
  const isImage = file.type.startsWith('image/')
  const isMarkdown = MARKDOWN_FILE_RE.test(file.name)
  const isDocument =
    DOCUMENT_FILE_RE.test(file.name) ||
    isMarkdown ||
    file.type === 'application/pdf' ||
    file.type.includes('wordprocessingml') ||
    file.type === 'application/msword'
  const isText = file.type.startsWith('text/') || TEXT_FILE_RE.test(file.name)
  if (!isImage && !isText && !isDocument) {
    throw new Error(`暂不支持「${file.name}」类型，请上传图片、文本或 PDF/DOCX`)
  }
  if (isDocument) {
    if (file.size > 10 * 1024 * 1024) {
      throw new Error(`「${file.name}」超过 10MB 上限`)
    }
    return {
      id: genId('att'),
      file,
      name: file.name,
      type: 'document',
      mime: file.type || 'application/octet-stream',
    }
  }
  if (isImage) {
    return {
      id: genId('att'),
      file,
      name: file.name,
      type: 'image',
      preview: URL.createObjectURL(file),
    }
  }
  const textContent = await file.text()
  if (textContent.length > 120_000) {
    throw new Error(`「${file.name}」过大，请控制在 120KB 以内`)
  }
  return {
    id: genId('att'),
    file,
    name: file.name,
    type: 'text',
    textContent,
  }
}

async function addFiles(files: FileList | File[]) {
  clearError()
  const list = Array.from(files)
  for (const file of list) {
    try {
      const att = await prepareAttachment(file)
      pendingAttachments.value.push(att)
    } catch (e) {
      error.value = toUserErrorMessage(e, '文件添加失败')
    }
  }
}

function removeAttachment(id: string) {
  const item = pendingAttachments.value.find((a) => a.id === id)
  if (item?.preview?.startsWith('blob:')) {
    URL.revokeObjectURL(item.preview)
  }
  pendingAttachments.value = pendingAttachments.value.filter((a) => a.id !== id)
}

async function buildAttachmentMeta(
  attachments: PendingAttachment[],
): Promise<{ meta: ChatAttachmentMeta[]; payload: AgentAttachmentPayload[]; extra: string }> {
  const meta: ChatAttachmentMeta[] = []
  const payload: AgentAttachmentPayload[] = []
  const parts: string[] = []
  for (const att of attachments) {
    if (att.type === 'image') {
      const { url } = await uploadContentImage(att.file)
      meta.push({ id: att.id, name: att.name, type: 'image', url })
      payload.push({ id: att.id, name: att.name, mime: att.file.type || 'image/*', url, kind: 'image' })
      parts.push(`\n\n![${att.name}](${url})`)
      continue
    }
    if (att.type === 'document') {
      const uploaded = await uploadDocument(att.file)
      meta.push({
        id: att.id,
        name: att.name,
        type: 'document',
        url: uploaded.url,
        mime: uploaded.mime,
      })
      payload.push({
        id: att.id,
        name: att.name,
        mime: uploaded.mime,
        url: uploaded.url,
        kind: 'document',
      })
      parts.push(`\n\n[附件：${att.name}]`)
      continue
    }
    const content = att.textContent ?? ''
    meta.push({ id: att.id, name: att.name, type: 'text' })
    payload.push({
      id: att.id,
      name: att.name,
      mime: att.file.type || 'text/plain',
      kind: 'text',
      text: content,
    })
    parts.push(`\n\n---\n附件：${att.name}\n\`\`\`\n${content}\n\`\`\``)
  }
  return { meta, payload, extra: parts.join('') }
}

function togglePlanMode() {
  planModeEnabled.value = !planModeEnabled.value
  try {
    localStorage.setItem(PLAN_MODE_KEY, String(planModeEnabled.value))
  } catch {
    /* ignore */
  }
}

function updatePlanStep(update: { stepId: string; status: PlanStepStatus; summary?: string }) {
  const idx = planSteps.value.findIndex((s) => s.id === update.stepId)
  if (idx < 0) return
  const next = [...planSteps.value]
  next[idx] = {
    ...next[idx],
    status: update.status,
    summary: update.summary ?? next[idx].summary,
  }
  planSteps.value = next
}

async function sendMessage(options?: AgentChatSendOptions) {
  const rawText = input.value.trim()
  const { question: strippedText, forcePlan } = stripPlanPrefix(rawText)
  const text = strippedText || rawText
  const executionMode: ExecutionMode =
    planModeEnabled.value || forcePlan ? 'plan' : 'auto'
  const hasAttachments = pendingAttachments.value.length > 0
  if ((!text && !hasAttachments) || isStreaming.value) return

  const loggedIn = isLoggedIn(options)
  if (!loggedIn) {
    loginRequired.value = true
    error.value = '访客模式无法对话，请先登录'
    options?.onLoginRequired?.()
    return
  }

  let session: AgentChatSession | null = activeSession.value
  if (!session) {
    if (hasValidSession()) {
      const sessionId = await ensureAgentSessionId()
      await refreshSessions()
      session = sessions.value.find((s) => s.sessionId === sessionId) ?? null
      if (session) await selectSession(session.sessionId)
    } else {
      session = ensureLocalDefaultSession()
      sessions.value = loadAgentSessions()
      await selectSession(session.sessionId)
    }
  }
  if (!session) return

  clearError()

  let attachmentMeta: ChatAttachmentMeta[] = []
  let attachmentPayload: AgentAttachmentPayload[] = []
  let content = text
  pendingActionPreview.value = null
  planSteps.value = []
  try {
    if (hasAttachments) {
      const built = await buildAttachmentMeta([...pendingAttachments.value])
      attachmentMeta = built.meta
      attachmentPayload = built.payload
      content = `${text}${built.extra}`.trim()
    }
  } catch (e) {
    error.value = toUserErrorMessage(e, '附件上传失败')
    return
  }

  for (const att of pendingAttachments.value) {
    if (att.preview?.startsWith('blob:')) URL.revokeObjectURL(att.preview)
  }
  pendingAttachments.value = []
  input.value = ''

  const isFirstUserTurn = session.messages.filter((m) => m.role === 'user').length === 0
  const nextTitle = deriveTitle(content, session.title)
  session.title = nextTitle
  session.messages.push({
    id: genId('u'),
    role: 'user',
    content,
    createdAt: Date.now(),
    attachments: attachmentMeta.length ? attachmentMeta : undefined,
  })
  session.updatedAt = Date.now()
  if (!hasValidSession()) {
    upsertLocalSession(session)
    sessions.value = loadAgentSessions()
  }

  const turns: ChatTurn[] = session.messages.map((m) => ({
    role: m.role,
    content: m.content,
  }))

  isStreaming.value = true
  streamingText.value = ''
  abortCtrl = new AbortController()
  let agentIntent = ''

  try {
    await streamAgentChat(
      turns,
      (piece) => {
        streamingText.value += piece
      },
      abortCtrl.signal,
      {
        sessionId: session.sessionId,
        attachments: attachmentPayload.length ? attachmentPayload : undefined,
        executionMode,
        onMeta: (meta) => {
          if (meta.intent) agentIntent = meta.intent
        },
        onActionPreview: (preview) => {
          pendingActionPreview.value = preview
        },
        onPlan: (steps) => {
          planSteps.value = steps
        },
        onPlanStep: (update) => {
          updatePlanStep(update)
        },
      },
    )

    const reply = streamingText.value.trim() || '（没有收到回复）'
    session.messages.push({
      id: genId('a'),
      role: 'assistant',
      content: reply,
      createdAt: Date.now(),
    })
    session.updatedAt = Date.now()

    if (hasValidSession()) {
      if (isFirstUserTurn && nextTitle !== '新对话') {
        try {
          await updateSessionTitleRemote(session.sessionId, nextTitle)
        } catch {
          /* Python save_turn 也会更新标题 */
        }
      }
      await refreshSessions()
    } else {
      upsertLocalSession(session)
      sessions.value = loadAgentSessions()
    }

    if (
      replyIndicatesMusicPlaylistSaved(reply) ||
      (agentIntent === 'music' && /播放列表|已保存|添加/.test(reply))
    ) {
      await refreshMusicTracksAfterAgentAdd()
    }
  } catch (e) {
    if (abortCtrl?.signal.aborted) return
    error.value = toUserErrorMessage(e, '发送失败，请稍后重试')
  } finally {
    isStreaming.value = false
    streamingText.value = ''
    abortCtrl = null
  }
}

function stopStreaming() {
  const session = activeSession.value
  const partial = streamingText.value.trim()
  abortCtrl?.abort()
  abortCtrl = null
  if (partial && session) {
    session.messages.push({
      id: genId('a'),
      role: 'assistant',
      content: partial,
      createdAt: Date.now(),
    })
    session.updatedAt = Date.now()
    if (!hasValidSession()) {
      upsertLocalSession(session)
      sessions.value = loadAgentSessions()
    }
  }
  isStreaming.value = false
  streamingText.value = ''
}

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

function dismissActionPreview() {
  pendingActionPreview.value = null
}

async function confirmPublishNote(edits?: { title?: string; topicTitle?: string }) {
  const preview = pendingActionPreview.value
  if (!preview || preview.action !== 'publish_note') return
  if (!hasValidSession()) {
    loginRequired.value = true
    error.value = '请先登录后再发布笔记'
    return
  }
  const session = activeSession.value
  const data = preview.data
  const title = (edits?.title ?? data.title).trim()
  const topicTitle = (edits?.topicTitle ?? data.topicTitle ?? '随笔').trim() || '随笔'
  const content = (data.content || data.contentPreview || '').trim()
  if (!title || !content) {
    error.value = '标题或正文为空，无法发布'
    return
  }
  publishNoteLoading.value = true
  clearError()
  try {
    const note = await publishNoteAction({
      title,
      content,
      topicTitle,
      sessionId: session?.sessionId ?? data.sessionId,
      status: 'published',
    })
    pendingActionPreview.value = null
    if (session) {
      const sessionId = session.sessionId
      const successMsg = `笔记已发布：《${note.title}》`
      await refreshSessions()
      const target = sessions.value.find((s) => s.sessionId === sessionId)
      if (target) {
        target.messages.push({
          id: genId('a'),
          role: 'assistant',
          content: successMsg,
          createdAt: Date.now(),
        })
        target.updatedAt = Date.now()
      }
    }
  } catch (e) {
    error.value = toUserErrorMessage(e, '发布笔记失败')
  } finally {
    publishNoteLoading.value = false
  }
}

export function useAgentChat() {
  return {
    sessions,
    activeSessionId,
    activeSession,
    messages,
    input,
    streamingText,
    isStreaming,
    sessionsLoading,
    messagesLoading,
    error,
    loginRequired,
    pendingAttachments,
    pendingActionPreview,
    publishNoteLoading,
    planSteps,
    planModeEnabled,
    sidebarOpen,
    selectSession,
    startNewSession,
    removeSession,
    sendMessage,
    stopStreaming,
    addFiles,
    removeAttachment,
    dismissActionPreview,
    confirmPublishNote,
    togglePlanMode,
    clearError,
    toggleSidebar,
    refreshSessions,
  }
}
