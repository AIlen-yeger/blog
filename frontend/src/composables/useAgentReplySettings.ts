import { computed, reactive, watch } from 'vue'
import type { AgentReplyContentKind, AgentReplySettings } from '@/types/agentReply'
import { fetchAgentReplySettings, updateAgentReplyOwnerOnly } from '@/api/blog'
import { useMockApi } from '@/api/http'
import { useGuestMode } from '@/composables/useGuestMode'
import { useSession } from '@/composables/useSession'

const STORAGE_KEY = 'blog:agent-reply-settings'

function readEnvBool(name: string, defaultVal: boolean): boolean {
  const raw = import.meta.env[name]
  if (raw === undefined || raw === '') return defaultVal
  return raw === 'true' || raw === '1'
}

export function envDefaultAgentReplySettings(): AgentReplySettings {
  const maxRaw = Number(import.meta.env.VITE_AGENT_REPLY_PREVIEW_MAX ?? 120)
  return {
    noteEnabled: readEnvBool('VITE_AGENT_REPLY_NOTE_ENABLED', true),
    lifeEnabled: readEnvBool('VITE_AGENT_REPLY_LIFE_ENABLED', true),
    previewMaxChars: Number.isFinite(maxRaw) && maxRaw >= 20 ? maxRaw : 120,
    ownerOnlyVisible: readEnvBool('VITE_AGENT_REPLY_OWNER_ONLY', false),
  }
}

function loadSettings(): AgentReplySettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return envDefaultAgentReplySettings()
    const parsed = JSON.parse(raw) as Partial<AgentReplySettings>
    const base = envDefaultAgentReplySettings()
    return {
      noteEnabled: typeof parsed.noteEnabled === 'boolean' ? parsed.noteEnabled : base.noteEnabled,
      lifeEnabled: typeof parsed.lifeEnabled === 'boolean' ? parsed.lifeEnabled : base.lifeEnabled,
      previewMaxChars:
        typeof parsed.previewMaxChars === 'number' && parsed.previewMaxChars >= 20
          ? parsed.previewMaxChars
          : base.previewMaxChars,
      ownerOnlyVisible:
        typeof parsed.ownerOnlyVisible === 'boolean'
          ? parsed.ownerOnlyVisible
          : base.ownerOnlyVisible,
    }
  } catch {
    return envDefaultAgentReplySettings()
  }
}

const state = reactive<AgentReplySettings>(loadSettings())
let serverSynced = false

watch(
  state,
  (v) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(v))
  },
  { deep: true },
)

function applyServerSettings(row: Partial<AgentReplySettings>) {
  if (typeof row.noteEnabled === 'boolean') state.noteEnabled = row.noteEnabled
  if (typeof row.lifeEnabled === 'boolean') state.lifeEnabled = row.lifeEnabled
  if (typeof row.previewMaxChars === 'number' && row.previewMaxChars >= 20) {
    state.previewMaxChars = row.previewMaxChars
  }
  if (typeof row.ownerOnlyVisible === 'boolean') state.ownerOnlyVisible = row.ownerOnlyVisible
}

/** 从服务端同步全局开关（含「仅个人可见」） */
export async function syncAgentReplySettingsFromServer(): Promise<void> {
  if (useMockApi()) return
  try {
    const row = await fetchAgentReplySettings()
    applyServerSettings(row)
    serverSynced = true
  } catch (e) {
    console.warn('[agent-reply] sync settings failed', e)
  }
}

export function useAgentReplySettings() {
  const { isAdmin } = useSession()
  const { guestMode } = useGuestMode()

  function isEnabledFor(kind: AgentReplyContentKind): boolean {
    return kind === 'note' ? state.noteEnabled : state.lifeEnabled
  }

  /** 当前访客是否允许看到蕾西亚回复区域（含撰写中提示） */
  function canViewAgentReply(kind: AgentReplyContentKind): boolean {
    if (!isEnabledFor(kind)) return false
    if (state.ownerOnlyVisible) {
      // 预览模式模拟访客视角，即使已登录管理员也不展示
      if (guestMode.value || !isAdmin.value) return false
    }
    return true
  }

  function shouldShowReply(kind: AgentReplyContentKind, reply?: string | null): boolean {
    if (!canViewAgentReply(kind)) return false
    return Boolean((reply || '').trim())
  }

  function isGenerating(status?: string | null, reply?: string | null): boolean {
    const st = (status || '').toLowerCase()
    return (st === 'pending' || st === 'running') && !(reply || '').trim()
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

  async function setOwnerOnlyVisible(v: boolean) {
    state.ownerOnlyVisible = v
    if (useMockApi() || !isAdmin.value) return
    try {
      const row = await updateAgentReplyOwnerOnly(v)
      applyServerSettings(row)
    } catch (e) {
      console.warn('[agent-reply] save owner-only failed', e)
      throw e
    }
  }

  function resetToEnvDefaults() {
    const base = envDefaultAgentReplySettings()
    state.noteEnabled = base.noteEnabled
    state.lifeEnabled = base.lifeEnabled
    state.previewMaxChars = base.previewMaxChars
    state.ownerOnlyVisible = base.ownerOnlyVisible
  }

  return {
    settings: state,
    noteEnabled: computed(() => state.noteEnabled),
    lifeEnabled: computed(() => state.lifeEnabled),
    previewMaxChars: computed(() => state.previewMaxChars),
    ownerOnlyVisible: computed(() => state.ownerOnlyVisible),
    serverSynced: computed(() => serverSynced),
    isEnabledFor,
    canViewAgentReply,
    shouldShowReply,
    isGenerating,
    setNoteEnabled,
    setLifeEnabled,
    setPreviewMaxChars,
    setOwnerOnlyVisible,
    resetToEnvDefaults,
    envDefaults: envDefaultAgentReplySettings,
    syncFromServer: syncAgentReplySettingsFromServer,
  }
}
