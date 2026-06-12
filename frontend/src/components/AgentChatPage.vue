<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import AgentPlanSteps from '@/components/AgentPlanSteps.vue'
import { useAgentChat } from '@/composables/useAgentChat'
import { exitAgentChat } from '@/utils/agentRoute'
import { resolveMediaUrl } from '@/utils/mediaUrl'
import { renderNoteMarkdown } from '@/utils/renderMarkdown'

const { loggedIn: loggedInProp } = defineProps<{
  loggedIn?: boolean
}>()

const emit = defineEmits<{
  'request-login': []
}>()

const isLoggedIn = () => loggedInProp === true

const fileInputRef = ref<HTMLInputElement | null>(null)
const folderInputRef = ref<HTMLInputElement | null>(null)
const messagesRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)
const previewTitle = ref('')
const previewTopic = ref('随笔')

const {
  sessions,
  activeSessionId,
  messages,
  input,
  streamingText,
  isStreaming,
  error,
  loginRequired,
  pendingAttachments,
  pendingActionPreview,
  publishNoteLoading,
  planSteps,
  planModeEnabled,
  webSearchEnabled,
  searchStatus,
  sidebarOpen,
  selectSession,
  startNewSession,
  removeSession,
  sendMessage,
  stopStreaming,
  addFiles,
  addFolder,
  removeAttachment,
  dismissActionPreview,
  confirmPublishNote,
  togglePlanMode,
  toggleWebSearch,
  clearError,
  toggleSidebar,
  refreshSessions,
  sessionsLoading,
  messagesLoading,
} = useAgentChat()

const previewBodyHtml = computed(() => {
  const text = pendingActionPreview.value?.data?.contentPreview ?? ''
  return renderNoteMarkdown(text)
})

watch(
  pendingActionPreview,
  (row) => {
    if (row?.action === 'publish_note') {
      previewTitle.value = row.data.title
      previewTopic.value = row.data.topicTitle || '随笔'
    }
  },
  { immediate: true },
)

function onConfirmPublish() {
  void confirmPublishNote({
    title: previewTitle.value,
    topicTitle: previewTopic.value,
  })
}

const showPlanOnLastReply = computed(
  () => planSteps.value.length > 0 && !isStreaming.value && messages.value.length > 0,
)

const lastMessageIndex = computed(() => messages.value.length - 1)

function scrollToBottom() {
  const el = messagesRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

watch([messages, isStreaming, streamingText, planSteps], () => {
  void nextTick(scrollToBottom)
})

function onBack() {
  exitAgentChat()
}

function onSubmit() {
  void sendMessage({
    isLoggedIn,
    onLoginRequired: () => emit('request-login'),
  })
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    onSubmit()
  }
}

function onPickFiles() {
  fileInputRef.value?.click()
}

function onPickFolder() {
  folderInputRef.value?.click()
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) {
    void addFiles(input.files)
    input.value = ''
  }
}

function onFolderChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) {
    void addFolder(input.files)
    input.value = ''
  }
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer?.files?.length) {
    void addFiles(e.dataTransfer.files)
  }
}

function formatTime(ts: number) {
  const d = new Date(ts)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function resizeInput() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`
}

watch(input, () => void nextTick(resizeInput))

onMounted(() => {
  void refreshSessions().then(() => {
    void nextTick(() => {
      scrollToBottom()
      resizeInput()
    })
  })
})
</script>

<template>
  <div class="agent-page" @dragover.prevent @drop="onDrop" @wheel.stop>
    <aside class="agent-sidebar" :class="{ 'is-collapsed': !sidebarOpen }">
      <div class="agent-sidebar__head">
        <button
          type="button"
          class="agent-sidebar__new"
          :disabled="sessionsLoading"
          @click="startNewSession"
        >
          <span aria-hidden="true">＋</span>
          新对话
        </button>
      </div>
      <div class="agent-sidebar__list">
        <p v-if="sessionsLoading" class="agent-sidebar__empty">加载中…</p>
        <button
          v-for="session in sessions"
          :key="session.sessionId"
          type="button"
          class="agent-sidebar__item"
          :class="{ active: session.sessionId === activeSessionId }"
          @click="selectSession(session.sessionId)"
        >
          <span class="agent-sidebar__item-title">{{ session.title }}</span>
          <span class="agent-sidebar__item-time">{{ formatTime(session.updatedAt) }}</span>
          <button
            type="button"
            class="agent-sidebar__item-del"
            title="删除对话"
            @click.stop="removeSession(session.sessionId)"
          >
            ×
          </button>
        </button>
        <p v-if="!sessionsLoading && !sessions.length" class="agent-sidebar__empty">
          暂无对话，点击上方开始
        </p>
      </div>
    </aside>

    <div class="agent-main">
      <header class="agent-header">
        <button type="button" class="agent-header__back" title="返回" @click="onBack">
          ←
        </button>
        <button
          type="button"
          class="agent-header__menu"
          title="对话列表"
          @click="toggleSidebar"
        >
          ☰
        </button>
        <div class="agent-header__title">
          <span class="agent-header__name">蕾西亚</span>
          <span class="agent-header__sub">全屏对话 · 支持附件</span>
        </div>
        <button
          type="button"
          class="agent-header__new"
          :disabled="sessionsLoading"
          @click="startNewSession"
        >
          新对话
        </button>
      </header>

      <div ref="messagesRef" class="agent-messages">
        <p v-if="messagesLoading" class="agent-messages__loading">加载消息中…</p>
        <template v-else>
          <div v-if="!messages.length && !isStreaming" class="agent-welcome">
            <p class="agent-welcome__title">你好，我是蕾西亚</p>
            <p class="agent-welcome__hint">
              可以聊博客、加歌、查笔记，也可以上传附件。
              开启「深度思考」会分步规划任务；「智能搜索」会先联网检索再回答。
            </p>
          </div>

          <article
            v-for="(msg, index) in messages"
            :key="msg.id"
            class="agent-msg"
            :class="msg.role"
          >
            <div class="agent-msg__avatar" aria-hidden="true">
              {{ msg.role === 'user' ? '你' : '蕾' }}
            </div>
            <div class="agent-msg__body">
              <p class="agent-msg__role">{{ msg.role === 'user' ? '你' : '蕾西亚' }}</p>
              <AgentPlanSteps
                v-if="
                  showPlanOnLastReply &&
                  msg.role === 'assistant' &&
                  index === lastMessageIndex
                "
                :steps="planSteps"
                embedded
              />
              <div v-if="msg.attachments?.length" class="agent-msg__attachments">
                <template v-for="att in msg.attachments" :key="att.id">
                  <img
                    v-if="att.type === 'image' && att.url"
                    :src="resolveMediaUrl(att.url)"
                    :alt="att.name"
                    class="agent-msg__img"
                  />
                  <span v-else class="agent-msg__file-tag">📄 {{ att.name }}</span>
                </template>
              </div>
              <pre class="agent-msg__text">{{ msg.content }}</pre>
            </div>
          </article>

          <div v-if="isStreaming" class="agent-streaming-turn">
            <p v-if="searchStatus === 'searching'" class="agent-search-hint" aria-live="polite">
              正在联网搜索…
            </p>
            <AgentPlanSteps v-if="planSteps.length" :steps="planSteps" embedded />
            <article class="agent-msg assistant is-streaming">
              <div class="agent-msg__avatar" aria-hidden="true">蕾</div>
              <div class="agent-msg__body">
                <p class="agent-msg__role">蕾西亚</p>
                <p
                  v-if="!streamingText.trim() && planModeEnabled && !planSteps.length"
                  class="agent-msg__pending"
                  aria-live="polite"
                >
                  深度思考中<span class="agent-msg__dots" aria-hidden="true">…</span>
                </p>
                <p
                  v-else-if="!streamingText.trim()"
                  class="agent-msg__pending"
                  aria-live="polite"
                >
                  蕾西亚正在回复<span class="agent-msg__dots" aria-hidden="true">…</span>
                </p>
                <pre v-else class="agent-msg__text">{{ streamingText }}</pre>
              </div>
            </article>
          </div>
        </template>
      </div>

      <div
        v-if="pendingActionPreview?.action === 'publish_note'"
        class="agent-preview"
      >
        <div class="agent-preview__card">
          <p class="agent-preview__title">确认发布笔记</p>
          <p class="agent-preview__excerpt">{{ pendingActionPreview.data.excerpt }}</p>
          <label class="agent-preview__field">
            <span>标题</span>
            <input v-model="previewTitle" type="text" class="agent-preview__input" />
          </label>
          <label class="agent-preview__field">
            <span>专题</span>
            <input v-model="previewTopic" type="text" class="agent-preview__input" />
          </label>
          <div
            class="agent-preview__body md-content"
            v-html="previewBodyHtml"
          />
          <p
            v-if="pendingActionPreview.data.attachmentNames"
            class="agent-preview__files"
          >
            附件：{{ pendingActionPreview.data.attachmentNames }}
          </p>
          <div class="agent-preview__actions">
            <button
              type="button"
              class="agent-preview__cancel"
              :disabled="publishNoteLoading"
              @click="dismissActionPreview"
            >
              取消
            </button>
            <button
              type="button"
              class="agent-preview__confirm"
              :disabled="publishNoteLoading || !previewTitle.trim()"
              @click="onConfirmPublish"
            >
              {{ publishNoteLoading ? '发布中…' : '确认发布' }}
            </button>
          </div>
        </div>
      </div>

      <p v-if="error" class="agent-error">
        {{ error }}
        <button
          v-if="loginRequired"
          type="button"
          class="agent-error__login"
          @click="emit('request-login')"
        >
          去登录
        </button>
        <button type="button" class="agent-error__dismiss" @click="clearError">×</button>
      </p>

      <div v-if="pendingAttachments.length" class="agent-pending">
        <div
          v-for="att in pendingAttachments"
          :key="att.id"
          class="agent-pending__chip"
        >
          <img
            v-if="att.preview"
            :src="att.preview"
            :alt="att.name"
            class="agent-pending__thumb"
          />
          <span v-else class="agent-pending__name">📄 {{ att.name }}</span>
          <button type="button" class="agent-pending__remove" @click="removeAttachment(att.id)">
            ×
          </button>
        </div>
      </div>

      <footer class="agent-composer">
        <input
          ref="fileInputRef"
          type="file"
          class="agent-composer__file-input"
          accept="image/*,.pdf,.doc,.docx,.txt,.md,.markdown,.json,.csv,.log,.xml,.yaml,.yml,.js,.ts,.py,.java,.html,.css"
          multiple
          @change="onFileChange"
        />
        <input
          ref="folderInputRef"
          type="file"
          class="agent-composer__file-input"
          webkitdirectory
          directory
          multiple
          @change="onFolderChange"
        />
        <div class="agent-composer__box">
          <textarea
            ref="inputRef"
            v-model="input"
            class="agent-composer__input"
            rows="1"
            placeholder="给蕾西亚发送消息"
            :disabled="isStreaming"
            @keydown="onKeydown"
            @input="resizeInput"
          />
          <div class="agent-composer__toolbar">
            <div class="agent-composer__modes">
              <button
                type="button"
                class="agent-mode-pill"
                :class="{ 'is-active': planModeEnabled }"
                title="深度思考：分步规划并逐项执行复杂任务"
                :disabled="isStreaming"
                @click="togglePlanMode"
              >
                <span class="agent-mode-pill__icon" aria-hidden="true">∞</span>
                深度思考
              </button>
              <button
                type="button"
                class="agent-mode-pill"
                :class="{ 'is-active': webSearchEnabled }"
                title="智能搜索：先联网检索再回答"
                :disabled="isStreaming"
                @click="toggleWebSearch"
              >
                <span class="agent-mode-pill__icon agent-mode-pill__icon--globe" aria-hidden="true">⌁</span>
                智能搜索
              </button>
            </div>
            <div class="agent-composer__actions">
              <button
                type="button"
                class="agent-composer__icon-btn"
                title="上传文件"
                :disabled="isStreaming"
                @click="onPickFiles"
              >
                📎
              </button>
              <button
                type="button"
                class="agent-composer__icon-btn"
                title="上传文件夹"
                :disabled="isStreaming"
                @click="onPickFolder"
              >
                📁
              </button>
              <button
                v-if="!isStreaming"
                type="button"
                class="agent-composer__send"
                :disabled="!input.trim() && !pendingAttachments.length"
                title="发送"
                @click="onSubmit"
              >
                ↑
              </button>
              <button
                v-else
                type="button"
                class="agent-composer__send agent-composer__send--stop"
                title="停止"
                @click="stopStreaming"
              >
                ■
              </button>
            </div>
          </div>
        </div>
      </footer>
    </div>

    <button
      v-if="sidebarOpen"
      type="button"
      class="agent-sidebar-backdrop"
      aria-label="关闭侧边栏"
      @click="toggleSidebar"
    />
  </div>
</template>

<style scoped>
.agent-page {
  --agent-bg: rgba(18, 30, 52, 0.96);
  --agent-panel: rgba(24, 42, 72, 0.88);
  --agent-border: rgba(140, 190, 255, 0.22);
  --agent-accent: #8ec8ff;
  --agent-text: rgba(232, 244, 255, 0.94);
  --agent-muted: rgba(186, 210, 240, 0.72);
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  background: var(--color-bg-dark);
  color: var(--agent-text);
}

.agent-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--agent-panel);
  border-right: 1px solid var(--agent-border);
  backdrop-filter: blur(16px);
  transition: transform 0.28s ease;
}

.agent-sidebar__head {
  padding: 0.85rem;
  border-bottom: 1px solid rgba(140, 190, 255, 0.12);
}

.agent-sidebar__new {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  width: 100%;
  padding: 0.55rem 0.75rem;
  border: 1px dashed rgba(140, 190, 255, 0.35);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--agent-accent);
  font-size: 0.88rem;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.agent-sidebar__new:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(140, 190, 255, 0.5);
}

.agent-sidebar__list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.agent-sidebar__item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  margin-bottom: 0.35rem;
  padding: 0.55rem 0.65rem;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: var(--agent-text);
  text-align: left;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.agent-sidebar__item:hover,
.agent-sidebar__item.active {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(140, 190, 255, 0.2);
}

.agent-sidebar__item-title {
  font-size: 0.82rem;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  padding-right: 1.2rem;
}

.agent-sidebar__item-time {
  margin-top: 0.15rem;
  font-size: 0.68rem;
  color: var(--agent-muted);
}

.agent-sidebar__item-del {
  position: absolute;
  top: 0.35rem;
  right: 0.35rem;
  width: 1.2rem;
  height: 1.2rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(160, 190, 220, 0.55);
  font-size: 0.9rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s ease, color 0.2s ease;
}

.agent-sidebar__item:hover .agent-sidebar__item-del {
  opacity: 1;
}

.agent-sidebar__item-del:hover {
  color: #f0a0a0;
}

.agent-sidebar__empty {
  margin: 1rem 0.5rem;
  font-size: 0.78rem;
  color: var(--agent-muted);
  text-align: center;
}

.agent-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--agent-bg);
}

.agent-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 1rem;
  border-bottom: 1px solid rgba(140, 190, 255, 0.14);
  background: rgba(16, 28, 48, 0.72);
  backdrop-filter: blur(12px);
}

.agent-header__back,
.agent-header__menu {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border: 1px solid rgba(140, 190, 255, 0.2);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: var(--agent-accent);
  font-size: 0.95rem;
  cursor: pointer;
}

.agent-header__menu {
  display: none;
}

.agent-header__title {
  flex: 1;
  min-width: 0;
}

.agent-header__name {
  display: block;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--agent-accent);
}

.agent-header__sub {
  display: block;
  margin-top: 0.1rem;
  font-size: 0.68rem;
  color: var(--agent-muted);
}

.agent-header__new {
  flex-shrink: 0;
  padding: 0.35rem 0.7rem;
  border: 1px solid rgba(140, 190, 255, 0.28);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--agent-accent);
  font-size: 0.78rem;
  cursor: pointer;
}

.agent-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem clamp(1rem, 4vw, 2rem) 0.75rem;
  scroll-behavior: smooth;
  overscroll-behavior: contain;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.agent-messages > * {
  width: 100%;
  max-width: 820px;
}

.agent-messages__loading {
  margin: 2rem auto;
  text-align: center;
  font-size: 0.85rem;
  color: var(--agent-muted);
}

.agent-welcome {
  max-width: 36rem;
  margin: 2rem auto;
  padding: 1.5rem;
  text-align: center;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(140, 190, 255, 0.14);
}

.agent-welcome__title {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--agent-accent);
}

.agent-welcome__hint {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.55;
  color: var(--agent-muted);
}

.agent-msg {
  display: flex;
  gap: 0.65rem;
  width: 100%;
  max-width: 100%;
  margin-bottom: 1.25rem;
}

.agent-msg.assistant {
  margin-right: auto;
  margin-left: 0;
}

.agent-msg.user {
  flex-direction: row-reverse;
  margin-left: auto;
  margin-right: 0;
  max-width: min(78%, 640px);
}

.agent-msg__avatar {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  font-size: 0.72rem;
  font-weight: 700;
  background: rgba(100, 170, 240, 0.2);
  color: var(--agent-accent);
}

.agent-msg.user .agent-msg__avatar {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(220, 235, 255, 0.9);
}

.agent-msg__body {
  flex: 1;
  min-width: 0;
  padding: 0.65rem 0.85rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(140, 190, 255, 0.12);
}

.agent-msg.user .agent-msg__body {
  background: linear-gradient(135deg, rgba(56, 120, 210, 0.92), rgba(42, 98, 180, 0.88));
  border-color: rgba(120, 180, 255, 0.35);
  color: rgba(245, 250, 255, 0.98);
}

.agent-msg.user .agent-msg__role {
  color: rgba(220, 235, 255, 0.75);
}

.agent-msg__role {
  margin: 0 0 0.35rem;
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--agent-muted);
}

.agent-msg__text {
  margin: 0;
  font-family: inherit;
  font-size: 0.88rem;
  line-height: 1.58;
  white-space: pre-wrap;
  word-break: break-word;
}

.agent-streaming-turn {
  width: 100%;
  max-width: 100%;
  margin-right: auto;
  margin-left: 0;
  margin-bottom: 1.25rem;
}

.agent-search-hint {
  margin: 0 0 0.65rem 2.65rem;
  font-size: 0.78rem;
  color: rgba(160, 210, 255, 0.85);
  font-style: italic;
}

.agent-streaming-turn .agent-msg {
  margin-bottom: 0;
  max-width: none;
  width: 100%;
}

.agent-msg.is-streaming .agent-msg__body {
  border-color: rgba(140, 190, 255, 0.22);
}

.agent-msg__pending {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.58;
  color: rgba(186, 210, 240, 0.82);
  font-style: italic;
}

.agent-msg__dots {
  display: inline-block;
  width: 1.2em;
  text-align: left;
  animation: agent-typing-dots 1.2s steps(4, end) infinite;
}

@keyframes agent-typing-dots {
  0% {
    clip-path: inset(0 100% 0 0);
  }
  100% {
    clip-path: inset(0 0 0 0);
  }
}

.agent-msg__attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-bottom: 0.45rem;
}

.agent-msg__img {
  max-width: 200px;
  max-height: 140px;
  border-radius: 8px;
  object-fit: cover;
  border: 1px solid rgba(140, 190, 255, 0.2);
}

.agent-msg__file-tag {
  display: inline-block;
  padding: 0.2rem 0.45rem;
  border-radius: 6px;
  background: rgba(8, 16, 32, 0.4);
  font-size: 0.72rem;
  color: var(--agent-muted);
}

.agent-error {
  margin: 0 1rem 0.35rem;
  padding: 0.45rem 0.65rem;
  border-radius: 8px;
  background: rgba(220, 80, 70, 0.14);
  border: 1px solid rgba(248, 130, 120, 0.28);
  color: #fecdd3;
  font-size: 0.78rem;
}

.agent-error__login,
.agent-error__dismiss {
  margin-left: 0.35rem;
  border: none;
  background: transparent;
  color: var(--agent-accent);
  cursor: pointer;
}

.agent-pending {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  padding: 0 1rem 0.5rem;
}

.agent-pending__chip {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.45rem;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(140, 190, 255, 0.2);
}

.agent-pending__thumb {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  object-fit: cover;
}

.agent-pending__name {
  font-size: 0.75rem;
  color: var(--agent-muted);
}

.agent-pending__remove {
  border: none;
  background: transparent;
  color: rgba(160, 190, 220, 0.7);
  cursor: pointer;
  font-size: 0.9rem;
}

.agent-composer {
  display: flex;
  justify-content: center;
  padding: 0.75rem clamp(1rem, 4vw, 2rem) 1.25rem;
  border-top: 1px solid rgba(140, 190, 255, 0.12);
  background: rgba(14, 24, 42, 0.85);
}

.agent-composer__box {
  width: 100%;
  max-width: 820px;
  border: 1px solid rgba(140, 190, 255, 0.22);
  border-radius: 16px;
  background: rgba(8, 16, 32, 0.55);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.18);
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.agent-composer__box:focus-within {
  border-color: rgba(140, 200, 255, 0.45);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.18), 0 0 0 2px rgba(100, 170, 255, 0.12);
}

.agent-composer__file-input {
  display: none;
}

.agent-composer__input {
  display: block;
  width: 100%;
  min-height: 3rem;
  max-height: 160px;
  padding: 0.85rem 1rem 0.35rem;
  border: none;
  background: transparent;
  color: var(--agent-text);
  font-family: inherit;
  font-size: 0.92rem;
  line-height: 1.5;
  resize: none;
  outline: none;
}

.agent-composer__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.45rem 0.55rem 0.55rem;
}

.agent-composer__modes {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  min-width: 0;
}

.agent-mode-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  height: 2rem;
  padding: 0 0.65rem;
  border: 1px solid rgba(140, 190, 255, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--agent-muted);
  font-size: 0.78rem;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.agent-mode-pill__icon {
  font-size: 0.85rem;
  line-height: 1;
  opacity: 0.85;
}

.agent-mode-pill__icon--globe {
  font-size: 0.95rem;
}

.agent-mode-pill.is-active {
  border-color: rgba(142, 200, 255, 0.55);
  background: rgba(90, 159, 212, 0.18);
  color: var(--agent-accent);
}

.agent-mode-pill:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.agent-composer__actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
}

.agent-composer__icon-btn {
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 10px;
  background: transparent;
  font-size: 1rem;
  cursor: pointer;
  opacity: 0.85;
}

.agent-composer__icon-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.06);
}

.agent-composer__icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.agent-composer__send {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: 1px solid rgba(140, 200, 255, 0.35);
  border-radius: 999px;
  background: linear-gradient(165deg, rgba(100, 170, 240, 0.95), rgba(60, 120, 200, 0.92));
  color: #fff;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}

.agent-composer__send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.agent-composer__send--stop {
  background: linear-gradient(165deg, rgba(230, 120, 120, 0.95), rgba(190, 70, 70, 0.92));
  border-color: rgba(255, 160, 160, 0.35);
  font-size: 0.72rem;
}

.agent-preview {
  padding: 0 1rem 0.5rem;
}

.agent-preview__card {
  max-width: 720px;
  margin: 0 auto;
  padding: 1rem 1.1rem;
  border: 1px solid rgba(140, 190, 255, 0.28);
  border-radius: 14px;
  background: rgba(20, 36, 64, 0.92);
}

.agent-preview__title {
  margin: 0 0 0.35rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--agent-accent);
}

.agent-preview__excerpt {
  margin: 0 0 0.75rem;
  font-size: 0.82rem;
  color: var(--agent-muted);
}

.agent-preview__field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.6rem;
  font-size: 0.78rem;
  color: var(--agent-muted);
}

.agent-preview__input {
  padding: 0.45rem 0.6rem;
  border: 1px solid rgba(140, 190, 255, 0.22);
  border-radius: 8px;
  background: rgba(8, 16, 32, 0.55);
  color: var(--agent-text);
  font-size: 0.88rem;
}

.agent-preview__body {
  margin: 0.5rem 0;
  max-height: 180px;
  overflow: auto;
  padding: 0.65rem 0.75rem;
  border-radius: 8px;
  background: rgba(8, 16, 32, 0.45);
  font-size: 0.8rem;
  line-height: 1.55;
  word-break: break-word;
}

.agent-preview__body :deep(p) {
  margin: 0 0 0.5rem;
}

.agent-preview__body :deep(h1),
.agent-preview__body :deep(h2),
.agent-preview__body :deep(h3) {
  margin: 0.35rem 0 0.4rem;
  font-size: inherit;
  font-weight: 700;
}

.agent-preview__body :deep(strong) {
  font-weight: 700;
  color: var(--agent-text);
}

.agent-preview__body :deep(code) {
  padding: 0.1em 0.35em;
  border-radius: 4px;
  background: rgba(140, 190, 255, 0.12);
  font-size: 0.92em;
}

.agent-preview__body :deep(.md-figure) {
  margin: 0.5rem 0;
}

.agent-preview__body :deep(.md-figure img),
.agent-preview__body :deep(.md-inline-img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
}

.agent-preview__files {
  margin: 0.35rem 0 0;
  font-size: 0.78rem;
  color: var(--agent-muted);
}

.agent-preview__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.agent-preview__cancel,
.agent-preview__confirm {
  padding: 0.45rem 0.9rem;
  border-radius: 8px;
  font-size: 0.85rem;
  cursor: pointer;
}

.agent-preview__cancel {
  border: 1px solid rgba(140, 190, 255, 0.22);
  background: transparent;
  color: var(--agent-muted);
}

.agent-preview__confirm {
  border: none;
  background: linear-gradient(135deg, #5a9fd4, #3d7fb8);
  color: #fff;
}

.agent-preview__confirm:disabled,
.agent-preview__cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 767px) {
  .agent-sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 2;
    transform: translateX(0);
  }

  .agent-sidebar.is-collapsed {
    transform: translateX(-100%);
  }

  .agent-sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 1;
    border: none;
    background: rgba(0, 0, 0, 0.45);
    cursor: pointer;
  }

  .agent-header__menu {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .agent-header__new {
    display: none;
  }

  .agent-messages {
    padding-left: 0.75rem;
    padding-right: 0.75rem;
  }

  .agent-composer {
    padding-left: 0.75rem;
    padding-right: 0.75rem;
  }

  .agent-mode-pill {
    font-size: 0.72rem;
    padding: 0 0.5rem;
  }
}

.agent-sidebar-backdrop {
  display: none;
}
</style>
