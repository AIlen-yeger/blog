<script setup lang="ts">
import ScrollHint from './ScrollHint.vue'
import AvatarImage from './AvatarImage.vue'
import { useBlogStore } from '@/composables/useBlogStore'

defineProps<{
  mini?: boolean
}>()

const emit = defineEmits<{
  login: []
  guest: []
}>()

const { profile } = useBlogStore()
</script>

<template>
  <header class="hero" :class="{ mini }">
    <template v-if="!mini">
      <div class="hero-top">
        <div class="hero-banner">
          <AvatarImage :src="profile.avatarUrl" size="hero" />
          <div class="hero-caption">
            <h1 class="name">{{ profile.name }}</h1>
            <p class="caption-sub">{{ profile.subtitle }}</p>
          </div>
        </div>
      </div>
      <div class="hero-bottom">
        <p class="intro">
          {{ profile.bio || '记录前端学习与知识整理的个人空间。' }}
        </p>
        <ScrollHint @login="emit('login')" @guest="emit('guest')" />
      </div>
    </template>
    <template v-else>
      <AvatarImage :src="profile.avatarUrl" size="sm" shape="round" />
      <h1 class="name">{{ profile.name }}</h1>
    </template>
  </header>
</template>

<style scoped>
.hero {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  color: var(--color-text-on-dark);
  transition:
    transform 0.95s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.5s ease;
}
.hero.mini {
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem 1.25rem;
  height: auto;
}
.hero-top {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  padding: var(--landing-gap-top) var(--landing-gap-x) 0;
}
.hero-banner {
  position: relative;
  width: min(92vw, 560px);
  height: min(52vh, 480px);
  min-height: 300px;
  margin: 0 auto;
  display: flex;
}
.hero-banner :deep(.avatar-img.hero) {
  width: 100%;
  height: 100%;
}
.hero-caption {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 2.75rem 1.75rem 1.35rem;
  background: linear-gradient(
    to top,
    rgba(10, 25, 55, 0.82) 0%,
    rgba(15, 40, 90, 0.4) 55%,
    transparent 100%
  );
  border-radius: 0 0 24px 24px;
  text-align: left;
  pointer-events: none;
}
.hero-caption .name {
  margin: 0;
  font-size: clamp(1.85rem, 5vw, 2.5rem);
  font-weight: 700;
  color: #fff;
}
.caption-sub {
  margin-top: 0.35rem;
  font-size: 0.78rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(200, 225, 255, 0.85);
}
.hero-bottom {
  flex-shrink: 0;
  text-align: center;
  padding: 1.25rem var(--landing-gap-x) 1.5rem;
}
.hero.mini .name {
  margin: 0;
  font-size: 1.2rem;
}
.intro {
  margin: 0 auto 0.75rem;
  max-width: 520px;
  line-height: 1.55;
  font-size: 0.95rem;
  color: rgba(232, 242, 255, 0.9);
}
</style>
