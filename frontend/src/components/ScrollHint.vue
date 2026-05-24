<script setup lang="ts">
const emit = defineEmits<{
  login: []
  guest: []
}>()
</script>

<template>
  <div
    class="scroll-hint"
    aria-label="向上滑动登录，向下滑动以游客身份浏览"
  >
    <button type="button" class="hint-row hint-up" @click="emit('login')">
      <span class="text">向上滑动登录</span>
      <span class="chevron-wrap" aria-hidden="true">
        <svg class="chevron" viewBox="0 0 24 24" fill="none">
          <path
            d="M6 14l6-6 6 6"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </span>
    </button>
    <div class="hint-divider" aria-hidden="true" />
    <button type="button" class="hint-row hint-down" @click="emit('guest')">
      <span class="text">向下滑动浏览</span>
      <span class="chevron-wrap" aria-hidden="true">
        <svg class="chevron chevron--down" viewBox="0 0 24 24" fill="none">
          <path
            d="M6 10l6 6 6-6"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </span>
    </button>
  </div>
</template>

<style scoped>
.scroll-hint {
  display: inline-flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0;
  margin-top: 1.25rem;
  padding: 0.5rem 1rem 0.55rem;
  border-radius: 999px;
  background: rgba(8, 20, 48, 0.38);
  border: 1px solid rgba(160, 200, 255, 0.16);
  backdrop-filter: blur(8px);
  box-shadow: 0 6px 22px rgba(0, 0, 0, 0.14);
}
.hint-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.32rem 0.1rem;
  border: none;
  background: transparent;
  color: rgba(232, 242, 255, 0.88);
  cursor: pointer;
  user-select: none;
  font: inherit;
  transition: color 0.2s ease;
}
.hint-row:hover {
  color: #fff;
}
.hint-row:hover .chevron-wrap {
  opacity: 0.9;
}
.hint-divider {
  height: 1px;
  margin: 0.08rem 0.4rem;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(200, 225, 255, 0.28) 50%,
    transparent
  );
}
.text {
  font-size: 0.76rem;
  letter-spacing: 0.1em;
  opacity: 0.88;
  line-height: 1.3;
}
.hint-row:hover .text {
  opacity: 1;
}
.chevron-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.125rem;
  height: 1.125rem;
  flex-shrink: 0;
  opacity: 0.55;
  transition: opacity 0.2s ease;
}
.chevron {
  width: 100%;
  height: 100%;
  display: block;
}
.hint-up .chevron-wrap {
  animation: chevron-up 2.6s ease-in-out infinite;
}
.hint-down .chevron-wrap {
  animation: chevron-down 2.6s ease-in-out infinite;
  animation-delay: 0.4s;
}
@keyframes chevron-up {
  0%,
  100% {
    transform: translateY(1px);
    opacity: 0.45;
  }
  50% {
    transform: translateY(-2px);
    opacity: 0.78;
  }
}
@keyframes chevron-down {
  0%,
  100% {
    transform: translateY(-1px);
    opacity: 0.45;
  }
  50% {
    transform: translateY(2px);
    opacity: 0.78;
  }
}
@media (prefers-reduced-motion: reduce) {
  .chevron-wrap {
    animation: none !important;
    opacity: 0.65;
  }
}
</style>
