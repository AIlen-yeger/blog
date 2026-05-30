<script setup lang="ts">
import { computed } from 'vue'
import type { AgentReplyContentKind } from '@/types/agentReply'
import { useAgentReplySettings } from '@/composables/useAgentReplySettings'
import { truncateAgentReplyPreview } from '@/utils/agentReplyText'

const props = withDefaults(
  defineProps<{
    reply: string
    kind: AgentReplyContentKind
    /** preview：卡片摘要；full：阅读全文弹窗 */
    mode?: 'preview' | 'full'
  }>(),
  { mode: 'preview' },
)

const { previewMaxChars } = useAgentReplySettings()

const label = computed(() => (props.kind === 'note' ? 'Kohaku · 笔记回复' : 'Kohaku · 生活回复'))

const body = computed(() => {
  const text = (props.reply || '').trim()
  if (props.mode === 'full') {
    return { display: text, truncated: false }
  }
  return truncateAgentReplyPreview(text, previewMaxChars.value)
})
</script>

<template>
  <aside
    class="agent-reply"
    :class="[`agent-reply--${mode}`, `agent-reply--${kind}`]"
    :aria-label="label"
  >
    <header class="agent-reply__head">
      <span class="agent-reply__badge" aria-hidden="true">✦</span>
      <span class="agent-reply__label">{{ label }}</span>
    </header>
    <p class="agent-reply__text">{{ body.display }}</p>
    <p v-if="mode === 'preview' && body.truncated" class="agent-reply__hint">
      点击「阅读全文」查看 Kohaku 的完整回复
    </p>
  </aside>
</template>

<style scoped>
.agent-reply {
  margin-top: 0.75rem;
  padding: 0.65rem 0.85rem;
  border-radius: 12px;
  border: 1px solid rgba(139, 92, 246, 0.22);
  background: linear-gradient(
    135deg,
    rgba(237, 233, 254, 0.85) 0%,
    rgba(224, 242, 254, 0.55) 100%
  );
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.agent-reply--full {
  margin-top: 1.25rem;
  padding: 0.85rem 1rem;
}

.agent-reply__head {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 0.35rem;
}

.agent-reply__badge {
  font-size: 0.75rem;
  color: #7c3aed;
  line-height: 1;
}

.agent-reply__label {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #6d28d9;
  font-family: var(--font-sans);
}

.agent-reply__text {
  margin: 0;
  font-size: 0.86rem;
  line-height: 1.65;
  color: #5b21b6;
  font-family: var(--font-sans);
  font-weight: 400;
  white-space: pre-wrap;
  word-break: break-word;
}

.agent-reply--preview .agent-reply__text {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  overflow: hidden;
}

.agent-reply__hint {
  margin: 0.4rem 0 0;
  font-size: 0.72rem;
  color: #7c3aed;
  opacity: 0.85;
  font-family: inherit;
  font-style: normal;
}
</style>
