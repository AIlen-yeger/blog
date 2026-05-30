<script setup lang="ts">
import { computed, Teleport, watch } from 'vue'
import QqMusicEmbed from '@/components/QqMusicEmbed.vue'
import {
  applyQqTeleportSlot,
  globalQqNext,
  qqTeleportTo,
  useGlobalQqPlayer,
} from '@/composables/useGlobalQqPlayer'

const {
  teleportSlot,
  songId,
  active,
  currentTrack,
  markQqPlaying,
} = useGlobalQqPlayer()

/** 着陆页在面板内直接渲染 iframe；此处仅负责 about / 屏外续播 */
const useTeleport = computed(
  () => active.value && !!songId.value && teleportSlot.value !== 'landing',
)

watch(teleportSlot, () => {
  void applyQqTeleportSlot(teleportSlot.value)
})

watch(songId, (id) => {
  if (id) markQqPlaying(true)
})
</script>

<template>
  <Teleport v-if="useTeleport" :to="qqTeleportTo">
    <div
      class="qq-persistent-embed"
      @pointerdown="markQqPlaying(true)"
    >
      <QqMusicEmbed
        :song-id="songId"
        :duration-sec="currentTrack?.durationSec"
        @ended="globalQqNext()"
      />
    </div>
  </Teleport>
</template>

<style scoped>
.qq-persistent-embed {
  width: 100%;
  display: flex;
  justify-content: center;
}
</style>
