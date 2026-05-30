import { computed, ref } from 'vue'
import { hasValidSession } from '@/composables/useSession'
import { streamAgentChat, type ChatTurn } from '@/api/agentChat'
import { bubbleTierFromText } from '@/utils/bubbleSize'
import { genId } from '@/utils/id'
import { toUserErrorMessage } from '@/utils/userErrorMessage'
import { notifyMusicTracksChanged } from '@/composables/useUserMusicTracks'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: number
}

export interface DesktopPetChatOptions {
  /** 是否已登录（非访客） */
  isLoggedIn?: () => boolean
  /** 访客发消息时引导登录 */
  onLoginRequired?: () => void
}

const history = ref<ChatMessage[]>([])
const input = ref('')
const streamingText = ref('')
const isStreaming = ref(false)
const historyOpen = ref(false)
const error = ref('')
const loginRequired = ref(false)

let abortCtrl: AbortController | null = null

const displayText = computed(() => {
  if (isStreaming.value) return streamingText.value
  const last = [...history.value].reverse().find((m) => m.role === 'assistant')
  return last?.content ?? '你好呀，我是kohaku'
})

const bubbleTier = computed(() => bubbleTierFromText(displayText.value))

const hasHistory = computed(() => history.value.length > 0)

function toggleHistory() {
  historyOpen.value = !historyOpen.value
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
  history.value.push({
    id: genId('u'),
    role: 'user',
    content: text,
    createdAt: Date.now(),
  })
  input.value = ''

  const turns: ChatTurn[] = history.value.map((m) => ({
    role: m.role,
    content: m.content,
  }))

  isStreaming.value = true
  streamingText.value = ''
  abortCtrl = new AbortController()

  try {
    await streamAgentChat(
      turns,
      (piece) => {
        streamingText.value += piece
      },
      abortCtrl.signal,
    )

    const reply = streamingText.value.trim() || '（没有收到回复）'
    history.value.push({
      id: genId('a'),
      role: 'assistant',
      content: reply,
      createdAt: Date.now(),
    })
    if (/已添加：/.test(reply)) {
      notifyMusicTracksChanged()
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
    history.value.push({
      id: genId('a'),
      role: 'assistant',
      content: partial,
      createdAt: Date.now(),
    })
  }
  isStreaming.value = false
  streamingText.value = ''
}

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
  }
}
