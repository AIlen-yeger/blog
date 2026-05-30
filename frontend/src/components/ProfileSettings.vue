<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import type { ProfileData } from '@/data/mockContent'
import { uploadProfileAvatar } from '@/api/blog'
import { useMockApi } from '@/api/http'
import AvatarImage from './AvatarImage.vue'
import AgentReplySettingsPanel from './AgentReplySettingsPanel.vue'

const props = defineProps<{
  profile: ProfileData
  saving?: boolean
}>()

const emit = defineEmits<{
  save: [profile: ProfileData]
  cancel: []
}>()

const form = ref<ProfileData>({ ...props.profile })
const focusText = ref(props.profile.focus.join('、'))
const pickError = ref('')
const pendingAvatarFile = ref<File | null>(null)
const pendingAvatarPreview = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)

watch(
  () => props.profile,
  (p) => {
    clearPendingAvatar()
    form.value = { ...p }
    focusText.value = p.focus.join('、')
  },
  { deep: true },
)

const avatarDisplaySrc = computed(() => {
  if (pendingAvatarPreview.value) return pendingAvatarPreview.value
  // 由 AvatarImage 统一 resolve，避免双重解析成 /v1/api/uploads/...
  return form.value.avatarUrl
})

const hasPendingAvatar = computed(() => !!pendingAvatarFile.value)

function clearPendingAvatar() {
  if (pendingAvatarPreview.value.startsWith('blob:')) {
    URL.revokeObjectURL(pendingAvatarPreview.value)
  }
  pendingAvatarFile.value = null
  pendingAvatarPreview.value = ''
}

function openFilePicker() {
  if (props.saving) return
  pickError.value = ''
  fileInputRef.value?.click()
}

function onAvatarFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  pickError.value = ''
  if (!file.type.startsWith('image/')) {
    pickError.value = '仅支持图片文件'
    input.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    pickError.value = '图片不能超过 5MB'
    input.value = ''
    return
  }
  clearPendingAvatar()
  pendingAvatarFile.value = file
  pendingAvatarPreview.value = URL.createObjectURL(file)
  input.value = ''
}

async function submit() {
  const focus = focusText.value
    .split(/[,，、\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)

  let avatarUrl = form.value.avatarUrl
  if (pendingAvatarFile.value) {
    const file = pendingAvatarFile.value
    if (useMockApi()) {
      avatarUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => {
          if (typeof reader.result === 'string') resolve(reader.result)
          else reject(new Error('读取图片失败'))
        }
        reader.onerror = () => reject(new Error('读取图片失败'))
        reader.readAsDataURL(file)
      })
    } else {
      const res = await uploadProfileAvatar(file)
      avatarUrl = res.avatarUrl
    }
    clearPendingAvatar()
  }

  emit('save', {
    ...form.value,
    avatarUrl,
    focus: focus.length ? focus : ['学习笔记'],
  })
}

onUnmounted(() => {
  clearPendingAvatar()
})
</script>

<template>
  <div class="settings">
    <p class="desc">
      修改头像、昵称、个人介绍与兴趣标签，保存后同步到关于页与首页展示。
    </p>

    <!-- 头像区独立于 form，避免选完文件误触发表单提交导致弹窗关闭 -->
    <div class="avatar-row">
      <AvatarImage :src="avatarDisplaySrc" size="lg" shape="round" />
      <div class="avatar-fields">
        <label for="avatar-url">头像图片 URL</label>
        <input
          id="avatar-url"
          v-model="form.avatarUrl"
          placeholder="https://… 或选择本地图片，保存时上传"
          @keydown.enter.prevent
        />
        <input
          ref="fileInputRef"
          type="file"
          accept="image/*"
          class="file-input-hidden"
          tabindex="-1"
          aria-hidden="true"
          @change="onAvatarFile"
        />
        <button type="button" class="file-btn" :disabled="saving" @click="openFilePicker">
          选择本地图片
        </button>
        <p v-if="hasPendingAvatar" class="field-ok">已选择新头像，点击「保存资料」后才会上传</p>
        <p v-if="pickError" class="field-err">{{ pickError }}</p>
      </div>
    </div>

    <form class="form" @submit.prevent="void submit()">
      <label for="profile-name">昵称</label>
      <input id="profile-name" v-model="form.name" required maxlength="32" />

      <label for="profile-sub">英文副标题</label>
      <input id="profile-sub" v-model="form.subtitle" maxlength="64" />

      <label for="profile-bio">个人介绍</label>
      <textarea id="profile-bio" v-model="form.bio" rows="4" maxlength="500" />

      <label for="profile-focus">兴趣标签（顿号、逗号分隔）</label>
      <input
        id="profile-focus"
        v-model="focusText"
        placeholder="Vue / TypeScript、工程化、读书笔记"
      />

      <AgentReplySettingsPanel />

      <div class="actions">
        <button type="button" class="btn ghost" :disabled="saving" @click="emit('cancel')">
          取消
        </button>
        <button type="submit" class="btn primary" :disabled="saving">
          {{ saving ? '保存中…' : '保存资料' }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.settings {
  width: 100%;
}
.desc {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  margin-bottom: 1.25rem;
  line-height: 1.55;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.avatar-row {
  display: flex;
  gap: 1.25rem;
  align-items: flex-start;
  margin-bottom: 0.75rem;
  padding-bottom: 1rem;
  border-bottom: 1px dashed rgba(59, 130, 246, 0.15);
}
.avatar-fields {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: 0.35rem;
}
input,
textarea {
  padding: 0.65rem 0.85rem;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  background: var(--color-surface-elevated);
  outline: none;
  font-family: inherit;
}
input:focus,
textarea:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}
.file-input-hidden {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}
.file-btn {
  display: inline-block;
  margin-top: 0.5rem;
  padding: 0.45rem 0.9rem;
  border-radius: 10px;
  border: none;
  background: #dbeafe;
  color: var(--color-accent-dark);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  width: fit-content;
}
.file-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.field-ok {
  font-size: 0.8rem;
  color: #2d8a4e;
  margin: 0.25rem 0 0;
}
.field-err {
  font-size: 0.8rem;
  color: #a63d32;
  margin: 0.25rem 0 0;
}
.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.65rem;
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}
.btn {
  padding: 0.65rem 1.25rem;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  font-size: 0.9rem;
}
.btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
.btn.primary {
  background: linear-gradient(135deg, var(--color-accent-dark), var(--color-accent-light));
  color: #fff;
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.35);
}
.btn.ghost {
  background: transparent;
  color: var(--color-text-muted);
  border: 1px solid rgba(59, 130, 246, 0.25);
}
.btn.ghost:hover:not(:disabled) {
  background: #f0f7ff;
  color: var(--color-accent-dark);
}

@media (max-width: 768px) {
  .avatar-row {
    flex-direction: column;
    align-items: center;
  }
  .avatar-fields {
    width: 100%;
  }
}
</style>
