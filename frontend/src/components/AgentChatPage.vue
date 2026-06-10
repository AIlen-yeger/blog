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

const displayMessages = computed(() => {
  const list = [...messages.value]
  if (isStreaming.value && streamingText.value) {
    list.push({
      id: '__streaming__',
      role: 'assistant' as const,
      content: streamingText.value,
      createdAt: Date.now(),
    })
  }
  return list
})

function scrollToBottom() {
  const el = messagesRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

watch([displayMessages, isStreaming], () => {
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
          <div v-if="!displayMessages.length" class="agent-welcome">
            <p class="agent-welcome__title">你好，我是蕾西亚</p>
            <p class="agent-welcome__hint">
              可以聊博客、加歌、查笔记，也可以上传图片、PDF 或 Markdown。
              多任务可开启「分步执行」，或输入 <code>/plan 发布笔记并加歌</code>。
            </p>
          </div>

          <article
            v-for="msg in displayMessages"
            :key="msg.id"
            class="agent-msg"
            :class="msg.role"
          >
          <div class="agent-msg__avatar" aria-hidden="true">
            {{ msg.role === 'user' ? '你' : '蕾' }}
          </div>
          <div class="agent-msg__body">
            <p class="agent-msg__role">{{ msg.role === 'user' ? '你' : '蕾西亚' }}</p>
            <div v-if="msg.attachments?.length" class="agent-msg__attachments">
              <template v-for="att in msg.attachments" :key="att.id">
                <img
                  v-if="att.type === 'image' && att.url"
                  :src="resolveMediaUrl(att.url)"
                  :alt="att.name"
                  class="agent-msg__img"
                />
                <span
                  v-else
                  class="agent-msg__file-tag"
                >📄 {{ att.name }}</span>
              </template>
            </div>
            <pre class="agent-msg__text">{{ msg.content }}</pre>
          </div>
        </article>
        </template>

        <AgentPlanSteps v-if="planSteps.length" :steps="planSteps" />
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
        <button
          type="button"
          class="agent-composer__attach"
          title="上传文件"
          :disabled="isStreaming"
          @click="onPickFiles"
        >
          📎
        </button>
        <button
          type="button"
          class="agent-composer__attach"
          title="上传文件夹（含 .md 与 images 子目录，自动匹配本地图片路径）"
          :disabled="isStreaming"
          @click="onPickFolder"
        >
          📁
        </button>
        <button
          type="button"
          class="agent-composer__plan"
          :class="{ 'is-active': planModeEnabled }"
          title="分步执行：先列出步骤再逐项完成"
          :disabled="isStreaming"
          @click="togglePlanMode"
        >
          分步
        </button>
        <textarea
          ref="inputRef"
          v-model="input"
          class="agent-composer__input"
          rows="1"
          placeholder="输入消息，Shift+Enter 换行…"
          :disabled="isStreaming"
          @keydown="onKeydown"
          @input="resizeInput"
        />
        <button
          v-if="!isStreaming"
          type="button"
          class="agent-composer__send"
          :disabled="!input.trim() && !pendingAttachments.length"
          @click="onSubmit"
        >
          发送
        </button>
        <button
          v-else
          type="button"
          class="agent-composer__send agent-composer__send--stop"
          @click="stopStreaming"
        >
          停止
        </button>
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
  padding: 1.25rem clamp(1.5rem, 5vw, 4rem) 0.75rem;
  scroll-behavior: smooth;
  overscroll-behavior: contain;
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
  max-width: min(46%, 560px);
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
  background: rgba(60, 120, 200, 0.18);
  border-color: rgba(140, 190, 255, 0.2);
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
  align-items: flex-end;
  gap: 0.45rem;
  padding: 0.75rem 1rem 1rem;
  border-top: 1px solid rgba(140, 190, 255, 0.12);
  background: rgba(14, 24, 42, 0.85);
}

.agent-composer__file-input {
  display: none;
}

.agent-composer__attach {
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  border: 1px solid rgba(140, 190, 255, 0.22);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  font-size: 1rem;
  cursor: pointer;
}

.agent-composer__attach:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.agent-composer__plan {
  flex-shrink: 0;
  height: 2.25rem;
  padding: 0 0.55rem;
  border: 1px solid rgba(140, 190, 255, 0.22);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  font-size: 0.78rem;
  color: var(--agent-muted);
  cursor: pointer;
}

.agent-composer__plan.is-active {
  border-color: rgba(142, 200, 255, 0.55);
  background: rgba(90, 159, 212, 0.2);
  color: var(--agent-accent);
}

.agent-composer__plan:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.agent-composer__input {
  flex: 1;
  min-width: 0;
  min-height: 2.25rem;
  max-height: 160px;
  padding: 0.55rem 0.75rem;
  border: 1px solid rgba(140, 190, 255, 0.22);
  border-radius: 12px;
  background: rgba(8, 16, 32, 0.5);
  color: var(--agent-text);
  font-family: inherit;
  font-size: 0.88rem;
  line-height: 1.45;
  resize: none;
  outline: none;
}

.agent-composer__input:focus {
  border-color: rgba(140, 200, 255, 0.45);
  box-shadow: 0 0 0 2px rgba(100, 170, 255, 0.12);
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

.agent-composer__send {
  flex-shrink: 0;
  min-width: 3.5rem;
  height: 2.25rem;
  padding: 0 0.85rem;
  border: 1px solid rgba(140, 200, 255, 0.35);
  border-radius: 10px;
  background: linear-gradient(165deg, rgba(100, 170, 240, 0.95), rgba(60, 120, 200, 0.92));
  color: #fff;
  font-size: 0.82rem;
  cursor: pointer;
}

.agent-composer__send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.agent-composer__send--stop {
  background: linear-gradient(165deg, rgba(230, 120, 120, 0.95), rgba(190, 70, 70, 0.92));
  border-color: rgba(255, 160, 160, 0.35);
}

.agent-sidebar-backdrop {
  display: none;
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
}
</style>
