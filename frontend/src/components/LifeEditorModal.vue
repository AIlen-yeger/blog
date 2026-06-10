<script setup lang="ts">
import { ref, watch } from 'vue'
import type { LifeItem } from '@/data/mockContent'
import ContentImageUpload from './ContentImageUpload.vue'
import EditorDrawer from './EditorDrawer.vue'
import { useBlogStore } from '@/composables/useBlogStore'
import { toUserErrorMessage } from '@/utils/userErrorMessage'

const { saveLife } = useBlogStore()

const props = defineProps<{
  open: boolean
  editing: LifeItem | null
}>()

const emit = defineEmits<{
  close: []
}>()

const title = ref('')
const excerpt = ref('')
const tag = ref('')
const content = ref('')
const initialImageUrls = ref<string[]>([])
const imageUploadRef = ref<InstanceType<typeof ContentImageUpload> | null>(null)
const submitting = ref(false)
const submitError = ref('')
const drawerTitle = ref('发布生活记录')

watch(
  () => [props.open, props.editing] as const,
  ([open, item]) => {
    if (!open) return
    submitError.value = ''
    drawerTitle.value = item ? '编辑记录' : '发布生活记录'
    if (item) {
      title.value = item.title
      excerpt.value = item.excerpt
      tag.value = item.tag
      content.value = item.content
      initialImageUrls.value = [...(item.images ?? [])]
    } else {
      title.value = ''
      excerpt.value = ''
      tag.value = '生活'
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
    await saveLife({
      ...(props.editing?.id ? { id: props.editing.id } : {}),
      title: title.value.trim(),
      excerpt: excerpt.value.trim() || title.value.trim().slice(0, 48),
      tag: tag.value.trim() || '生活',
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
  <EditorDrawer :open="open" :title="drawerTitle" @close="emit('close')">
    <form class="form" @submit.prevent="submit('published')">
      <label>标题</label>
      <input v-model="title" required placeholder="记录标题" :disabled="submitting" />
      <label>摘要</label>
      <input v-model="excerpt" placeholder="简短描述（可选）" :disabled="submitting" />
      <label>标签</label>
      <input v-model="tag" placeholder="如：美食、户外" :disabled="submitting" />
      <label>正文</label>
      <textarea
        v-model="content"
        class="content-area"
        placeholder="详细内容…"
        :disabled="submitting"
      />
      <ContentImageUpload ref="imageUploadRef" :initial-urls="initialImageUrls" />
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
</style>
