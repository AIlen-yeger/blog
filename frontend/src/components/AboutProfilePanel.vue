<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ProfileData } from '@/data/mockContent'
import AvatarImage from './AvatarImage.vue'
import MusicParticles from './MusicParticles.vue'
import MusicPlaylistDrawer from './MusicPlaylistDrawer.vue'
import { useAboutMusic } from '@/composables/useAboutMusic'
import { aboutDisplayParticleTheme } from '@/data/musicTracks'
import {
  markQqPlaying,
  setQqTeleportSlot,
} from '@/composables/useGlobalQqPlayer'
import { removeMusicTrack } from '@/composables/useUserMusicTracks'

defineProps<{
  profile: ProfileData
  showEdit?: boolean
}>()

const emit = defineEmits<{
  edit: []
}>()

const {
  musicMode,
  tracks,
  currentTrack,
  isQqTrack,
  qqBackgroundActive,
  embedPlaybackActive,
  visualPlaybackActive,
  isPlaying,
  progressPercent,
  timeLabel,
  loadError,
  toggleMusicMode,
  togglePlayPause,
  stopAndReset,
  prevTrack,
  nextTrack,
  seekByPercent,
  selectTrackById,
} = useAboutMusic()

const playlistOpen = ref(false)

const playlistTracks = computed(() => tracks.value.filter((t) => !!t.qqSongId))

function onProgressInput(e: Event) {
  seekByPercent(Number((e.target as HTMLInputElement).value))
}

function onStop() {
  stopAndReset()
}

function openPlaylist() {
  playlistOpen.value = true
}

function onSelectPlaylist(index: number) {
  const track = playlistTracks.value[index]
  if (!track) return
  selectTrackById(track.id)
  markQqPlaying(true)
  setQqTeleportSlot(musicMode.value ? 'about' : 'hidden')
  playlistOpen.value = false
}

function onUserPlayPause() {
  togglePlayPause()
}

async function onDeletePlaylist(track: (typeof playlistTracks.value)[0]) {
  await removeMusicTrack(track)
  playlistOpen.value = false
}
</script>

<template>
  <div
    class="about-panel"
    :class="{
      'is-music': musicMode,
      'is-playing-bg': visualPlaybackActive && !musicMode,
    }"
  >
    <div class="about-panel-bg" aria-hidden="true" />
    <MusicParticles
      :active="visualPlaybackActive"
      :ambient-motion="embedPlaybackActive && !isPlaying"
      :theme="aboutDisplayParticleTheme"
      :lyrics-fall="false"
    />

    <div class="profile-identity">
      <AvatarImage :src="profile.avatarUrl" size="lg" shape="round" class="profile-avatar" />
      <h3 class="profile-name">{{ profile.name }}</h3>
      <p class="profile-sub">{{ profile.subtitle }}</p>
      <p class="profile-bio">{{ profile.bio }}</p>
      <ul class="focus-tags">
        <li v-for="tag in profile.focus" :key="tag">{{ tag }}</li>
      </ul>
      <button
        v-if="showEdit"
        type="button"
        class="btn-edit-profile btn-edit-profile--identity"
        @click="emit('edit')"
      >
        编辑个人资料
      </button>
    </div>

    <div class="panel-bottom">
      <div class="profile-actions" :class="{ 'panel-view--hidden': musicMode }">
          <div v-if="isPlaying || qqBackgroundActive" class="bg-music-bar">
            <span class="bg-music-title">{{ currentTrack?.title }}</span>
            <span class="bg-music-meta">
              {{ currentTrack?.artist }} ·
              {{ qqBackgroundActive ? 'QQ 音乐后台播放中' : '后台播放中' }}
            </span>
            <div class="bg-music-actions">
              <button type="button" class="bg-music-btn" title="暂停" @click="onUserPlayPause">
                ⏸
              </button>
              <button type="button" class="bg-music-btn" title="打开播放器" @click="toggleMusicMode">
                播放器
              </button>
              <button type="button" class="bg-music-btn bg-music-stop" title="停止" @click="onStop">
                ⏹
              </button>
            </div>
          </div>
        </div>

        <div class="music-player" :class="{ 'panel-view--hidden': !musicMode }">
          <p class="track-title">{{ currentTrack?.title ?? '未选择曲目' }}</p>
          <p class="track-artist">{{ currentTrack?.artist }}</p>

          <div
            v-if="isQqTrack && musicMode"
            id="about-qq-slot"
            class="qq-embed-host"
          />

          <div v-if="!isQqTrack" class="progress-row">
            <input
              type="range"
              class="progress-bar"
              min="0"
              max="100"
              step="0.1"
              :value="progressPercent"
              aria-label="播放进度"
              @input="onProgressInput"
            />
            <span class="time-text">{{ timeLabel }}</span>
          </div>

          <div class="controls">
            <button type="button" class="ctrl-btn" title="播放列表" @click="openPlaylist">
              ☰
            </button>
            <button type="button" class="ctrl-btn" title="上一首" @click="prevTrack">
              ⏮
            </button>
            <button
              v-if="!isQqTrack"
              type="button"
              class="ctrl-btn ctrl-main"
              :title="isPlaying ? '暂停' : '播放'"
              @click="onUserPlayPause"
            >
              {{ isPlaying ? '⏸' : '▶' }}
            </button>
            <span v-else class="ctrl-qq-hint" title="请在下方 QQ 音乐播放器中操作">
              QQ
            </span>
            <button type="button" class="ctrl-btn" title="下一首" @click="nextTrack()">
              ⏭
            </button>
            <button type="button" class="ctrl-btn ctrl-stop" title="停止" @click="onStop">
              ⏹
            </button>
          </div>

          <p v-if="loadError" class="blog-alert blog-alert--error music-err" role="alert">
            <span class="blog-alert__icon" aria-hidden="true">!</span>
            <span>{{ loadError }}</span>
          </p>
          <p v-else-if="isQqTrack" class="music-tip">
            由 QQ 音乐官方播放器提供；登录后可通过 Kohaku 发送分享链接添加曲目
          </p>
          <p v-else class="music-tip">
            将 mp3 放入 <code>public/music/</code> 后重启
            <code>npm run dev</code>，会自动识别曲目（文件名建议：歌手 - 歌名.mp3）
          </p>
        </div>
    </div>

    <button
      type="button"
      class="vinyl-trigger vinyl-float"
      :class="{ active: musicMode, 'is-audio-playing': visualPlaybackActive }"
      :aria-label="musicMode ? '返回资料视图' : '打开音乐播放'"
      :title="musicMode ? '返回资料视图' : '点击播放音乐'"
      @click="toggleMusicMode"
    >
      <span class="vinyl-hint">{{ musicMode ? '返回资料' : '点击唱片' }}</span>
      <span class="vinyl">
        <span
          class="vinyl-rotor"
          :class="{ 'is-playing': visualPlaybackActive }"
        >
          <span class="vinyl-disc" />
          <span class="vinyl-label">MUSIC</span>
          <span class="vinyl-center" />
        </span>
      </span>
    </button>

    <MusicPlaylistDrawer
      :open="playlistOpen"
      :tracks="playlistTracks"
      :current-track-id="currentTrack?.id"
      @close="playlistOpen = false"
      @select="onSelectPlaylist"
      @delete="onDeletePlaylist"
    />
  </div>
</template>

<style scoped>
.about-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 0.5rem 0 0.5rem;
  min-height: 18rem;
  border-radius: 20px;
  overflow: hidden;
  isolation: isolate;
  transition: color 0.65s cubic-bezier(0.4, 0, 0.2, 1);
}

.about-panel-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: transparent;
  transition: background 0.85s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.85s ease;
  pointer-events: none;
}

.about-panel.is-playing-bg .about-panel-bg {
  background: linear-gradient(
    145deg,
    rgba(26, 16, 53, 0.55) 0%,
    rgba(45, 27, 78, 0.4) 50%,
    rgba(30, 58, 95, 0.35) 100%
  );
  opacity: 1;
}

.about-panel.is-music .about-panel-bg {
  background: linear-gradient(
    145deg,
    #1a1035 0%,
    #2d1b4e 35%,
    #3d2a6b 55%,
    #1e3a5f 100%
  );
  opacity: 1;
}

.about-panel.is-music .about-panel-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(
    circle at 30% 20%,
    rgba(147, 112, 219, 0.35),
    transparent 55%
  );
  animation: bg-glow 8s ease-in-out infinite alternate;
}

@keyframes bg-glow {
  from {
    opacity: 0.6;
    transform: scale(1);
  }
  to {
    opacity: 1;
    transform: scale(1.08);
  }
}

.profile-identity {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  pointer-events: none;
}

.profile-identity .btn-edit-profile--identity {
  pointer-events: auto;
  margin-top: 1rem;
}

.btn-edit-profile--identity {
  position: relative;
  z-index: 2;
}

.profile-identity :deep(.profile-avatar) {
  transition: box-shadow 0.65s ease;
}

.about-panel.is-music .profile-identity :deep(.profile-avatar) {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
}

.profile-name {
  margin-top: 1.1rem;
  font-size: 1.65rem;
  font-weight: 700;
  color: var(--color-text);
  transition: color 0.65s ease;
}

.profile-sub {
  margin-top: 0.25rem;
  font-size: 0.82rem;
  letter-spacing: 0.12em;
  color: var(--color-text-muted);
  text-transform: uppercase;
  transition: color 0.65s ease;
}

.profile-bio {
  margin-top: 1rem;
  max-width: 480px;
  line-height: 1.65;
  color: var(--color-text-muted);
  font-size: 0.95rem;
  transition: color 0.65s ease;
}

.about-panel.is-music .profile-name,
.about-panel.is-music .profile-sub,
.about-panel.is-music .profile-bio {
  color: rgba(236, 240, 255, 0.95);
}

.about-panel.is-music .profile-sub {
  color: rgba(200, 210, 240, 0.75);
}

.focus-tags {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1.25rem;
  padding: 0;
}

.focus-tags li {
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  background: #dbeafe;
  border: 1px solid var(--color-accent-light);
  font-size: 0.82rem;
  color: var(--color-accent-dark);
  font-weight: 500;
  transition: background 0.65s ease, color 0.65s ease, border-color 0.65s ease;
}

.about-panel.is-music .focus-tags li {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.22);
  color: rgba(230, 235, 255, 0.95);
}

.vinyl-trigger {
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  transition: transform 0.35s cubic-bezier(0.34, 1.4, 0.64, 1);
}

.vinyl-float {
  position: absolute;
  z-index: 20;
  top: 0.15rem;
  right: 0.35rem;
  flex-direction: row-reverse;
  padding: 0.35rem;
  min-width: 2.75rem;
  min-height: 2.75rem;
}

.vinyl-trigger:hover {
  transform: scale(1.05);
}

.vinyl-trigger.active {
  transform: scale(1.03);
}

.about-panel.is-music .vinyl-float {
  top: 0.35rem;
  filter: drop-shadow(0 6px 18px rgba(120, 80, 200, 0.35));
}

.vinyl {
  position: relative;
  width: 76px;
  height: 76px;
  flex-shrink: 0;
}

.vinyl-rotor {
  position: relative;
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  transform: rotate(0deg);
}

.vinyl-rotor.is-playing {
  animation: vinyl-spin 2.4s linear infinite;
}

.vinyl-disc {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: repeating-radial-gradient(
      circle at center,
      #0f0f12 0px,
      #0f0f12 2px,
      #1a1a22 3px,
      #1a1a22 4px
    ),
    linear-gradient(145deg, #1c1c24, #2a2a34);
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.35),
    inset 0 0 0 3px rgba(255, 255, 255, 0.06);
}

.vinyl-trigger.is-audio-playing .vinyl-disc,
.vinyl-trigger.active .vinyl-disc {
  box-shadow:
    0 10px 32px rgba(120, 80, 200, 0.45),
    inset 0 0 0 3px rgba(200, 180, 255, 0.15);
}

@keyframes vinyl-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.vinyl-label {
  position: relative;
  z-index: 1;
  font-size: 0.55rem;
  font-weight: 800;
  letter-spacing: 0.2em;
  color: rgba(255, 255, 255, 0.35);
  pointer-events: none;
}

.vinyl-center {
  position: relative;
  z-index: 2;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #6b4c9a, #2a1848);
  border: 2px solid rgba(255, 255, 255, 0.2);
  box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.4);
  pointer-events: none;
}

.vinyl-hint {
  font-size: 0.72rem;
  color: var(--color-text-muted);
  white-space: nowrap;
  opacity: 0;
  transform: translateX(8px);
  pointer-events: none;
  transition:
    opacity 0.3s ease,
    transform 0.3s ease,
    color 0.65s ease;
}

.vinyl-trigger:hover .vinyl-hint,
.vinyl-trigger:focus-visible .vinyl-hint,
.vinyl-trigger.active .vinyl-hint {
  opacity: 1;
  transform: translateX(0);
}

.about-panel.is-music .vinyl-hint {
  color: rgba(220, 215, 255, 0.85);
}

@media (max-width: 640px) {
  .vinyl-float {
    top: auto;
    bottom: 7.25rem;
    right: 0.5rem;
    flex-direction: column-reverse;
    gap: 0.35rem;
  }

  .vinyl {
    width: 68px;
    height: 68px;
  }

  .vinyl-hint {
    display: none;
  }
}

.panel-bottom {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  min-height: 7.5rem;
  margin-top: 1.25rem;
}

.panel-view--hidden {
  visibility: hidden;
  height: 0;
  min-height: 0;
  margin: 0;
  padding: 0;
  overflow: hidden;
  pointer-events: none;
  opacity: 0;
}

.qq-embed-host--offscreen {
  position: fixed;
  left: -10000px;
  top: 0;
  width: 330px;
  height: 86px;
  margin: 0;
  opacity: 0;
  pointer-events: none;
  overflow: hidden;
}

.profile-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.85rem;
  padding-top: 0.5rem;
  width: 100%;
}

.bg-music-bar {
  width: 100%;
  max-width: 360px;
  padding: 0.75rem 1rem;
  border-radius: 14px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.22);
  text-align: left;
}

.bg-music-title {
  display: block;
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--color-text);
}

.bg-music-meta {
  display: block;
  margin-top: 0.2rem;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.bg-music-actions {
  display: flex;
  gap: 0.45rem;
  margin-top: 0.6rem;
}

.bg-music-btn {
  padding: 0.35rem 0.7rem;
  border-radius: 8px;
  border: 1px solid rgba(59, 130, 246, 0.3);
  background: var(--color-surface-elevated);
  color: var(--color-accent-dark);
  font-size: 0.78rem;
  cursor: pointer;
  transition: background 0.2s;
}

.bg-music-btn:hover {
  background: #dbeafe;
}

.bg-music-stop {
  margin-left: auto;
}

.btn-edit-profile {
  padding: 0.6rem 1.35rem;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, #2563eb, #60a5fa);
  color: #fff;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.35);
  transition: transform 0.15s, box-shadow 0.15s;
}

.about-panel.is-music .btn-edit-profile {
  box-shadow: 0 4px 20px rgba(80, 60, 160, 0.5);
}

.btn-edit-profile:hover {
  transform: translateY(-1px);
}

.music-player {
  padding: 1rem 1.1rem 0.25rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
}

.track-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #fff;
}

.track-artist {
  margin: 0.2rem 0 0.85rem;
  font-size: 0.82rem;
  color: rgba(210, 205, 255, 0.75);
}

.progress-row {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.progress-bar {
  width: 100%;
  height: 6px;
  appearance: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.15);
  cursor: pointer;
}

.progress-bar::-webkit-slider-thumb {
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #a78bfa;
  box-shadow: 0 0 8px rgba(167, 139, 250, 0.8);
}

.progress-bar::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border: none;
  border-radius: 50%;
  background: #a78bfa;
}

.progress-bar--read {
  height: 6px;
  appearance: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.15);
  overflow: hidden;
  cursor: default;
}

.progress-bar-fill {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #7c3aed, #a78bfa);
  transition: width 0.35s linear;
}

.time-text {
  font-size: 0.78rem;
  color: rgba(220, 215, 255, 0.7);
  font-variant-numeric: tabular-nums;
}

.controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.65rem;
  margin-top: 1rem;
}

.ctrl-btn {
  width: 2.5rem;
  height: 2.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background 0.2s, transform 0.15s;
}

.ctrl-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.05);
}

.ctrl-order {
  display: grid;
  place-items: center;
  padding: 0;
}

.ctrl-order.is-shuffle,
.ctrl-order.is-sequential {
  background: rgba(167, 139, 250, 0.28);
  border-color: rgba(196, 181, 253, 0.45);
}

.ctrl-order-icon {
  width: 1.05rem;
  height: 1.05rem;
}

.ctrl-main {
  width: 3rem;
  height: 3rem;
  font-size: 1.1rem;
  background: linear-gradient(135deg, #7c3aed, #a78bfa);
  border: none;
  box-shadow: 0 6px 20px rgba(124, 58, 237, 0.45);
}

.ctrl-stop {
  font-size: 0.85rem;
}

.ctrl-qq-hint {
  display: grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.12);
  border: 1px dashed rgba(255, 255, 255, 0.28);
}

.music-err {
  margin: 0.75rem 0 0;
  align-items: center;
  font-size: 0.8rem;
}

.music-tip {
  margin: 0.65rem 0 0;
  font-size: 0.72rem;
  color: rgba(200, 195, 230, 0.55);
}

.music-tip code {
  font-size: 0.7rem;
  color: rgba(230, 225, 255, 0.75);
}

.bottom-fade-enter-active,
.bottom-fade-leave-active {
  transition: opacity 0.45s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.45s cubic-bezier(0.4, 0, 0.2, 1);
}

.bottom-fade-enter-from,
.bottom-fade-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
</style>
