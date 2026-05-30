<script setup lang="ts">
import { ref, watch } from 'vue'
import type { NoteItem } from '@/data/mockContent'
import ContentImageUpload from './ContentImageUpload.vue'
import { useBlogStore } from '@/composables/useBlogStore'
import { toUserErrorMessage } from '@/utils/userErrorMessage'

const { topics, saveNote } = useBlogStore()

const props = defineProps<{
  open: boolean
  editing: NoteItem | null
}>()

const emit = defineEmits<{
  close: []
}>()

const title = ref('')
const excerpt = ref('')
const tag = ref('')
const topicInput = ref('')
const topicListId = 'note-topic-datalist'

function topicTitleById(id: string): string {
  return topics.value.find((t) => t.id === id)?.title ?? id
}

function resolveTopicPayload(): { topicId?: string; topicTitle?: string } {
  const input = topicInput.value.trim()
  if (!input) return {}
  const matched = topics.value.find(
    (t) => t.id === input || t.title.toLowerCase() === input.toLowerCase(),
  )
  if (matched) return { topicId: matched.id }
  return { topicTitle: input }
}
const content = ref('')
const initialImageUrls = ref<string[]>([])
const imageUploadRef = ref<InstanceType<typeof ContentImageUpload> | null>(null)
const submitting = ref(false)
const submitError = ref('')

watch(
  () => [props.open, props.editing] as const,
  ([open, item]) => {
    if (!open) return
    submitError.value = ''
    if (item) {
      title.value = item.title
      excerpt.value = item.excerpt
      tag.value = item.tag
      topicInput.value = topicTitleById(item.topicId)
      content.value = item.content
      initialImageUrls.value = [...(item.images ?? [])]
    } else {
      title.value = ''
      excerpt.value = ''
      tag.value = '前端'
      topicInput.value = topics.value[0]?.title ?? ''
      content.value = ''
      initialImageUrls.value = []
    }
  },
)

async function submit(publishStatus: 'published' | 'draft') {
  if (!title.value.trim() || submitting.value) return
  submitting.value = true
  submitError.value = ''
  try {
    const images = (await imageUploadRef.value?.resolveImageUrls()) ?? []
    await saveNote({
      ...(props.editing?.id ? { id: props.editing.id } : {}),
      title: title.value.trim(),
      excerpt: excerpt.value.trim() || title.value.trim().slice(0, 48),
      tag: tag.value.trim() || '笔记',
      ...resolveTopicPayload(),
      content: content.value.trim(),
      images,
      status: publishStatus,
    })
    emit('close')
  } catch (err) {
    submitError.value = toUserErrorMessage(err, '保存失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="backdrop" @click.self="!submitting && emit('close')">
        <div class="modal" role="dialog">
          <h2>{{ editing ? '编辑文章' : '发布文章' }}</h2>
          <form class="form" @submit.prevent="submit('published')">
            <label>标题</label>
            <input v-model="title" required placeholder="笔记标题" :disabled="submitting" />
            <label>摘要</label>
            <input v-model="excerpt" placeholder="简短描述" :disabled="submitting" />
            <div class="row">
              <div class="field">
                <label>标签</label>
                <input v-model="tag" placeholder="如：前端" :disabled="submitting" />
              </div>
              <div class="field">
                <label for="note-topic-input">专题</label>
                <input
                  id="note-topic-input"
                  v-model="topicInput"
                  :list="topicListId"
                  placeholder="选择已有或输入新专题"
                  required
                  :disabled="submitting"
                />
                <datalist :id="topicListId">
                  <option v-for="t in topics" :key="t.id" :value="t.title" />
                </datalist>
              </div>
            </div>
            <label>正文</label>
            <textarea
              v-model="content"
              rows="8"
              placeholder="详细内容…"
              :disabled="submitting"
            />
            <ContentImageUpload
              ref="imageUploadRef"
              :initial-urls="initialImageUrls"
            />
            <p v-if="submitError" class="submit-err" role="alert">{{ submitError }}</p>
            <div class="actions">
              <button
                type="button"
                class="btn ghost"
                :disabled="submitting"
                @click="emit('close')"
              >
                取消
              </button>
              <button
                type="button"
                class="btn ghost"
                :disabled="submitting"
                @click="submit('draft')"
              >
                {{ submitting ? '保存中…' : '存为草稿' }}
              </button>
              <button type="submit" class="btn primary" :disabled="submitting">
                {{ submitting ? '发布中…' : editing ? '保存并发布' : '发布' }}
              </button>
            </div>
          </form>
        </div>
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
  z-index: 200;
  background: rgba(15, 25, 45, 0.55);
  display: grid;
  place-items: center;
  padding: 1rem;
  backdrop-filter: blur(6px);
}
.modal {
  width: min(92vw, 560px);
  max-height: 90vh;
  overflow-y: auto;
  background: var(--color-surface);
  border-radius: var(--radius-card);
  padding: 1.5rem 1.6rem;
  box-shadow: var(--shadow-card);
}
h2 {
  margin-bottom: 1rem;
  color: var(--color-text);
  font-size: 1.2rem;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: 0.35rem;
}
input,
select,
textarea {
  padding: 0.65rem 0.85rem;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  background: var(--color-surface-elevated);
  outline: none;
}
input:focus,
select:focus,
textarea:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}
.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.field {
  display: flex;
  flex-direction: column;
}
.submit-err {
  margin: 0.35rem 0 0;
  font-size: 0.82rem;
  color: #b91c1c;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
.btn {
  padding: 0.6rem 1.2rem;
  border-radius: 12px;
  border: none;
  cursor: pointer;
  font-weight: 600;
}
.btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
.btn.primary {
  background: linear-gradient(135deg, var(--color-accent-dark), var(--color-accent-light));
  color: #fff;
}
.btn.ghost {
  background: transparent;
  color: var(--color-accent-dark);
  border: 1px solid rgba(59, 130, 246, 0.3);
}
</style>
