<script setup lang="ts">
import { ref } from 'vue'
import { useAgentReplySettings } from '@/composables/useAgentReplySettings'

const {
  settings,
  setNoteEnabled,
  setLifeEnabled,
  setOwnerOnlyVisible,
  setPreviewMaxChars,
  resetToEnvDefaults,
} = useAgentReplySettings()

const ownerOnlyError = ref('')

async function onOwnerOnlyChange(checked: boolean) {
  ownerOnlyError.value = ''
  try {
    await setOwnerOnlyVisible(checked)
  } catch {
    ownerOnlyError.value = '保存失败，请稍后重试'
  }
}
</script>

<template>
  <section class="agent-reply-settings" aria-labelledby="agent-reply-settings-title">
    <h3 id="agent-reply-settings-title" class="section-title">蕾西亚 自动回复</h3>
    <p class="section-desc">
      笔记或生活记录发布后，由蕾西亚生成回复。可开关展示、限制预览字数；「仅个人可见」会保存到服务器，访客无法看到回复。
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

    <label class="switch-row">
      <span class="switch-label">
        蕾西亚回复仅个人可见
        <span class="switch-hint">开启后仅管理员登录时可见，访客看不到</span>
      </span>
      <input
        type="checkbox"
        :checked="settings.ownerOnlyVisible"
        @change="onOwnerOnlyChange(($event.target as HTMLInputElement).checked)"
      />
    </label>

    <p v-if="ownerOnlyError" class="owner-only-err">{{ ownerOnlyError }}</p>

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

.switch-hint {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 400;
}

.number-row input[type='number'] {
  width: 5.5rem;
  padding: 0.4rem 0.55rem;
  border-radius: 8px;
  border: 1px solid rgba(139, 92, 246, 0.25);
  font-family: inherit;
}

.owner-only-err {
  margin: -0.25rem 0 0.65rem;
  font-size: 0.78rem;
  color: #b91c1c;
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
