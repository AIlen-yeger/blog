<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ContentKind } from '@/types/views'
import { useContentViewTracking } from '@/composables/useContentView'
import ContentImageGallery from './ContentImageGallery.vue'

export interface ReaderItem {
  id: string
  title: string
  tag: string
  date: string
  content: string
  images?: string[]
  viewCount?: number
}

const props = defineProps<{
  open: boolean
  kind: ContentKind
  item: ReaderItem | null
}>()

const emit = defineEmits<{
  close: []
  'view-count': [count: number]
}>()

const trackOpen = ref(false)

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
            <button type="button" class="close-btn" aria-label="关闭" @click="emit('close')">
              ×
            </button>
          </header>
          <div class="reader-body">
            <div class="content">{{ item.content }}</div>
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
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
