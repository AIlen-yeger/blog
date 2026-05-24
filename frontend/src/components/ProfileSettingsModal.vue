<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ProfileData } from '@/data/mockContent'
import ProfileSettings from './ProfileSettings.vue'

const props = defineProps<{
  open: boolean
  profile: ProfileData
  onSave: (data: ProfileData) => Promise<void>
}>()

const emit = defineEmits<{
  close: []
}>()

const saving = ref(false)
const saveError = ref('')

watch(
  () => props.open,
  (v) => {
    if (v) saveError.value = ''
  },
)

async function handleSave(data: ProfileData) {
  saving.value = true
  saveError.value = ''
  try {
    await props.onSave(data)
    emit('close')
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="backdrop" @click.self="emit('close')">
        <div class="modal card" role="dialog" aria-labelledby="profile-edit-title">
          <div class="card-accent" />
          <button type="button" class="close" aria-label="关闭" @click="emit('close')">
            ×
          </button>
          <h2 id="profile-edit-title">编辑个人资料</h2>
          <p class="modal-sub">修改后将更新关于页与首页展示</p>
          <p v-if="saveError" class="err" role="alert">{{ saveError }}</p>
          <ProfileSettings
            :profile="profile"
            :saving="saving"
            @save="handleSave"
            @cancel="emit('close')"
          />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
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
  backdrop-filter: blur(8px);
}
.card {
  width: min(92vw, 520px);
  max-height: 90vh;
  overflow-y: auto;
  background: var(--color-surface);
  border-radius: var(--radius-card);
  padding: 1.5rem 1.6rem 1.75rem;
  box-shadow: var(--shadow-card);
  position: relative;
  border: 1px solid rgba(0, 0, 0, 0.06);
}
.card-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--color-accent-dark), var(--color-accent-light));
  border-radius: var(--radius-card) var(--radius-card) 0 0;
}
.close {
  position: absolute;
  top: 0.85rem;
  right: 1rem;
  border: none;
  background: none;
  font-size: 1.6rem;
  line-height: 1;
  cursor: pointer;
  color: #888;
  width: 2rem;
  height: 2rem;
  border-radius: 8px;
  z-index: 1;
}
.close:hover {
  background: rgba(0, 0, 0, 0.06);
  color: var(--color-text);
}
h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 1.25rem;
  font-weight: 650;
  padding-right: 2rem;
}
.modal-sub {
  margin: 0.35rem 0 1rem;
  font-size: 0.82rem;
  color: var(--color-text-muted);
}
.err {
  color: #a63d32;
  font-size: 0.88rem;
  margin-bottom: 0.75rem;
  padding: 0.5rem 0.65rem;
  background: #fdecea;
  border-radius: 10px;
}
</style>
