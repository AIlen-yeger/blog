<script setup lang="ts">
import { useAboutMusic } from '@/composables/useAboutMusic'

const { bindAudio } = useAboutMusic()
</script>

<template>
  <!-- 挂在 App 根节点；刷新后从 localStorage 恢复进度并尝试续播 -->
  <audio
    :ref="(el) => bindAudio(el as HTMLAudioElement | null)"
    class="music-audio-host"
    preload="metadata"
  />
</template>

<style scoped>
.music-audio-host {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}
</style>
