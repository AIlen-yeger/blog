<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    message: string
    confirmLabel?: string
    cancelLabel?: string
    /** 危险操作（如退出、删除）使用强调色 */
    danger?: boolean
  }>(),
  {
    title: '请确认',
    confirmLabel: '确定',
    cancelLabel: '取消',
    danger: false,
  },
)

const emit = defineEmits<{
  confirm: []
  cancel: []
  close: []
}>()

function onKeydown(e: KeyboardEvent) {
  if (!props.open) return
  if (e.key === 'Escape') {
    e.preventDefault()
    emit('cancel')
    emit('close')
  }
}

watch(
  () => props.open,
  (open) => {
    if (typeof document === 'undefined') return
    document.body.style.overflow = open ? 'hidden' : ''
  },
)

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  if (typeof document !== 'undefined') document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div
        v-if="open"
        class="confirm-backdrop"
        role="presentation"
        @click.self="emit('cancel'); emit('close')"
      >
        <div
          class="confirm-card"
          role="alertdialog"
          :aria-labelledby="open ? 'confirm-title' : undefined"
          :aria-describedby="open ? 'confirm-message' : undefined"
        >
          <div class="confirm-accent" :class="{ 'confirm-accent--danger': danger }" />
          <h2 id="confirm-title" class="confirm-title">{{ title }}</h2>
          <p id="confirm-message" class="confirm-message">{{ message }}</p>
          <div class="confirm-actions">
            <button
              type="button"
              class="btn btn-cancel"
              @click="emit('cancel'); emit('close')"
            >
              {{ cancelLabel }}
            </button>
            <button
              type="button"
              class="btn btn-confirm"
              :class="{ 'btn-confirm--danger': danger }"
              @click="emit('confirm')"
            >
              {{ confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.confirm-fade-enter-active,
.confirm-fade-leave-active {
  transition: opacity 0.22s ease;
}
.confirm-fade-enter-active .confirm-card,
.confirm-fade-leave-active .confirm-card {
  transition:
    transform 0.26s cubic-bezier(0.32, 0.72, 0, 1),
    opacity 0.22s ease;
}
.confirm-fade-enter-from,
.confirm-fade-leave-to {
  opacity: 0;
}
.confirm-fade-enter-from .confirm-card,
.confirm-fade-leave-to .confirm-card {
  transform: translateY(12px) scale(0.97);
  opacity: 0;
}

.confirm-backdrop {
  position: fixed;
  inset: 0;
  z-index: 110;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(22, 32, 48, 0.58);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.confirm-card {
  position: relative;
  width: min(92vw, 380px);
  padding: 1.35rem 1.5rem 1.4rem;
  border-radius: var(--radius-card);
  background: var(--color-surface);
  border: 1px solid rgba(74, 111, 154, 0.18);
  box-shadow:
    var(--shadow-card),
    0 20px 50px rgba(26, 31, 46, 0.22);
  overflow: hidden;
}

.confirm-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(
    90deg,
    var(--color-accent-dark),
    var(--color-accent-light)
  );
}
.confirm-accent--danger {
  background: linear-gradient(90deg, #b45309, #f59e0b);
}

.confirm-title {
  margin: 0.15rem 0 0.55rem;
  font-size: 1.1rem;
  font-weight: 650;
  color: var(--color-text);
  letter-spacing: 0.02em;
}

.confirm-message {
  margin: 0 0 1.25rem;
  font-size: 0.92rem;
  line-height: 1.55;
  color: var(--color-text-muted);
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
}

.btn {
  min-width: 5.5rem;
  padding: 0.58rem 1rem;
  border: none;
  border-radius: 12px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease,
    background 0.15s ease;
}
.btn:active {
  transform: scale(0.98);
}

.btn-cancel {
  background: var(--color-surface-card);
  color: var(--color-text-muted);
  border: 1px solid rgba(74, 111, 154, 0.22);
}
.btn-cancel:hover {
  color: var(--color-text);
  border-color: rgba(74, 111, 154, 0.35);
}

.btn-confirm {
  color: #fff;
  background: linear-gradient(
    135deg,
    var(--color-accent-dark),
    var(--color-accent-light)
  );
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.32);
}
.btn-confirm:hover {
  box-shadow: 0 8px 22px rgba(37, 99, 235, 0.4);
}
.btn-confirm--danger {
  background: linear-gradient(135deg, #c2410c, #f59e0b);
  box-shadow: 0 6px 18px rgba(194, 65, 12, 0.28);
}
.btn-confirm--danger:hover {
  box-shadow: 0 8px 22px rgba(194, 65, 12, 0.36);
}

@media (prefers-reduced-motion: reduce) {
  .confirm-fade-enter-active .confirm-card,
  .confirm-fade-leave-active .confirm-card {
    transition: none;
  }
}
</style>
