<script setup lang="ts">
import { useAgentReplySettings } from '@/composables/useAgentReplySettings'

const {
  settings,
  setNoteEnabled,
  setLifeEnabled,
  setPreviewMaxChars,
  resetToEnvDefaults,
} = useAgentReplySettings()
</script>

<template>
  <section class="agent-reply-settings" aria-labelledby="agent-reply-settings-title">
    <h3 id="agent-reply-settings-title" class="section-title">Kohaku 自动回复</h3>
    <p class="section-desc">
      发布笔记或生活记录后，由 Kohaku 根据内容生成回复。可分别开关；卡片上超出字数会显示省略号，完整内容在「阅读全文」中查看。
    </p>

    <label class="switch-row">
      <span class="switch-label">笔记自动回复</span>
      <input
        type="checkbox"
        :checked="settings.noteEnabled"
        @change="setNoteEnabled(($event.target as HTMLInputElement).checked)"
      />
    </label>

    <label class="switch-row">
      <span class="switch-label">生活记录自动回复</span>
      <input
        type="checkbox"
        :checked="settings.lifeEnabled"
        @change="setLifeEnabled(($event.target as HTMLInputElement).checked)"
      />
    </label>

    <label class="number-row">
      <span class="switch-label">卡片预览字数上限</span>
      <input
        type="number"
        min="20"
        max="500"
        step="10"
        :value="settings.previewMaxChars"
        @change="
          setPreviewMaxChars(Number(($event.target as HTMLInputElement).value))
        "
      />
    </label>

    <button type="button" class="reset-btn" @click="resetToEnvDefaults">
      恢复为环境默认
    </button>
  </section>
</template>

<style scoped>
.agent-reply-settings {
  margin-top: 1.25rem;
  padding-top: 1.25rem;
  border-top: 1px dashed rgba(139, 92, 246, 0.25);
}

.section-title {
  margin: 0 0 0.35rem;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
}

.section-desc {
  margin: 0 0 1rem;
  font-size: 0.82rem;
  line-height: 1.55;
  color: var(--color-text-muted);
}

.switch-row,
.number-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.65rem;
  font-size: 0.88rem;
  color: var(--color-text);
}

.switch-label {
  flex: 1;
}

.number-row input[type='number'] {
  width: 5.5rem;
  padding: 0.4rem 0.55rem;
  border-radius: 8px;
  border: 1px solid rgba(139, 92, 246, 0.25);
  font-family: inherit;
}

.reset-btn {
  margin-top: 0.5rem;
  padding: 0.35rem 0.65rem;
  border: none;
  background: none;
  color: #7c3aed;
  font-size: 0.78rem;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
