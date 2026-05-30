<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { uploadContentImage } from '@/api/blog'
import {
  createDraftFromFile,
  createDraftFromUrl,
  revokeDraftPreview,
  type ImageDraftItem,
} from '@/utils/deferredUpload'
import { resolveMediaUrl } from '@/utils/mediaUrl'
import { toUserErrorMessage } from '@/utils/userErrorMessage'

const props = defineProps<{
  /** 打开编辑时已有的服务器图片地址 */
  initialUrls?: string[]
}>()

const drafts = ref<ImageDraftItem[]>([])
const pickError = ref('')

function previewSrc(item: ImageDraftItem) {
  if (item.file) return item.preview
  return resolveMediaUrl(item.preview)
}

function syncFromInitial(urls?: string[]) {
  drafts.value.forEach(revokeDraftPreview)
  drafts.value = (urls ?? []).map((url, i) => createDraftFromUrl(url, i))
}

watch(
  () => props.initialUrls,
  (urls) => syncFromInitial(urls),
  { immediate: true },
)

function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files?.length) return
  pickError.value = ''
  try {
    for (const file of Array.from(files)) {
      if (!file.type.startsWith('image/')) {
        throw new Error('仅支持图片文件')
      }
      if (file.size > 5 * 1024 * 1024) {
        throw new Error('单张图片不能超过 5MB')
      }
      if (drafts.value.length >= 12) {
        throw new Error('最多 12 张图片')
      }
      drafts.value.push(createDraftFromFile(file))
    }
  } catch (err) {
    pickError.value = toUserErrorMessage(err, '添加失败，请稍后重试')
  } finally {
    input.value = ''
  }
}

function removeAt(index: number) {
  const item = drafts.value[index]
  if (item) revokeDraftPreview(item)
  drafts.value = drafts.value.filter((_, i) => i !== index)
}

/** 发布/保存时调用：上传本地待传文件，返回最终 URL 列表 */
async function resolveImageUrls(): Promise<string[]> {
  const urls: string[] = []
  for (const item of drafts.value) {
    if (item.url) {
      urls.push(item.url)
      continue
    }
    if (item.file) {
      const { url } = await uploadContentImage(item.file)
      revokeDraftPreview(item)
      item.url = url
      item.file = undefined
      item.preview = url
      urls.push(url)
    }
  }
  return urls
}

function hasLocalPending() {
  return drafts.value.some((d) => !!d.file)
}

onUnmounted(() => {
  drafts.value.forEach(revokeDraftPreview)
})

defineExpose({ resolveImageUrls, hasLocalPending })
</script>

<template>
  <div class="img-upload">
    <div class="img-upload-head">
      <span class="label">配图</span>
      <label class="pick-btn" :class="{ disabled: drafts.length >= 12 }">
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          multiple
          :disabled="drafts.length >= 12"
          @change="onPick"
        />
        + 添加图片
      </label>
      <span class="hint">最多 12 张，单张 ≤ 5MB；点击发布后才会上传</span>
    </div>

    <p v-if="pickError" class="err">{{ pickError }}</p>

    <ul v-if="drafts.length" class="preview-list">
      <li v-for="(item, i) in drafts" :key="item.key" class="preview-item">
        <img :src="previewSrc(item)" :alt="`配图 ${i + 1}`" loading="lazy" />
        <span v-if="item.file" class="badge">待上传</span>
        <button type="button" class="remove" title="移除" @click="removeAt(i)">×</button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.img-upload {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.img-upload-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.pick-btn {
  padding: 0.4rem 0.85rem;
  border-radius: 10px;
  border: 1px dashed rgba(59, 130, 246, 0.45);
  background: rgba(59, 130, 246, 0.06);
  color: var(--color-accent-dark);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}

.pick-btn.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.pick-btn input {
  display: none;
}

.hint {
  font-size: 0.72rem;
  color: var(--color-text-muted);
}

.err {
  margin: 0;
  font-size: 0.78rem;
  color: #b91c1c;
}

.preview-list {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin: 0;
  padding: 0;
}

.preview-item {
  position: relative;
  width: 88px;
  height: 88px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.preview-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.badge {
  position: absolute;
  left: 4px;
  bottom: 4px;
  padding: 0.1rem 0.35rem;
  border-radius: 6px;
  background: rgba(37, 99, 235, 0.85);
  color: #fff;
  font-size: 0.62rem;
  font-weight: 600;
}

.remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 50%;
  background: rgba(15, 25, 45, 0.65);
  color: #fff;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}

.remove:hover {
  background: rgba(185, 28, 28, 0.85);
}
</style>
