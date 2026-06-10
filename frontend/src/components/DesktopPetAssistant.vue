<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useDesktopPetChat } from '@/composables/useDesktopPetChat'
import { useDesktopPetPosition } from '@/composables/useDesktopPetPosition'
import { useDesktopPetScale } from '@/composables/useDesktopPetScale'
import { useDesktopPetSprite } from '@/composables/useDesktopPetSprite'
import { PET_SPRITE_STAGE } from '@/data/desktopPetLayout'
import { petSpriteFallback } from '@/utils/petSpriteSrc'
import { navigateToAgentChat } from '@/utils/agentRoute'

const { loggedIn: loggedInProp } = defineProps<{
  loggedIn?: boolean
}>()

const emit = defineEmits<{
  'request-login': []
}>()

const isLoggedIn = () => loggedInProp === true

const spriteStageStyle = {
  width: `${PET_SPRITE_STAGE.width}px`,
  height: `${PET_SPRITE_STAGE.height}px`,
}

const rootRef = ref<HTMLElement | null>(null)
const chatOpen = ref(false)

const {
  history,
  input,
  isStreaming,
  historyOpen,
  error,
  loginRequired,
  displayText,
  bubbleTier,
  hasHistory,
  toggleHistory,
  sendMessage,
  stopStreaming,
  clearError,
  clearHistory,
} = useDesktopPetChat()

const messageBodyRef = ref<HTMLElement | null>(null)

function scrollMessageToBottom() {
  const el = messageBodyRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

watch([displayText, isStreaming, bubbleTier], () => {
  if (bubbleTier.value !== 'scroll') return
  void nextTick(scrollMessageToBottom)
})

const { currentSprite, setChatOpen } = useDesktopPetSprite()

function toggleChatOpen() {
  chatOpen.value = !chatOpen.value
}

const { posX, posY, dragging, measureAndPlace, onPointerDown, onPointerMove, onPointerUp } =
  useDesktopPetPosition(rootRef, toggleChatOpen)

const { spriteScale, onAvatarWheel } = useDesktopPetScale()

const scaledStyle = () => ({
  transform: `scale(${spriteScale.value})`,
})

watch(chatOpen, (open) => setChatOpen(open), { immediate: true })

watch(spriteScale, () => {
  void nextTick(() => measureAndPlace(false))
})


function onSubmit() {
  void sendMessage({
    isLoggedIn,
    onLoginRequired: () => emit('request-login'),
  })
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    void sendMessage({
      isLoggedIn,
      onLoginRequired: () => emit('request-login'),
    })
  }
}

const spriteMatteHint = ref(false)

const spriteImgStyle = computed(() => {
  const scale = currentSprite.value.fitScale ?? 1
  return {
    transform: scale === 1 ? undefined : `scale(${scale})`,
    transformOrigin: 'center bottom',
  }
})

onMounted(() => {
  requestAnimationFrame(() => measureAndPlace(false))
})

function onSpriteLoad() {
  spriteMatteHint.value = /\.jpe?g(\?|$)/i.test(currentSprite.value.src)
}

function openAgentPage() {
  navigateToAgentChat()
}

function onSpriteError(e: Event) {
  const img = e.target as HTMLImageElement
  const fallback = petSpriteFallback(currentSprite.value.src)
  if (fallback && img.src !== fallback) {
    img.src = fallback
    spriteMatteHint.value = true
    return
  }
  img.style.opacity = '0.35'
}
</script>

<template>
  <div
    ref="rootRef"
    class="pet-assistant"
    :class="{ 'is-dragging': dragging, 'is-chat-open': chatOpen }"
    :style="{ left: `${posX}px`, top: `${posY}px` }"
    aria-label="桌宠助手"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
  >
    <div class="pet-assistant__scaled" :style="scaledStyle()">
      <div class="pet-assistant__body" :style="spriteStageStyle">
        <Transition name="pet-chat">
          <div
            v-show="chatOpen"
            class="pet-assistant__speech"
            :class="[`pet-assistant__speech--${bubbleTier}`, { 'is-streaming': isStreaming }]"
            @click.stop
            @wheel.stop
          >
          <div class="pet-assistant__qq-head">
            <span class="pet-assistant__name">蕾西亚</span>
            <div class="pet-assistant__head-actions">
              <button
                type="button"
                class="pet-assistant__expand-btn"
                title="全屏对话"
                aria-label="进入全屏对话"
                @click.stop="openAgentPage"
              >
                <span class="pet-assistant__expand-icon" aria-hidden="true">⤢</span>
              </button>
              <button
                type="button"
                class="pet-assistant__history-btn"
                :aria-expanded="historyOpen"
                :title="historyOpen ? '收起历史' : '对话历史'"
                @click.stop="toggleHistory"
              >
                <span class="pet-assistant__history-icon" aria-hidden="true">☰</span>
                <span class="pet-assistant__history-chevron" :class="{ open: historyOpen }">›</span>
              </button>
            </div>
          </div>

          <Transition name="pet-history">
            <div v-if="historyOpen" class="pet-assistant__history">
              <div v-if="!hasHistory" class="pet-assistant__history-empty">暂无记录，发一条消息开始吧</div>
              <template v-else>
                <div
                  v-for="msg in history"
                  :key="msg.id"
                  class="pet-assistant__history-item"
                  :class="msg.role"
                >
                  <span class="pet-assistant__history-role">{{ msg.role === 'user' ? '你' : '蕾西亚' }}</span>
                  <p class="pet-assistant__history-text">{{ msg.content }}</p>
                </div>
                <button type="button" class="pet-assistant__history-clear" @click.stop="clearHistory">
                  清空本地历史
                </button>
              </template>
            </div>
          </Transition>

          <div
            ref="messageBodyRef"
            class="pet-assistant__qq-body"
            :class="{ 'is-scrollable': bubbleTier === 'scroll' }"
          >
            <p class="pet-assistant__msg">{{ displayText }}</p>
            <span v-if="isStreaming" class="pet-assistant__cursor" aria-hidden="true">▍</span>
          </div>

          <p v-if="error" class="pet-assistant__error">
            {{ error }}
            <button
              v-if="loginRequired"
              type="button"
              class="pet-assistant__login-btn"
              @click="emit('request-login')"
            >
              去登录
            </button>
            <button type="button" class="pet-assistant__error-dismiss" @click="clearError">×</button>
          </p>

          <form class="pet-assistant__form" @submit.prevent="onSubmit">
            <input
              v-model="input"
              type="text"
              class="pet-assistant__input"
              placeholder="和我聊聊…"
              :disabled="isStreaming"
              autocomplete="off"
              @keydown="onKeydown"
            />
            <button
              v-if="!isStreaming"
              type="submit"
              class="pet-assistant__send"
              :disabled="!input.trim()"
              aria-label="发送"
            >
              ↑
            </button>
            <button
              v-else
              type="button"
              class="pet-assistant__send pet-assistant__send--stop"
              aria-label="停止"
              @click="stopStreaming"
            >
              ■
            </button>
          </form>

          <span class="pet-assistant__tail" aria-hidden="true" />
          </div>
        </Transition>

        <div
          class="pet-assistant__avatar"
          :class="{ 'is-chat-open': chatOpen }"
          :title="chatOpen ? '点击收起 · 滚轮缩放' : '点击展开对话 · 滚轮缩放'"
          @wheel.prevent="onAvatarWheel"
        >
          <div class="pet-assistant__sprite-stage">
            <Transition name="pet-sprite">
              <div
                :key="currentSprite.id"
                class="pet-assistant__sprite-layer"
              >
                <img
                  :src="currentSprite.src"
                  :alt="currentSprite.label"
                  class="pet-assistant__sprite"
                  :style="spriteImgStyle"
                  draggable="false"
                  @load="onSpriteLoad"
                  @error="onSpriteError"
                />
              </div>
            </Transition>
          </div>
          <p v-if="spriteMatteHint" class="pet-assistant__matte-tip">
            当前为 JPG，透明底会变成灰格；请改用 PNG（见 public/desktop-pet/README.md）
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pet-assistant {
  position: fixed;
  z-index: 28;
  width: max-content;
  max-width: min(92vw, 340px);
  touch-action: none;
  cursor: grab;
  user-select: none;
}

.pet-assistant.is-dragging {
  cursor: grabbing;
}

.pet-assistant__scaled {
  transform-origin: center bottom;
  transition: transform 0.12s ease-out;
  will-change: transform;
}

/* 固定立绘占位，气泡浮在上方，不参与文档流 */
.pet-assistant__body {
  position: relative;
  flex-shrink: 0;
  background: transparent;
  overflow: visible;
}

.pet-assistant__speech {
  --qq-bg: rgba(22, 38, 68, 0.82);
  --qq-bg-solid: rgba(24, 42, 72, 0.94);
  --qq-border: rgba(140, 190, 255, 0.28);
  --qq-accent: #8ec8ff;
  --qq-text: rgba(232, 244, 255, 0.94);
  --qq-text-muted: rgba(186, 210, 240, 0.72);
  position: absolute;
  left: 50%;
  bottom: calc(100% + 0.35rem);
  transform: translateX(-50%);
  z-index: 3;
  min-width: 156px;
  max-width: 176px;
  padding: 0.5rem 0.62rem 0.48rem;
  background: var(--qq-bg);
  border: 1px solid var(--qq-border);
  border-radius: 6px 16px 16px 16px;
  -webkit-backdrop-filter: blur(14px) saturate(1.15);
  backdrop-filter: blur(14px) saturate(1.15);
  box-shadow:
    0 4px 18px rgba(0, 0, 0, 0.28),
    0 0 0 1px rgba(255, 255, 255, 0.06) inset,
    0 8px 32px rgba(40, 90, 160, 0.12);
  cursor: default;
  transition:
    max-width 0.32s ease,
    min-width 0.32s ease;
}

.pet-assistant__speech--normal {
  min-width: 208px;
  max-width: 252px;
}

.pet-assistant__speech--wide {
  min-width: 268px;
  max-width: min(78vw, 320px);
}

.pet-assistant__speech--scroll {
  min-width: 268px;
  max-width: min(78vw, 320px);
  max-height: min(52vh, 360px);
  display: flex;
  flex-direction: column;
}

.pet-assistant__speech--scroll .pet-assistant__qq-body.is-scrollable {
  flex: 1;
  min-height: 0;
  max-height: min(36vh, 220px);
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 0.15rem;
  scrollbar-width: thin;
  scrollbar-color: rgba(140, 190, 255, 0.45) transparent;
}

.pet-assistant__speech--scroll .pet-assistant__qq-body.is-scrollable::-webkit-scrollbar {
  width: 5px;
}

.pet-assistant__speech--scroll .pet-assistant__qq-body.is-scrollable::-webkit-scrollbar-thumb {
  border-radius: 4px;
  background: rgba(140, 190, 255, 0.45);
}

.pet-assistant__tail {
  position: absolute;
  bottom: -7px;
  left: 22px;
  width: 12px;
  height: 12px;
  background: var(--qq-bg-solid);
  border-right: 1px solid var(--qq-border);
  border-bottom: 1px solid var(--qq-border);
  transform: rotate(45deg);
  box-shadow: 3px 3px 6px rgba(0, 0, 0, 0.18);
  pointer-events: none;
}

.pet-assistant__qq-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
  margin-bottom: 0.2rem;
  padding-bottom: 0.15rem;
  border-bottom: 1px solid rgba(140, 190, 255, 0.16);
}

.pet-assistant__name {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--qq-accent);
  letter-spacing: 0.04em;
}

.pet-assistant__head-actions {
  display: flex;
  align-items: center;
  gap: 0.2rem;
}

.pet-assistant__expand-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 1.3rem;
  height: 1.3rem;
  padding: 0 0.2rem;
  border: 1px solid rgba(140, 190, 255, 0.2);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--qq-accent);
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.pet-assistant__expand-icon {
  font-size: 0.72rem;
  line-height: 1;
}

.pet-assistant__expand-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(140, 190, 255, 0.35);
}

.pet-assistant__history-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.1rem;
  min-width: 1.3rem;
  height: 1.3rem;
  padding: 0 0.2rem;
  border: 1px solid rgba(140, 190, 255, 0.2);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--qq-accent);
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.pet-assistant__history-icon {
  font-size: 0.62rem;
  line-height: 1;
  opacity: 0.85;
}

.pet-assistant__history-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(140, 190, 255, 0.35);
}

.pet-assistant__history-chevron {
  display: inline-block;
  font-size: 0.95rem;
  line-height: 1;
  transform: rotate(90deg);
  transition: transform 0.22s ease;
}

.pet-assistant__history-chevron.open {
  transform: rotate(-90deg);
}

.pet-assistant__history {
  max-height: 132px;
  overflow-y: auto;
  margin-bottom: 0.35rem;
  padding: 0.35rem 0.4rem;
  border-radius: 8px;
  background: rgba(8, 16, 32, 0.35);
  border: 1px solid rgba(140, 190, 255, 0.14);
  font-size: 0.72rem;
}

.pet-assistant__history-empty {
  margin: 0;
  padding: 0.2rem 0;
  color: rgba(160, 190, 220, 0.65);
  text-align: center;
  font-size: 0.68rem;
}

.pet-assistant__history-clear {
  display: block;
  width: 100%;
  margin-top: 0.35rem;
  padding: 0.2rem 0;
  border: none;
  border-top: 1px solid rgba(140, 190, 255, 0.14);
  background: transparent;
  color: rgba(160, 190, 220, 0.65);
  font-size: 0.65rem;
  cursor: pointer;
}

.pet-assistant__history-clear:hover {
  color: #f0a0a0;
}

.pet-assistant__history-item {
  margin-bottom: 0.32rem;
}

.pet-assistant__history-item:last-child {
  margin-bottom: 0;
}

.pet-assistant__history-role {
  display: inline-block;
  min-width: 1.1rem;
  margin-right: 0.2rem;
  font-weight: 600;
  color: var(--qq-accent);
}

.pet-assistant__history-item.user .pet-assistant__history-role {
  color: rgba(160, 190, 220, 0.85);
}

.pet-assistant__history-text {
  margin: 0.08rem 0 0;
  line-height: 1.45;
  color: var(--qq-text-muted);
  white-space: pre-wrap;
  word-break: break-word;
}

.pet-assistant__qq-body {
  position: relative;
  min-height: 1.5rem;
}

.pet-assistant__msg {
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.52;
  color: var(--qq-text);
  white-space: pre-wrap;
  word-break: break-word;
}

.pet-assistant__cursor {
  color: var(--qq-accent);
  animation: pet-blink 0.9s step-end infinite;
}

@keyframes pet-blink {
  50% {
    opacity: 0;
  }
}

.pet-assistant__error {
  margin: 0.3rem 0 0;
  font-size: 0.68rem;
  color: #f0a0a0;
}

.pet-assistant__login-btn {
  margin-left: 0.35rem;
  padding: 0.12rem 0.45rem;
  border: 1px solid rgba(140, 190, 255, 0.28);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--qq-accent);
  font-size: 0.68rem;
  cursor: pointer;
  transition: background 0.2s ease;
}

.pet-assistant__login-btn:hover {
  background: rgba(255, 255, 255, 0.14);
}

.pet-assistant__error-dismiss {
  margin-left: 0.2rem;
  padding: 0 0.2rem;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.pet-assistant__form {
  display: flex;
  gap: 0.32rem;
  margin-top: 0.42rem;
  align-items: center;
}

.pet-assistant__input {
  flex: 1;
  min-width: 0;
  padding: 0.34rem 0.52rem;
  font-size: 0.75rem;
  border: 1px solid rgba(140, 190, 255, 0.22);
  border-radius: 8px;
  background: rgba(8, 16, 32, 0.42);
  color: var(--qq-text);
  outline: none;
  cursor: text;
  user-select: text;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.pet-assistant__input::placeholder {
  color: rgba(160, 190, 220, 0.5);
}

.pet-assistant__input:focus {
  border-color: rgba(140, 200, 255, 0.45);
  background: rgba(8, 16, 32, 0.55);
  box-shadow: 0 0 0 2px rgba(100, 170, 255, 0.15);
}

.pet-assistant__send {
  flex-shrink: 0;
  width: 1.7rem;
  height: 1.7rem;
  padding: 0;
  border: 1px solid rgba(140, 200, 255, 0.35);
  border-radius: 8px;
  background: linear-gradient(165deg, rgba(100, 170, 240, 0.95), rgba(60, 120, 200, 0.92));
  color: #fff;
  font-size: 0.82rem;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(40, 100, 180, 0.35);
  transition: filter 0.2s ease, transform 0.15s ease;
}

.pet-assistant__send:hover:not(:disabled) {
  filter: brightness(1.08);
}

.pet-assistant__send:active:not(:disabled) {
  transform: scale(0.96);
}

.pet-assistant__send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.pet-assistant__send--stop {
  background: linear-gradient(165deg, rgba(230, 120, 120, 0.95), rgba(190, 70, 70, 0.92));
  border-color: rgba(255, 160, 160, 0.35);
  box-shadow: 0 2px 8px rgba(160, 50, 50, 0.3);
  font-size: 0.52rem;
}

.pet-assistant__avatar {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  line-height: 0;
  background: transparent;
  cursor: pointer;
}

.pet-assistant__sprite-stage {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: visible;
  background: transparent;
}

/* 切换时两层叠在同一锚点，只做透明度变化 */
.pet-assistant__sprite-layer {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  pointer-events: none;
}

.pet-assistant__matte-tip {
  position: absolute;
  left: 50%;
  bottom: 100%;
  transform: translateX(-50%);
  width: max-content;
  max-width: 200px;
  margin: 0 0 0.35rem;
  padding: 0.28rem 0.45rem;
  font-size: 0.62rem;
  line-height: 1.35;
  color: #c8daf0;
  text-align: center;
  background: rgba(20, 28, 48, 0.92);
  border-radius: 6px;
  pointer-events: none;
}

.pet-assistant__avatar.is-chat-open {
  cursor: pointer;
}

.pet-assistant__sprite {
  display: block;
  height: 100%;
  width: auto;
  max-width: none;
  object-fit: contain;
  object-position: center bottom;
  background: transparent !important;
  border: none;
  outline: none;
  box-shadow: none;
  filter: drop-shadow(0 6px 14px rgba(30, 50, 80, 0.22));
  pointer-events: none;
  -webkit-user-drag: none;
  user-select: none;
  flex-shrink: 0;
}

.pet-sprite-enter-active,
.pet-sprite-leave-active {
  transition: opacity 0.45s ease-in-out;
}

.pet-sprite-leave-active {
  z-index: 1;
}

.pet-sprite-enter-active {
  z-index: 2;
}

.pet-sprite-enter-from,
.pet-sprite-leave-to {
  opacity: 0;
}

.pet-chat-enter-active,
.pet-chat-leave-active {
  transition: opacity 0.2s ease;
}

.pet-chat-enter-from,
.pet-chat-leave-to {
  opacity: 0;
}

.pet-history-enter-active,
.pet-history-leave-active {
  transition:
    opacity 0.2s ease,
    max-height 0.24s ease;
  overflow: hidden;
}

.pet-history-enter-from,
.pet-history-leave-to {
  opacity: 0;
  max-height: 0;
}

@media (max-width: 767px) {
  .pet-assistant {
    z-index: 35;
  }

  .pet-assistant__speech--wide,
  .pet-assistant__speech--scroll {
    max-width: min(18.5rem, calc(100vw - 5.5rem));
  }

  .pet-assistant__speech {
    max-width: min(17rem, calc(100vw - 4.5rem));
  }

  .pet-assistant__body {
    width: 88px !important;
    height: 132px !important;
  }

  .pet-assistant__input,
  .pet-assistant__send {
    min-height: 40px;
  }

  .pet-assistant.is-chat-open {
    z-index: 50;
  }
}
</style>
