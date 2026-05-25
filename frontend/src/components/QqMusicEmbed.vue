<script setup lang="ts">
import { computed } from 'vue'
import { buildQqMusicPlayerUrl } from '@/utils/qqMusicEmbed'

const props = defineProps<{
  songId: string
  songtype?: string
}>()

const embedSrc = computed(() =>
  buildQqMusicPlayerUrl(props.songId, props.songtype ?? '0'),
)
</script>

<template>
  <div class="qq-music-embed">
    <iframe
      :key="embedSrc"
      class="qq-music-embed__frame"
      :src="embedSrc"
      frameborder="0"
      marginwidth="0"
      marginheight="0"
      width="330"
      height="86"
      allow="autoplay"
      loading="lazy"
      title="QQ音乐播放器"
    />
  </div>
</template>

<style scoped>
.qq-music-embed {
  width: 100%;
  display: flex;
  justify-content: center;
  margin: 0.15rem 0 0.65rem;
}

.qq-music-embed__frame {
  width: 100%;
  max-width: 330px;
  height: 86px;
  border: none;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.2);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}
</style>
