<script setup lang="ts">
import { computed, ref } from 'vue'
import type { LifeItem } from '@/data/mockContent'
import CardActionMenu from './CardActionMenu.vue'
import ContentImageGallery from './ContentImageGallery.vue'
import ContentReaderModal from './ContentReaderModal.vue'
import AgentReplyBlock from './AgentReplyBlock.vue'
import { useAgentReplySettings } from '@/composables/useAgentReplySettings'

const props = withDefaults(
  defineProps<{
    item: LifeItem
    editable?: boolean
  }>(),
  { editable: true },
)

const emit = defineEmits<{
  edit: [item: LifeItem]
  delete: [id: string]
  pin: [id: string]
}>()

const readerOpen = ref(false)
const { shouldShowReply } = useAgentReplySettings()

const showAgentReply = computed(() => shouldShowReply('life', props.item.agentReply))

function openReader() {
  readerOpen.value = true
}

function onEdit() {
  emit('edit', props.item)
}

function onDelete() {
  if (confirm(`确定删除「${props.item.title}」吗？`)) {
    emit('delete', props.item.id)
  }
}

function onPin() {
  emit('pin', props.item.id)
}
</script>

<template>
  <article class="life-card" :class="{ pinned: item.pinned }" :id="`life-${item.id}`">
    <div class="life-head">
      <div class="head-top">
        <div class="head-tags">
          <span v-if="item.pinned" class="pin-badge">置顶</span>
          <span v-if="item.status === 'draft'" class="draft-badge">草稿</span>
          <span class="tag">{{ item.tag }}</span>
        </div>
        <CardActionMenu
          v-if="editable"
          show-pin
          :pinned="!!item.pinned"
          @edit="onEdit"
          @delete="onDelete"
          @pin="onPin"
        />
      </div>
      <h3 class="card-title" :class="{ 'is-pinned': item.pinned }">{{ item.title }}</h3>
      <p class="excerpt">{{ item.excerpt }}</p>
      <AgentReplyBlock
        v-if="showAgentReply && item.agentReply"
        kind="life"
        mode="preview"
        :reply="item.agentReply"
      />
      <ContentImageGallery v-if="item.images?.length" :images="item.images" compact />
      <div class="meta">
        <time :datetime="item.date">{{ item.date }}</time>
        <div class="meta-right">
          <button type="button" class="read-btn" @click="openReader">阅读全文</button>
        </div>
      </div>
    </div>

    <ContentReaderModal
      :open="readerOpen"
      kind="life"
      :item="item"
      @close="readerOpen = false"
    />
  </article>
</template>

<style scoped>
.life-card {
  border-radius: 18px;
  background: var(--color-surface-elevated);
  border: 1px solid rgba(59, 130, 246, 0.12);
  box-shadow: 0 4px 16px rgba(30, 45, 60, 0.08);
  overflow: hidden;
  transition: border-color 0.25s, box-shadow 0.25s;
}
.life-card.pinned {
  border-color: rgba(245, 158, 11, 0.45);
  box-shadow: 0 6px 20px rgba(245, 158, 11, 0.12);
}
.life-head {
  padding: 1.2rem 1.3rem;
}
.head-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.5rem;
}
.head-tags {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
}
.pin-badge {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.12rem 0.45rem;
  border-radius: 6px;
  background: #fef3c7;
  color: #b45309;
}
.draft-badge {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.12rem 0.45rem;
  border-radius: 6px;
  background: var(--color-draft-bg);
  color: var(--color-draft-text);
}
.tag {
  font-size: 0.72rem;
  color: var(--color-accent-dark);
  font-weight: 600;
}
.card-title {
  margin: 0.35rem 0 0.3rem;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--color-text);
  transition: color 0.2s;
}
.card-title.is-pinned {
  color: #0c1929;
  font-weight: 700;
}
.excerpt {
  font-size: 0.88rem;
  color: var(--color-text-muted);
  line-height: 1.55;
}
.meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.55rem;
  gap: 0.75rem;
}
.meta-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
time {
  font-size: 0.78rem;
  color: #9a9aad;
}
.read-btn {
  padding: 0;
  border: none;
  background: none;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--color-accent);
  cursor: pointer;
}
.read-btn:hover {
  text-decoration: underline;
}
</style>
