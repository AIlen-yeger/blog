<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ContentKind } from '@/types/views'
import { useContentViewTracking } from '@/composables/useContentView'
import ContentImageGallery from './ContentImageGallery.vue'
import AgentReplyBlock from './AgentReplyBlock.vue'
import { useAgentReplySettings } from '@/composables/useAgentReplySettings'
import { renderNoteMarkdown } from '@/utils/renderMarkdown'

export interface ReaderItem {
  id: string
  title: string
  tag: string
  date: string
  content: string
  images?: string[]
  viewCount?: number
  agentReply?: string | null
  agentReplyStatus?: string | null
}

const props = defineProps<{
  open: boolean
  kind: ContentKind
  item: ReaderItem | null
  editable?: boolean
}>()

const emit = defineEmits<{
  close: []
  edit: []
  'view-count': [count: number]
}>()

const trackOpen = ref(false)
const { shouldShowReply, isGenerating, canViewAgentReply } = useAgentReplySettings()

const showAgentReply = computed(() =>
  props.item ? shouldShowReply(props.kind, props.item.agentReply) : false,
)

const agentReplyGenerating = computed(() => {
  if (!props.item) return false
  return (
    canViewAgentReply(props.kind) &&
    isGenerating(props.item.agentReplyStatus, props.item.agentReply)
  )
})

const { viewCount } = useContentViewTracking(
  props.kind,
  () => props.item?.id ?? '',
  () => props.item?.viewCount,
  trackOpen,
)

watch(
  () => props.open,
  (v) => {
    trackOpen.value = v
  },
  { immediate: true },
)

watch(viewCount, (n) => emit('view-count', n))

const contentHtml = computed(() =>
  props.item ? renderNoteMarkdown(props.item.content) : '',
)
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open && item"
        class="backdrop"
        role="dialog"
        aria-modal="true"
        :aria-label="item.title"
        @click.self="emit('close')"
      >
        <article class="reader-panel">
          <header class="reader-head">
            <div class="head-main">
              <span class="tag">{{ item.tag }}</span>
              <h2>{{ item.title }}</h2>
              <p class="meta-line">
                <time :datetime="item.date">{{ item.date }}</time>
                <span class="dot">·</span>
                <span>{{ viewCount }} 次浏览</span>
              </p>
            </div>
            <div class="head-actions">
              <button
                v-if="editable"
                type="button"
                class="edit-btn"
                @click="emit('edit')"
              >
                编辑
              </button>
              <button type="button" class="close-btn" aria-label="关闭" @click="emit('close')">
                ×
              </button>
            </div>
          </header>
          <div class="reader-body">
            <div class="content md-content" v-html="contentHtml" />
            <p v-if="agentReplyGenerating" class="agent-reply-pending">蕾西亚正在写回复…</p>
            <AgentReplyBlock
              v-if="showAgentReply && item.agentReply"
              :kind="kind"
              mode="full"
              :reply="item.agentReply"
            />
            <ContentImageGallery v-if="item.images?.length" :images="item.images" />
          </div>
        </article>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(15, 25, 45, 0.55);
  backdrop-filter: blur(6px);
}
.reader-panel {
  width: min(92vw, 680px);
  max-height: min(88vh, 900px);
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}
.reader-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem 1.4rem 0.75rem;
  border-bottom: 1px solid rgba(59, 130, 246, 0.12);
}
.head-main {
  min-width: 0;
}
.tag {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-accent-dark);
}
h2 {
  margin: 0.35rem 0 0.25rem;
  font-size: 1.25rem;
  color: var(--color-text);
  line-height: 1.35;
}
.meta-line {
  margin: 0;
  font-size: 0.78rem;
  color: #9a9aad;
}
.dot {
  margin: 0 0.35rem;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-shrink: 0;
}
.edit-btn {
  padding: 0.35rem 0.75rem;
  border: 1px solid rgba(59, 130, 246, 0.35);
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.08);
  color: var(--color-accent-dark);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}
.edit-btn:hover {
  background: rgba(59, 130, 246, 0.16);
}
.close-btn {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.08);
  color: var(--color-text-muted);
  font-size: 1.35rem;
  line-height: 1;
  cursor: pointer;
}
.close-btn:hover {
  background: rgba(59, 130, 246, 0.16);
}
.reader-body {
  padding: 1rem 1.4rem 1.4rem;
  overflow-y: auto;
}
.content {
  font-size: 0.95rem;
  line-height: 1.8;
  color: var(--color-text);
  word-break: break-word;
}

.content :deep(p) {
  margin: 0 0 0.85rem;
}

.content :deep(h1),
.content :deep(h2),
.content :deep(h3) {
  margin: 1rem 0 0.5rem;
  line-height: 1.35;
  color: var(--color-text);
}

.content :deep(h1) {
  font-size: 1.15rem;
}

.content :deep(h2) {
  font-size: 1.05rem;
}

.content :deep(h3) {
  font-size: 1rem;
}

.content :deep(strong) {
  font-weight: 700;
}

.content :deep(code) {
  padding: 0.12em 0.35em;
  border-radius: 4px;
  background: rgba(59, 130, 246, 0.1);
  font-size: 0.9em;
}

.content :deep(pre.md-code) {
  margin: 0.75rem 0;
  padding: 0.75rem 0.85rem;
  border-radius: 8px;
  background: rgba(15, 25, 45, 0.06);
  overflow-x: auto;
  white-space: pre-wrap;
}
.agent-reply-pending {
  margin: 1rem 0 0;
  font-size: 0.85rem;
  color: #7c3aed;
  font-style: italic;
}
</style>
