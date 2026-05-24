<script setup lang="ts">
import { computed } from 'vue'
import { resolveMediaUrl } from '@/utils/mediaUrl'

const props = defineProps<{
  images?: string[]
  compact?: boolean
}>()

const list = computed(() => (props.images ?? []).filter(Boolean))
</script>

<template>
  <div v-if="list.length" class="gallery" :class="{ compact }">
    <a
      v-for="(url, i) in list"
      :key="url + i"
      class="gallery-item"
      :href="resolveMediaUrl(url)"
      target="_blank"
      rel="noopener noreferrer"
      @click.stop
    >
      <img :src="resolveMediaUrl(url)" :alt="`配图 ${i + 1}`" loading="lazy" />
    </a>
  </div>
</template>

<style scoped>
.gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.65rem;
  margin-top: 1rem;
}

.gallery.compact {
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 0.5rem;
  margin-top: 0.65rem;
}

.gallery-item {
  display: block;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(59, 130, 246, 0.15);
  aspect-ratio: 4 / 3;
  background: var(--color-surface-elevated);
  transition: transform 0.15s, box-shadow 0.15s;
}

.gallery-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(30, 45, 60, 0.12);
}

.gallery-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
