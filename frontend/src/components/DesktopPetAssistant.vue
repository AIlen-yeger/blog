<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useDesktopPetChat } from '@/composables/useDesktopPetChat'
import { useDesktopPetPosition } from '@/composables/useDesktopPetPosition'
import { useDesktopPetScale } from '@/composables/useDesktopPetScale'
import { useDesktopPetSprite } from '@/composables/useDesktopPetSprite'
import { PET_SPRITE_STAGE } from '@/data/desktopPetLayout'
import { petSpriteFallback } from '@/utils/petSpriteSrc'

const props = defineProps<{
  loggedIn?: boolean
}>()

const emit = defineEmits<{
  'request-login': []
}>()

const isLoggedIn = () => props.loggedIn === true

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
} = useDesktopPetChat()

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
  requestAnimationFrame(() => measureAndPlace(true))
})

function onSpriteLoad() {
  spriteMatteHint.value = /\.jpe?g(\?|$)/i.test(currentSprite.value.src)
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
            <span class="pet-assistant__name">Kohaku</span>
            <button
              v-if="hasHistory"
              type="button"
              class="pet-assistant__history-btn"
              :aria-expanded="historyOpen"
              :title="historyOpen ? '收起历史' : '展开历史'"
              @click.stop="toggleHistory"
            >
              <span class="pet-assistant__history-chevron" :class="{ open: historyOpen }">›</span>
            </button>
          </div>

          <Transition name="pet-history">
            <div v-if="historyOpen && hasHistory" class="pet-assistant__history">
              <div
                v-for="msg in history"
                :key="msg.id"
                class="pet-assistant__history-item"
                :class="msg.role"
              >
                <span class="pet-assistant__history-role">{{ msg.role === 'user' ? '你' : 'Kohaku' }}</span>
                <p class="pet-assistant__history-text">{{ msg.content }}</p>
              </div>
            </div>
          </Transition>

          <div class="pet-assistant__qq-body">
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
  --qq-bg: #ffffff;
  --qq-border: #c5dcf0;
  --qq-accent: #4a90c8;
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
  border-radius: 4px 14px 14px 14px;
  box-shadow:
    0 2px 8px rgba(15, 40, 70, 0.12),
    0 6px 18px rgba(15, 40, 70, 0.08);
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

.pet-assistant__tail {
  position: absolute;
  bottom: -7px;
  left: 22px;
  width: 12px;
  height: 12px;
  background: var(--qq-bg);
  border-right: 1px solid var(--qq-border);
  border-bottom: 1px solid var(--qq-border);
  transform: rotate(45deg);
  box-shadow: 3px 3px 4px rgba(15, 40, 70, 0.06);
  pointer-events: none;
}

.pet-assistant__qq-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
  margin-bottom: 0.2rem;
  padding-bottom: 0.15rem;
  border-bottom: 1px solid #e8f2fa;
}

.pet-assistant__name {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--qq-accent);
}

.pet-assistant__history-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.3rem;
  height: 1.3rem;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: #eef6fc;
  color: #5a8eb8;
  cursor: pointer;
}

.pet-assistant__history-btn:hover {
  background: #dceaf6;
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
  border-radius: 6px;
  background: #f3f8fc;
  border: 1px solid #dceaf6;
  font-size: 0.72rem;
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
  color: #7a92a8;
}

.pet-assistant__history-text {
  margin: 0.08rem 0 0;
  line-height: 1.45;
  color: #334a5e;
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
  color: #1f2d3a;
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
  color: #c45a5a;
}

.pet-assistant__login-btn {
  margin-left: 0.35rem;
  padding: 0.12rem 0.45rem;
  border: 1px solid #c5dcf0;
  border-radius: 4px;
  background: #eef6fc;
  color: #4a90c8;
  font-size: 0.68rem;
  cursor: pointer;
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
  border: 1px solid #c5dcf0;
  border-radius: 4px;
  background: #f8fbfe;
  color: #1f2d3a;
  outline: none;
  cursor: text;
  user-select: text;
}

.pet-assistant__input:focus {
  border-color: var(--qq-accent);
  background: #fff;
  box-shadow: 0 0 0 2px rgba(74, 144, 200, 0.18);
}

.pet-assistant__send {
  flex-shrink: 0;
  width: 1.7rem;
  height: 1.7rem;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: linear-gradient(180deg, #6eb0e0, #4a90c8);
  color: #fff;
  font-size: 0.82rem;
  line-height: 1;
  cursor: pointer;
}

.pet-assistant__send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.pet-assistant__send--stop {
  background: linear-gradient(180deg, #e09090, #c86868);
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

@media (max-width: 640px) {
  .pet-assistant__speech--wide {
    max-width: calc(100vw - 2.5rem);
  }

  .pet-assistant__body {
    width: 96px !important;
    height: 144px !important;
  }
}
</style>
