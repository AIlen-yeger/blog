<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { galleryImagesNotInMarkdown } from '@/utils/renderMarkdown'
import type { NoteItem } from '@/data/mockContent'
import ContentImageUpload from './ContentImageUpload.vue'
import EditorDrawer from './EditorDrawer.vue'
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
const content = ref('')
const ownerOnly = ref(false)
const initialImageUrls = ref<string[]>([])
const imageUploadRef = ref<InstanceType<typeof ContentImageUpload> | null>(null)
const contentRef = ref<HTMLTextAreaElement | null>(null)
const submitting = ref(false)
const submitError = ref('')

const drawerTitle = ref('发布文章')

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

watch(
  () => [props.open, props.editing] as const,
  ([open, item]) => {
    if (!open) return
    submitError.value = ''
    drawerTitle.value = item ? '编辑文章' : '发布文章'
    if (item) {
      title.value = item.title
      excerpt.value = item.excerpt
      tag.value = item.tag
      topicInput.value = topicTitleById(item.topicId)
      content.value = item.content
      ownerOnly.value = Boolean(item.ownerOnly)
      initialImageUrls.value = [...(item.images ?? [])]
    } else {
      title.value = ''
      excerpt.value = ''
      tag.value = '前端'
      topicInput.value = topics.value[0]?.title ?? ''
      content.value = ''
      ownerOnly.value = false
      initialImageUrls.value = []
    }
  },
)

function insertMarkdownAtCursor(snippet: string) {
  const el = contentRef.value
  if (!el) {
    content.value += snippet
    return
  }
  const start = el.selectionStart ?? content.value.length
  const end = el.selectionEnd ?? start
  const before = content.value.slice(0, start)
  const after = content.value.slice(end)
  content.value = before + snippet + after
  void nextTick(() => {
    const pos = start + snippet.length
    el.setSelectionRange(pos, pos)
    el.focus()
  })
}

async function submit(publishStatus: 'published' | 'draft') {
  if (!title.value.trim() || submitting.value) return
  submitting.value = true
  submitError.value = ''
  try {
    const resolved = (await imageUploadRef.value?.resolveImageUrls()) ?? []
    const images = galleryImagesNotInMarkdown(content.value.trim(), resolved)
    await saveNote({
      ...(props.editing?.id ? { id: props.editing.id } : {}),
      title: title.value.trim(),
      excerpt: excerpt.value.trim() || title.value.trim().slice(0, 48),
      tag: tag.value.trim() || '笔记',
      ...resolveTopicPayload(),
      content: content.value.trim(),
      images,
      status: publishStatus,
      ownerOnly: ownerOnly.value,
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
  <EditorDrawer :open="open" :title="drawerTitle" @close="emit('close')">
    <form class="form" @submit.prevent="submit('published')">
      <label>标题</label>
      <input v-model="title" required placeholder="笔记标题" :disabled="submitting" />
      <label>摘要</label>
      <input v-model="excerpt" placeholder="简短描述（可选）" :disabled="submitting" />
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
            placeholder="选择或输入专题"
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
        ref="contentRef"
        v-model="content"
        class="content-area"
        placeholder="详细内容…支持 Markdown；可用 ![说明](图片地址) 插入图片"
        :disabled="submitting"
      />
      <label class="owner-only-row">
        <input v-model="ownerOnly" type="checkbox" :disabled="submitting" />
        <span>仅自己可见</span>
        <small>访客与预览模式下不可见，仅登录管理员可见</small>
      </label>
      <ContentImageUpload
        ref="imageUploadRef"
        :initial-urls="initialImageUrls"
        inline-insert
        @insert-markdown="insertMarkdownAtCursor"
      />
      <p v-if="submitError" class="submit-err" role="alert">{{ submitError }}</p>
      <div class="actions">
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
  </EditorDrawer>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-height: 100%;
}
label {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  margin-top: 0.35rem;
}
input,
textarea {
  padding: 0.6rem 0.75rem;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  background: var(--color-surface-elevated);
  outline: none;
  font-size: 0.9rem;
}
input:focus,
textarea:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.16);
}
.content-area {
  flex: 1;
  min-height: min(50vh, 420px);
  resize: vertical;
  line-height: 1.65;
  font-family: inherit;
}
.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
}
.field {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.owner-only-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  margin-top: 0.5rem;
  padding: 0.55rem 0.65rem;
  border-radius: 10px;
  border: 1px solid rgba(59, 130, 246, 0.18);
  background: rgba(59, 130, 246, 0.06);
  font-size: 0.85rem;
}
.owner-only-row input {
  width: auto;
  margin: 0;
}
.owner-only-row small {
  flex: 1 1 100%;
  font-size: 0.72rem;
  color: var(--color-text-muted);
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
  margin-top: auto;
  padding-top: 0.85rem;
  position: sticky;
  bottom: 0;
  background: linear-gradient(to top, var(--color-surface) 70%, transparent);
}
.btn {
  padding: 0.55rem 1rem;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.88rem;
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
@media (max-width: 768px) {
  .row {
    grid-template-columns: 1fr;
  }
}
</style>
