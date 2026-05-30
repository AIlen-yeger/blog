import { computed, reactive, watch } from 'vue'
import type { AgentReplyContentKind, AgentReplySettings } from '@/types/agentReply'

const STORAGE_KEY = 'blog:agent-reply-settings'

function readEnvBool(name: string, defaultVal: boolean): boolean {
  const raw = import.meta.env[name]
  if (raw === undefined || raw === '') return defaultVal
  return raw === 'true' || raw === '1'
}

function defaultSettings(): AgentReplySettings {
  const maxRaw = Number(import.meta.env.VITE_AGENT_REPLY_PREVIEW_MAX ?? 120)
  return {
    noteEnabled: readEnvBool('VITE_AGENT_REPLY_NOTE_ENABLED', true),
    lifeEnabled: readEnvBool('VITE_AGENT_REPLY_LIFE_ENABLED', true),
    previewMaxChars: Number.isFinite(maxRaw) && maxRaw >= 20 ? maxRaw : 120,
  }
}

function loadSettings(): AgentReplySettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultSettings()
    const parsed = JSON.parse(raw) as Partial<AgentReplySettings>
    const base = defaultSettings()
    return {
      noteEnabled: typeof parsed.noteEnabled === 'boolean' ? parsed.noteEnabled : base.noteEnabled,
      lifeEnabled: typeof parsed.lifeEnabled === 'boolean' ? parsed.lifeEnabled : base.lifeEnabled,
      previewMaxChars:
        typeof parsed.previewMaxChars === 'number' && parsed.previewMaxChars >= 20
          ? parsed.previewMaxChars
          : base.previewMaxChars,
    }
  } catch {
    return defaultSettings()
  }
}

const state = reactive<AgentReplySettings>(loadSettings())

watch(
  state,
  (v) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(v))
  },
  { deep: true },
)

export function useAgentReplySettings() {
  const noteEnabled = computed(() => state.noteEnabled)
  const lifeEnabled = computed(() => state.lifeEnabled)
  const previewMaxChars = computed(() => state.previewMaxChars)

  function isEnabledFor(kind: AgentReplyContentKind): boolean {
    return kind === 'note' ? state.noteEnabled : state.lifeEnabled
  }

  function shouldShowReply(kind: AgentReplyContentKind, reply?: string | null): boolean {
    if (!isEnabledFor(kind)) return false
    return Boolean((reply || '').trim())
  }

  function setNoteEnabled(v: boolean) {
    state.noteEnabled = v
  }

  function setLifeEnabled(v: boolean) {
    state.lifeEnabled = v
  }

  function setPreviewMaxChars(v: number) {
    state.previewMaxChars = Math.min(500, Math.max(20, Math.round(v)))
  }

  function resetToEnvDefaults() {
    Object.assign(state, defaultSettings())
  }

  return {
    settings: state,
    noteEnabled,
    lifeEnabled,
    previewMaxChars,
    isEnabledFor,
    shouldShowReply,
    setNoteEnabled,
    setLifeEnabled,
    setPreviewMaxChars,
    resetToEnvDefaults,
  }
}
