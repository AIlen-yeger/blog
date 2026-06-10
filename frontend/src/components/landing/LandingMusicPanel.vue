<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, onUnmounted, ref, watch } from 'vue'
import MusicPlaylistDrawer from '@/components/MusicPlaylistDrawer.vue'
import QqMusicEmbed from '@/components/QqMusicEmbed.vue'
import { syncGlobalMusicTrackId } from '@/composables/useAboutMusic'
import {
  applyQqTeleportSlot,
  globalQqNext,
  globalQqPrev,
  globalQqSelectIndex,
  hydrateGlobalQqFromStorage,
  markQqPlaying,
  setGlobalQqTracks,
  syncQqTeleportSlot,
  useGlobalQqPlayer,
} from '@/composables/useGlobalQqPlayer'
import {
  landingMusicTracks,
  landingMusicLoading,
  loadLandingMusicTracks,
  MUSIC_TRACKS_CHANGED,
  removeMusicTrack,
} from '@/composables/useUserMusicTracks'
import { aboutMusicTracks, isQqMusicTrack } from '@/data/musicTracks'

const landingSongId = import.meta.env.VITE_LANDING_QQ_SONG_ID as string | undefined
const playlistOpen = ref(false)
const panelAlive = ref(true)

const landingTracks = computed(() => {
  const fromApi = landingMusicTracks.value.filter((t) => isQqMusicTrack(t))
  if (fromApi.length > 0) return fromApi
  return aboutMusicTracks.filter((t) => isQqMusicTrack(t))
})

const { trackIndex, currentTrack, songId, teleportSlot } = useGlobalQqPlayer()

/** 着陆页展示用：优先 API 列表，避免全局状态与本地列表不一致 */
const displaySongId = computed(() => {
  const fromList = landingTracks.value[trackIndex.value]?.qqSongId
  if (fromList) return fromList
  return songId.value
})

const displayDuration = computed(
  () => landingTracks.value[trackIndex.value]?.durationSec ?? currentTrack.value?.durationSec,
)

const showLandingEmbed = computed(
  () => !!displaySongId.value && teleportSlot.value !== 'hidden',
)

function fallbackIndex() {
  const tracks = landingTracks.value
  if (tracks.length === 0) return 0
  const fromEnv = landingSongId?.trim()
  if (fromEnv) {
    const i = tracks.findIndex((t) => t.qqSongId === fromEnv)
    if (i >= 0) return i
  }
  return 0
}

async function refreshTracks() {
  if (!panelAlive.value) return
  await loadLandingMusicTracks()
  if (!panelAlive.value) return
  const list = landingTracks.value
  setGlobalQqTracks(list)
  if (list.length > 0 && trackIndex.value >= list.length) {
    trackIndex.value = 0
  }
  hydrateGlobalQqFromStorage(list)
  if (trackIndex.value === 0 && list.length > 0) {
    const fb = fallbackIndex()
    if (fb > 0) trackIndex.value = fb
  }
  syncQqTeleportSlot('landing')
  void applyQqTeleportSlot('landing')
}

onMounted(() => {
  void refreshTracks()
  window.addEventListener(MUSIC_TRACKS_CHANGED, onTracksChanged)
  window.addEventListener('auth:logout', onTracksChanged)
})

onBeforeUnmount(() => {
  panelAlive.value = false
  playlistOpen.value = false
  syncQqTeleportSlot('hidden')
})

onUnmounted(() => {
  window.removeEventListener(MUSIC_TRACKS_CHANGED, onTracksChanged)
  window.removeEventListener('auth:logout', onTracksChanged)
})

function onTracksChanged() {
  void refreshTracks()
}

watch(landingTracks, (list) => {
  if (!panelAlive.value) return
  setGlobalQqTracks(list)
  if (trackIndex.value >= list.length) trackIndex.value = 0
})

const trackLabel = computed(() => {
  const t = currentTrack.value
  if (!t) return 'QQ 音乐'
  const base = `${t.title} · ${t.artist}`
  const n = t.playCount ?? landingTracks.value.find((x) => x.id === t.id)?.playCount
  if (n && n > 0) return `${base} · ${n} 次`
  return base
})

const canSwitch = computed(() => landingTracks.value.length > 1)

watch(
  () => currentTrack.value?.id,
  (id) => {
    if (id) void syncGlobalMusicTrackId(id)
  },
  { immediate: true },
)

function prevTrack() {
  globalQqPrev()
  markQqPlaying(true)
}

/** 用户点击「下一首」 */
function nextTrackByUser() {
  globalQqNext()
  markQqPlaying(true)
}

/** 曲目时长结束自动切歌（不计入播放次数） */
function nextTrackAuto() {
  globalQqNext()
  markQqPlaying(true)
}

function openPlaylist() {
  playlistOpen.value = true
}

async function onDeleteTrack(track: (typeof landingTracks.value)[0]) {
  await removeMusicTrack(track)
  playlistOpen.value = false
}

function onSelectTrack(index: number) {
  globalQqSelectIndex(index)
  markQqPlaying(true)
  playlistOpen.value = false
}

function onEmbedInteract() {
  markQqPlaying(true)
}
</script>

<template>
  <section class="landing-music" aria-label="音乐播放器">
    <header class="music-head">
      <p class="music-label" :title="trackLabel">{{ trackLabel }}</p>
      <div class="music-actions">
        <button type="button" class="nav-btn list-btn" aria-label="播放列表" title="播放列表" @click="openPlaylist">
          ☰
        </button>
        <div v-if="canSwitch" class="music-nav" role="group" aria-label="切换曲目">
          <button type="button" class="nav-btn" aria-label="上一首" @click="prevTrack">‹</button>
          <button type="button" class="nav-btn" aria-label="下一首" @click="nextTrackByUser">›</button>
        </div>
      </div>
    </header>
    <div id="landing-qq-slot" class="music-embed-wrap" @pointerdown="onEmbedInteract">
      <QqMusicEmbed
        v-if="showLandingEmbed"
        :key="displaySongId"
        :song-id="displaySongId"
        :duration-sec="displayDuration"
        @ended="nextTrackAuto"
      />
      <p v-else-if="landingMusicLoading" class="music-empty">加载曲目中…</p>
      <p v-else class="music-empty">暂无曲目，登录后可通过蕾西亚添加</p>
    </div>

    <MusicPlaylistDrawer
      :open="playlistOpen"
      :tracks="landingTracks"
      :current-track-id="currentTrack?.id"
      @close="playlistOpen = false"
      @select="onSelectTrack"
      @delete="onDeleteTrack"
    />
  </section>
</template>

<style scoped>
.landing-music {
  flex: 1.35;
  min-width: 0;
  padding: 0.4rem 0.5rem 0.35rem;
  border-radius: 14px;
  background: rgba(32, 52, 88, 0.24);
  border: 1px solid rgba(150, 195, 255, 0.24);
  -webkit-backdrop-filter: blur(7px);
  backdrop-filter: blur(7px);
  display: flex;
  flex-direction: column;
}

.music-head {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 0.35rem;
  min-width: 0;
}

.music-label {
  margin: 0;
  flex: 1;
  min-width: 0;
  font-size: 0.72rem;
  color: rgba(186, 210, 240, 0.75);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.music-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}

.music-nav {
  display: flex;
  gap: 0.25rem;
}

.nav-btn {
  width: 1.65rem;
  height: 1.65rem;
  padding: 0;
  border: 1px solid rgba(120, 170, 255, 0.22);
  border-radius: 8px;
  background: rgba(40, 68, 115, 0.45);
  color: rgba(220, 240, 255, 0.9);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  transition:
    background 0.2s ease,
    border-color 0.2s ease;
}

.list-btn {
  font-size: 0.85rem;
}

.nav-btn:hover {
  background: rgba(40, 80, 140, 0.65);
  border-color: rgba(140, 200, 255, 0.4);
}

.music-embed-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 12px;
  background: rgba(18, 32, 58, 0.22);
  position: relative;
  min-height: 62px;
}

.music-embed-wrap :deep(.qq-music-embed) {
  margin: 0;
  width: 100%;
}

.music-embed-wrap :deep(.qq-music-embed__frame) {
  max-width: 100%;
  height: 62px;
  border-radius: 8px;
  opacity: 0.9;
  filter: brightness(1.12) saturate(0.88);
}

.music-empty {
  margin: 0;
  font-size: 0.68rem;
  color: rgba(180, 205, 235, 0.65);
  text-align: center;
  padding: 0.5rem;
}

@media (max-width: 767px) {
  .landing-music {
    padding: 0.35rem 0.45rem;
    flex: 1 1 auto;
    width: 100%;
    min-height: 5.5rem;
  }
  .music-label {
    font-size: 0.68rem;
  }
  .nav-btn {
    width: 1.85rem;
    height: 1.85rem;
    min-width: 44px;
    min-height: 44px;
  }
  .music-embed-wrap {
    min-height: 62px;
    flex-shrink: 0;
  }
  .music-embed-wrap :deep(.qq-music-embed__frame) {
    height: 62px;
    min-height: 62px;
  }
}

@media (max-width: 520px) {
  .music-head {
    flex-wrap: wrap;
  }
  .music-label {
    width: 100%;
    margin-bottom: 0.15rem;
  }
}

</style>
