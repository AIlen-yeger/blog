<script setup lang="ts">

defineProps<{

  /** 已登录：上滑进入博客；未登录：上滑打开登录 */

  loggedIn?: boolean

}>()



const emit = defineEmits<{

  login: []

  guest: []

  enterBlog: []

}>()

</script>



<template>

  <div

    class="scroll-hint"

    :aria-label="

      loggedIn

        ? '向上滑动进入博客，向下滑动预览内容'

        : '向上滑动登录，向下滑动以游客身份浏览'

    "

  >

    <button

      type="button"

      class="hint-item hint-up"

      @click="loggedIn ? emit('enterBlog') : emit('login')"

    >

      <span class="text">{{ loggedIn ? '向上进入博客' : '向上滑动登录' }}</span>

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

    <button type="button" class="hint-item hint-down" @click="emit('guest')">

      <span class="text">向下滑动预览</span>

      <span class="chevron-wrap" aria-hidden="true">

        <svg class="chevron" viewBox="0 0 24 24" fill="none">

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

  flex-direction: row;

  align-items: stretch;

  gap: 0;

  padding: 0.45rem 0.85rem 0.5rem;

  border-radius: 999px;

  background: rgba(32, 52, 88, 0.24);

  border: 1px solid rgba(150, 195, 255, 0.24);

  -webkit-backdrop-filter: blur(7px);

  backdrop-filter: blur(7px);

  box-shadow: 0 6px 22px rgba(0, 0, 0, 0.14);

}

.hint-item {

  display: flex;

  flex-direction: column;

  align-items: center;

  justify-content: flex-end;

  gap: 0.35rem;

  min-width: 5.5rem;

  padding: 0.2rem 0.65rem 0.15rem;

  border: none;

  background: transparent;

  color: rgba(232, 242, 255, 0.88);

  cursor: pointer;

  user-select: none;

  font: inherit;

  transition: color 0.2s ease;

}

.hint-item:hover {

  color: #fff;

}

.hint-item:hover .chevron-wrap {

  opacity: 0.9;

}

.hint-divider {

  width: 1px;

  align-self: stretch;

  margin: 0.35rem 0.15rem;

  background: linear-gradient(

    180deg,

    transparent,

    rgba(200, 225, 255, 0.28) 50%,

    transparent

  );

}

.text {

  font-size: 0.72rem;

  letter-spacing: 0.08em;

  opacity: 0.88;

  line-height: 1.3;

  text-align: center;

  white-space: nowrap;

}

.hint-item:hover .text {

  opacity: 1;

}

.chevron-wrap {

  display: flex;

  align-items: center;

  justify-content: center;

  width: 1.25rem;

  height: 1.25rem;

  flex-shrink: 0;

  opacity: 0.6;

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

    transform: translateY(2px);

    opacity: 0.45;

  }

  50% {

    transform: translateY(-3px);

    opacity: 0.85;

  }

}

@keyframes chevron-down {

  0%,

  100% {

    transform: translateY(-2px);

    opacity: 0.45;

  }

  50% {

    transform: translateY(3px);

    opacity: 0.85;

  }

}

@media (prefers-reduced-motion: reduce) {

  .chevron-wrap {

    animation: none !important;

    opacity: 0.65;

  }

}

@media (max-width: 767px) {
  .scroll-hint {
    width: 100%;
    max-width: min(100%, 22rem);
    justify-content: center;
    padding: 0.4rem 0.55rem 0.45rem;
  }
  .hint-item {
    min-width: 0;
    flex: 1;
    padding: 0.25rem 0.4rem 0.2rem;
    min-height: 44px;
  }
  .text {
    font-size: 0.7rem;
    letter-spacing: 0.04em;
    white-space: normal;
    line-height: 1.25;
  }
}

@media (max-width: 400px) {
  .hint-item {
    padding-inline: 0.3rem;
  }
  .text {
    font-size: 0.65rem;
  }
}

</style>

