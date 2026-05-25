<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const { pinned, showPin } = withDefaults(
  defineProps<{
    pinned?: boolean
    showPin?: boolean
  }>(),
  { pinned: false, showPin: false },
)

const emit = defineEmits<{
  edit: []
  delete: []
  pin: []
}>()

const open = ref(false)
const rootRef = ref<HTMLElement | null>(null)

function toggle() {
  open.value = !open.value
}

function close() {
  open.value = false
}

function onEdit() {
  close()
  emit('edit')
}

function onDelete() {
  close()
  emit('delete')
}

function onPin() {
  close()
  emit('pin')
}

function onDocClick(e: MouseEvent) {
  if (!open.value) return
  const el = rootRef.value
  if (el && !el.contains(e.target as Node)) close()
}

onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <div ref="rootRef" class="card-menu" @click.stop>
    <button
      type="button"
      class="menu-trigger"
      aria-label="更多操作"
      aria-haspopup="menu"
      :aria-expanded="open"
      @click="toggle"
    >
      <span class="dot" aria-hidden="true" />
      <span class="dot" aria-hidden="true" />
      <span class="dot" aria-hidden="true" />
    </button>
    <Transition name="menu-fade">
      <div v-if="open" class="menu-panel" role="menu">
        <button v-if="showPin" type="button" role="menuitem" @click="onPin">
          {{ pinned ? '取消置顶' : '置顶' }}
        </button>
        <button type="button" role="menuitem" @click="onEdit">编辑</button>
        <button type="button" class="danger" role="menuitem" @click="onDelete">删除</button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.card-menu {
  position: relative;
}
.menu-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: none;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.08);
  color: var(--color-accent-dark);
  cursor: pointer;
  transition: background 0.2s;
  flex-shrink: 0;
}
.menu-trigger:hover {
  background: rgba(59, 130, 246, 0.16);
}
.dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: currentColor;
}
.menu-panel {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  z-index: 20;
  min-width: 7.5rem;
  padding: 0.35rem;
  border-radius: 12px;
  background: #fff;
  border: 1px solid rgba(59, 130, 246, 0.18);
  box-shadow: 0 8px 24px rgba(30, 45, 60, 0.12);
}
.menu-panel button {
  display: block;
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: none;
  border-radius: 8px;
  background: transparent;
  text-align: left;
  font-size: 0.82rem;
  color: var(--color-text);
  cursor: pointer;
}
.menu-panel button:hover {
  background: rgba(59, 130, 246, 0.08);
}
.menu-panel button.danger {
  color: #b91c1c;
}
.menu-panel button.danger:hover {
  background: #fee2e2;
}
.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
