<script setup lang="ts">
import type { MusicTrack } from '@/data/musicTracks'

const props = defineProps<{
  open: boolean
  tracks: MusicTrack[]
  currentTrackId?: string
  loading?: boolean
}>()

const emit = defineEmits<{
  close: []
  select: [index: number]
  delete: [track: MusicTrack]
}>()

function onDelete(track: MusicTrack) {
  if (!confirm(`确定从列表移除「${track.title}」？`)) return
  emit('delete', track)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="playlist-drawer">
      <div v-if="open" class="playlist-root">
        <button type="button" class="playlist-backdrop" aria-label="关闭列表" @click="emit('close')" />
        <aside class="playlist-panel" role="dialog" aria-label="播放列表">
          <header class="playlist-head">
            <h3 class="playlist-title">播放列表</h3>
            <button type="button" class="playlist-close" aria-label="关闭" @click="emit('close')">
              ×
            </button>
          </header>
          <p v-if="loading" class="playlist-hint">加载中…</p>
          <p v-else-if="tracks.length === 0" class="playlist-hint">暂无曲目</p>
          <ul v-else class="playlist-list">
            <li
              v-for="(track, index) in tracks"
              :key="track.id"
              class="playlist-item"
              :class="{ active: track.id === currentTrackId }"
            >
              <button type="button" class="playlist-play" @click="emit('select', index)">
                <span class="playlist-name">{{ track.title }}</span>
                <span class="playlist-meta">
                  <span class="playlist-artist">{{ track.artist }}</span>
                  <span v-if="(track.playCount ?? 0) > 0" class="playlist-plays">
                    {{ track.playCount }} 次
                  </span>
                </span>
              </button>
              <button
                type="button"
                class="playlist-del"
                aria-label="删除"
                title="从列表移除"
                @click="onDelete(track)"
              >
                删
              </button>
            </li>
          </ul>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.playlist-root {
  position: fixed;
  inset: 0;
  z-index: 12000;
  display: flex;
  justify-content: flex-end;
}

.playlist-backdrop {
  position: absolute;
  inset: 0;
  border: none;
  background: rgba(8, 12, 24, 0.45);
  cursor: pointer;
}

.playlist-panel {
  position: relative;
  z-index: 1;
  width: min(320px, 88vw);
  height: 100%;
  padding: 1rem 0.85rem 1.25rem;
  background: linear-gradient(180deg, rgba(22, 32, 58, 0.97), rgba(14, 22, 42, 0.98));
  border-left: 1px solid rgba(140, 190, 255, 0.22);
  box-shadow: -12px 0 40px rgba(0, 0, 0, 0.35);
  display: flex;
  flex-direction: column;
}

.playlist-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.playlist-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: rgba(230, 240, 255, 0.95);
}

.playlist-close {
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(220, 235, 255, 0.9);
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
}

.playlist-hint {
  margin: 0.5rem 0;
  font-size: 0.85rem;
  color: rgba(180, 200, 230, 0.7);
}

.playlist-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  flex: 1;
}

.playlist-item {
  display: flex;
  align-items: stretch;
  gap: 0.35rem;
  margin-bottom: 0.4rem;
  border-radius: 10px;
  overflow: hidden;
}

.playlist-item.active {
  box-shadow: 0 0 0 1px rgba(120, 180, 255, 0.45);
}

.playlist-play {
  flex: 1;
  min-width: 0;
  padding: 0.55rem 0.65rem;
  border: none;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.playlist-item.active .playlist-play {
  background: rgba(80, 130, 220, 0.28);
}

.playlist-name {
  display: block;
  font-size: 0.88rem;
  font-weight: 600;
  color: rgba(235, 245, 255, 0.95);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.playlist-artist {
  display: block;
  font-size: 0.72rem;
  color: rgba(180, 200, 230, 0.75);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.playlist-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
  margin-top: 0.15rem;
}

.playlist-meta .playlist-artist {
  flex: 1;
  min-width: 0;
  margin-top: 0;
}

.playlist-plays {
  flex-shrink: 0;
  font-size: 0.65rem;
  color: rgba(140, 220, 180, 0.85);
}

.playlist-del {
  flex-shrink: 0;
  width: 2.25rem;
  border: 1px solid rgba(255, 120, 120, 0.35);
  border-radius: 10px;
  background: rgba(120, 40, 40, 0.35);
  color: rgba(255, 200, 200, 0.95);
  font-size: 0.72rem;
  cursor: pointer;
}

.playlist-del:hover {
  background: rgba(160, 50, 50, 0.55);
}

.playlist-drawer-enter-active,
.playlist-drawer-leave-active {
  transition: opacity 0.25s ease;
}

.playlist-drawer-enter-active .playlist-panel,
.playlist-drawer-leave-active .playlist-panel {
  transition: transform 0.28s cubic-bezier(0.32, 0.72, 0, 1);
}

.playlist-drawer-enter-from,
.playlist-drawer-leave-to {
  opacity: 0;
}

.playlist-drawer-enter-from .playlist-panel,
.playlist-drawer-leave-to .playlist-panel {
  transform: translateX(100%);
}
</style>
