import { computed, ref } from 'vue'
import { hasValidSession } from '@/composables/useSession'
import { streamAgentChat, type ChatTurn } from '@/api/agentChat'
import { ensureAgentSessionId, loadServerMessages } from '@/composables/agentSessionBridge'
import { bubbleTierFromText } from '@/utils/bubbleSize'
import {
  ensureLocalDefaultSession,
  getActiveSessionId,
  setActiveSessionId,
  upsertLocalSession,
  type ChatMessage,
} from '@/utils/agentSessionsStorage'
import { genId } from '@/utils/id'
import { toUserErrorMessage } from '@/utils/userErrorMessage'
import {
  refreshMusicTracksAfterAgentAdd,
  replyIndicatesMusicPlaylistSaved,
} from '@/composables/useUserMusicTracks'

export type { ChatMessage } from '@/utils/agentSessionsStorage'

export interface DesktopPetChatOptions {
  isLoggedIn?: () => boolean
  onLoginRequired?: () => void
}

const messagesRef = ref<ChatMessage[]>([])
const input = ref('')
const streamingText = ref('')
const isStreaming = ref(false)
const historyOpen = ref(false)
const error = ref('')
const loginRequired = ref(false)

let abortCtrl: AbortController | null = null

async function reloadMessages() {
  if (hasValidSession()) {
    const sessionId = getActiveSessionId() ?? (await ensureAgentSessionId())
    setActiveSessionId(sessionId)
    try {
      messagesRef.value = await loadServerMessages(sessionId)
    } catch (e) {
      error.value = toUserErrorMessage(e, '加载消息失败')
      messagesRef.value = []
    }
    return
  }
  const session = ensureLocalDefaultSession()
  messagesRef.value = session.messages
}

const history = computed(() => messagesRef.value)

const displayText = computed(() => {
  if (isStreaming.value) return streamingText.value
  const last = [...history.value].reverse().find((m) => m.role === 'assistant')
  return last?.content ?? '你好呀，我是kohaku'
})

const bubbleTier = computed(() => bubbleTierFromText(displayText.value))

const hasHistory = computed(() => history.value.length > 0)

function toggleHistory() {
  historyOpen.value = !historyOpen.value
  if (historyOpen.value) {
    void reloadMessages()
  }
}

function clearError() {
  error.value = ''
  loginRequired.value = false
}

async function sendMessage(options?: DesktopPetChatOptions) {
  const text = input.value.trim()
  if (!text || isStreaming.value) return

  const loggedIn = options?.isLoggedIn?.() ?? hasValidSession()
  if (!loggedIn) {
    loginRequired.value = true
    error.value = '访客模式无法对话，请先登录'
    options?.onLoginRequired?.()
    return
  }

  clearError()
  const sessionId = await ensureAgentSessionId()
  setActiveSessionId(sessionId)

  const userMessage: ChatMessage = {
    id: genId('u'),
    role: 'user',
    content: text,
    createdAt: Date.now(),
  }
  messagesRef.value.push(userMessage)
  if (!hasValidSession()) {
    const session = ensureLocalDefaultSession()
    session.messages = [...messagesRef.value]
    upsertLocalSession(session)
  }
  input.value = ''

  const turns: ChatTurn[] = messagesRef.value.map((m) => ({
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
        sessionId,
        onMeta: (meta) => {
          if (meta.intent) agentIntent = meta.intent
        },
      },
    )

    const reply = streamingText.value.trim() || '（没有收到回复）'
    messagesRef.value.push({
      id: genId('a'),
      role: 'assistant',
      content: reply,
      createdAt: Date.now(),
    })
    if (!hasValidSession()) {
      const session = ensureLocalDefaultSession()
      session.messages = [...messagesRef.value]
      upsertLocalSession(session)
    } else {
      await reloadMessages()
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
  const partial = streamingText.value.trim()
  abortCtrl?.abort()
  abortCtrl = null
  if (partial) {
    messagesRef.value.push({
      id: genId('a'),
      role: 'assistant',
      content: partial,
      createdAt: Date.now(),
    })
    if (!hasValidSession()) {
      const session = ensureLocalDefaultSession()
      session.messages = [...messagesRef.value]
      upsertLocalSession(session)
    }
  }
  isStreaming.value = false
  streamingText.value = ''
}

function clearHistory() {
  messagesRef.value = []
  if (!hasValidSession()) {
    const session = ensureLocalDefaultSession()
    session.messages = []
    upsertLocalSession(session)
  }
}

void reloadMessages()

export function useDesktopPetChat() {
  return {
    history,
    input,
    streamingText,
    isStreaming,
    historyOpen,
    error,
    loginRequired,
    displayText,
    bubbleTier,
    hasHistory,
    toggleHistory,
    sendMessage,
    stopStreaming,
    clearError,
    clearHistory,
  }
}
