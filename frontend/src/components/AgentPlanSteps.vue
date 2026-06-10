<script setup lang="ts">
import type { PlanStep } from '@/api/agentChat'

defineProps<{
  steps: PlanStep[]
}>()

function statusIcon(status: PlanStep['status']) {
  switch (status) {
    case 'running':
      return '…'
    case 'done':
      return '✓'
    case 'failed':
      return '✗'
    default:
      return '○'
  }
}
</script>

<template>
  <div v-if="steps.length" class="agent-plan">
    <p class="agent-plan__label">执行步骤</p>
    <ol class="agent-plan__list">
      <li
        v-for="step in steps"
        :key="step.id"
        class="agent-plan__item"
        :class="`is-${step.status}`"
      >
        <span class="agent-plan__icon" aria-hidden="true">{{ statusIcon(step.status) }}</span>
        <div class="agent-plan__body">
          <span class="agent-plan__title">{{ step.title }}</span>
          <span v-if="step.summary" class="agent-plan__summary">{{ step.summary }}</span>
        </div>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.agent-plan {
  max-width: 720px;
  margin: 0 auto 0.75rem;
  padding: 0.85rem 1rem;
  border: 1px solid rgba(140, 190, 255, 0.22);
  border-radius: 12px;
  background: rgba(18, 32, 56, 0.75);
}

.agent-plan__label {
  margin: 0 0 0.5rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: rgba(142, 200, 255, 0.9);
  letter-spacing: 0.04em;
}

.agent-plan__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.agent-plan__item {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  font-size: 0.86rem;
  color: rgba(220, 235, 255, 0.88);
}

.agent-plan__item.is-pending {
  opacity: 0.55;
}

.agent-plan__item.is-running .agent-plan__icon {
  color: #8ec8ff;
  animation: agent-plan-pulse 1s ease-in-out infinite;
}

.agent-plan__item.is-done .agent-plan__icon {
  color: #6dd4a0;
}

.agent-plan__item.is-failed .agent-plan__icon {
  color: #f08080;
}

.agent-plan__icon {
  flex-shrink: 0;
  width: 1.1rem;
  text-align: center;
  font-weight: 700;
}

.agent-plan__body {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.agent-plan__title {
  line-height: 1.35;
}

.agent-plan__summary {
  font-size: 0.76rem;
  color: rgba(186, 210, 240, 0.72);
}

@keyframes agent-plan-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
</style>
