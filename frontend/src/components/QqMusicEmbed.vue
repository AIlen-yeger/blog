<script setup lang="ts">
import { computed, toRef } from 'vue'
import { buildQqMusicPlayerUrl } from '@/utils/qqMusicEmbed'
import { useQqEmbedAutoAdvance } from '@/composables/useQqEmbedAutoAdvance'

const props = withDefaults(
  defineProps<{
    songId: string
    songtype?: string
    /** 曲目时长（秒），用于结束后自动切歌 */
    durationSec?: number
    /** 是否启用播放结束自动切下一首 */
    autoAdvance?: boolean
  }>(),
  {
    autoAdvance: true,
  },
)

const emit = defineEmits<{
  ended: []
}>()

const embedSrc = computed(() =>
  buildQqMusicPlayerUrl(props.songId, props.songtype ?? '0'),
)

const durationRef = computed(() => props.durationSec)
const enabledRef = computed(() => props.autoAdvance && (props.durationSec ?? 0) > 0)
const songIdRef = toRef(props, 'songId')

useQqEmbedAutoAdvance({
  songId: songIdRef,
  durationSec: durationRef,
  enabled: enabledRef,
  onEnded: () => emit('ended'),
})
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
  background: rgba(255, 255, 255, 0.12);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  opacity: 0.88;
  filter: brightness(1.1) saturate(0.9);
}
</style>
