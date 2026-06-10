<script setup lang="ts">
defineProps<{
  open: boolean
  title: string
}>()

const emit = defineEmits<{
  close: []
}>()
</script>

<template>
  <Transition name="editor-cover">
    <aside
      v-if="open"
      class="editor-overlay"
      role="dialog"
      :aria-label="title"
    >
      <div class="editor-overlay__panel">
        <header class="editor-overlay__head">
          <button
            type="button"
            class="editor-overlay__close"
            aria-label="关闭编辑"
            @click="emit('close')"
          >
            ×
          </button>
          <h2 class="editor-overlay__title">{{ title }}</h2>
        </header>
        <div class="editor-overlay__body">
          <slot />
        </div>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.editor-overlay {
  position: absolute;
  inset: 0;
  z-index: 50;
  padding: 1rem 1.75rem 1.25rem;
  background: var(--color-bg-dark);
  overflow: hidden;
}

.editor-overlay__panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-surface);
  border-radius: 28px;
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.editor-overlay__head {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 1rem 1.25rem 0.85rem;
  border-bottom: 1px solid rgba(59, 130, 246, 0.12);
  flex-shrink: 0;
}

.editor-overlay__close {
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

.editor-overlay__close:hover {
  background: rgba(59, 130, 246, 0.16);
  color: var(--color-text);
}

.editor-overlay__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.35;
}

.editor-overlay__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.85rem 1.25rem 1.25rem;
}

.editor-cover-enter-active,
.editor-cover-leave-active {
  transition:
    transform 0.32s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.28s ease;
}

.editor-cover-enter-from,
.editor-cover-leave-to {
  transform: translateX(-4%);
  opacity: 0;
}

@media (max-width: 768px) {
  .editor-overlay {
    padding: 0.85rem 0.85rem 1rem;
  }

  .editor-overlay__panel {
    border-radius: 18px;
  }
}
</style>
