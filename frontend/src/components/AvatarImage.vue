<script setup lang="ts">
import { computed } from 'vue'
import { resolveMediaUrl } from '@/utils/mediaUrl'
import { defaultAvatarUrl } from '@/utils/defaultAvatar'

const props = withDefaults(
  defineProps<{
    src?: string
    alt?: string
    size?: 'hero' | 'lg' | 'md' | 'sm'
    shape?: 'square' | 'round'
  }>(),
  {
    src: defaultAvatarUrl(),
    alt: '个人头像',
    size: 'lg',
    shape: 'square',
  },
)

const displaySrc = computed(() => {
  const raw = props.src || ''
  if (!raw) return defaultAvatarUrl()
  return resolveMediaUrl(raw) || raw
})
</script>

<template>
  <img class="avatar-img" :class="[size, shape]" :src="displaySrc" :alt="alt" />
</template>

<style scoped>
.avatar-img {
  display: block;
  object-fit: cover;
  border-radius: var(--radius-avatar);
  border: 3px solid var(--color-accent-muted);
  box-shadow: var(--shadow-avatar);
  background: var(--color-surface-card);
}
.avatar-img.round {
  border-radius: 50%;
}
.avatar-img.hero {
  width: 100%;
  height: 100%;
  min-height: 100%;
  border-radius: 24px;
  border-width: 3px;
  border-color: var(--color-accent-secondary);
}
.avatar-img.hero.round {
  border-radius: 24px;
}
.avatar-img.lg {
  width: 140px;
  height: 140px;
}
.avatar-img.lg.round {
  border-radius: 50%;
}
.avatar-img.md {
  width: 120px;
  height: 120px;
}
.avatar-img.md.round {
  border-radius: 50%;
}
.avatar-img.sm {
  width: 56px;
  height: 56px;
  border-width: 2px;
}
.avatar-img.sm.round {
  border-radius: 50%;
}

@media (max-width: 768px) {
  .avatar-img.hero {
    border-radius: 20px;
  }
  .avatar-img.lg {
    width: 120px;
    height: 120px;
  }
}
</style>
