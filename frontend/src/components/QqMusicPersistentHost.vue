<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
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

const alive = ref(true)

/** 着陆页在面板内直接渲染 iframe；此处仅负责 about / 屏外续播 */
const useTeleport = computed(
  () => alive.value && active.value && !!songId.value && teleportSlot.value !== 'landing',
)

/** Teleport 目标必须存在于 DOM，否则 Vue 会报 nextSibling / emitsOptions 错 */
const teleportTarget = computed(() => {
  const sel = qqTeleportTo.value
  if (typeof document !== 'undefined') {
    try {
      if (document.querySelector(sel)) return sel
    } catch {
      /* 非法 selector */
    }
  }
  return '#qq-music-offscreen'
})

watch(teleportSlot, () => {
  if (!alive.value) return
  void applyQqTeleportSlot(teleportSlot.value)
})

watch(songId, (id) => {
  if (!alive.value) return
  if (id) markQqPlaying(true)
})

onBeforeUnmount(() => {
  alive.value = false
})
</script>

<template>
  <Teleport v-if="useTeleport" :to="teleportTarget">
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
