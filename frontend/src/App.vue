<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useGradient } from '@/composables/useGradient'
import LandingHero from '@/components/LandingHero.vue'
import LoginModal from '@/components/LoginModal.vue'
import BlogLayout from '@/components/BlogLayout.vue'
import MusicAudioHost from '@/components/MusicAudioHost.vue'
import DesktopPetAssistant from '@/components/DesktopPetAssistant.vue'
import {
  loadLandingProfile,
  reloadBlogData,
  resetBlogStore,
} from '@/composables/useBlogStore'
import { initSessionFromStorage } from '@/composables/useSession'
import { triggerDailyCheckIn } from '@/composables/useDailyCheckIn'
import { clearMusicPlayback } from '@/utils/musicPlaybackStorage'
import QqMusicPersistentHost from '@/components/QqMusicPersistentHost.vue'
import { handoffLandingMusicToBlog, resetAboutMusicForLanding } from '@/composables/useAboutMusic'
import { applyQqTeleportSlot, useGlobalQqPlayer } from '@/composables/useGlobalQqPlayer'
import { loadLandingMusicTracks } from '@/composables/useUserMusicTracks'

const { gradientStyle } = useGradient()
const loggedIn = ref(initSessionFromStorage())
const guestMode = ref(false)
/** 已登录用户主动进入博客（非游客预览） */
const blogViewActive = ref(false)
const showLogin = ref(false)
const animating = ref(false)
/** 进入博客过渡（着陆页下滑淡出） */
const enteringBlog = ref(false)
/** 返回着陆页过渡 */
const returningToLanding = ref(false)
/** 过渡期间预挂载博客层，与着陆页动画重叠 */
const pendingBlog = ref(false)

const ENTER_MS = 1240
const LEAVE_MS = 720

const inBlog = computed(() => guestMode.value || blogViewActive.value)
const showBlog = computed(() => inBlog.value || pendingBlog.value)
const landingVisible = computed(() => !inBlog.value || animating.value)

/** 进入博客时提前切到主题底色，避免渐变与 inline 样式切换闪白 */
const appSurfaceStyle = computed(() => {
  if (inBlog.value || pendingBlog.value || animating.value) {
    return { background: 'var(--color-bg-dark)' }
  }
  return gradientStyle.value
})

let touchStartY = 0

function isPC() {
  return window.matchMedia('(pointer: fine)').matches && window.innerWidth >= 768
}

function openLogin() {
  if (!loggedIn.value && !showLogin.value) {
    showLogin.value = true
  }
}

function startBlogEnter(onComplete: () => void) {
  void handoffLandingMusicToBlog()
  enteringBlog.value = true
  animating.value = true
  pendingBlog.value = true
  void reloadBlogData().catch(() => {
    /* 错误由 BlogLayout 展示 loadError */
  })
  window.setTimeout(() => {
    onComplete()
    pendingBlog.value = false
    window.setTimeout(() => {
      enteringBlog.value = false
      animating.value = false
      const g = useGlobalQqPlayer()
      if (g.qqPlaying.value) void applyQqTeleportSlot('about')
    }, 80)
  }, ENTER_MS)
}

function enterAsGuest() {
  if (guestMode.value || animating.value) return
  guestMode.value = true
  startBlogEnter(() => {})
}

function enterBlogLoggedIn() {
  if (!loggedIn.value || guestMode.value || animating.value) return
  void triggerDailyCheckIn()
  startBlogEnter(() => {
    blogViewActive.value = true
  })
}

function onWheel(e: WheelEvent) {
  if (inBlog.value || showLogin.value || !isPC()) return
  if (e.deltaY > 25) {
    enterAsGuest()
  } else if (e.deltaY < -25) {
    if (loggedIn.value) enterBlogLoggedIn()
    else openLogin()
  }
}

function onTouchStart(e: TouchEvent) {
  touchStartY = e.touches[0]?.clientY ?? 0
}

function onTouchEnd(e: TouchEvent) {
  if (inBlog.value || showLogin.value || isPC()) return
  const endY = e.changedTouches[0]?.clientY ?? 0
  if (endY - touchStartY > 60) {
    enterAsGuest()
  } else if (touchStartY - endY > 60) {
    if (loggedIn.value) enterBlogLoggedIn()
    else openLogin()
  }
}

function onLoginSuccess() {
  showLogin.value = false
  guestMode.value = false
  loggedIn.value = true
  void reloadBlogData().catch(() => {})
  void triggerDailyCheckIn()
}

function finishReturnToLanding() {
  guestMode.value = false
  blogViewActive.value = false
  pendingBlog.value = false
  showLogin.value = false
  resetAboutMusicForLanding()
  if (!loggedIn.value) {
    resetBlogStore()
    clearMusicPlayback()
  }
  void loadLandingProfile()
  if (loggedIn.value) {
    void loadLandingMusicTracks()
  }
  void nextTick(() => {
    void applyQqTeleportSlot('landing')
  })
}

function returnToLanding() {
  if (!inBlog.value && !pendingBlog.value) {
    finishReturnToLanding()
    return
  }
  if (animating.value || returningToLanding.value) return

  resetAboutMusicForLanding()
  returningToLanding.value = true
  animating.value = true

  window.setTimeout(() => {
    finishReturnToLanding()
    returningToLanding.value = false
    animating.value = false
  }, LEAVE_MS)
}

function leaveGuest() {
  returnToLanding()
}

function handleAuthLogout() {
  loggedIn.value = false
  guestMode.value = false
  blogViewActive.value = false
  pendingBlog.value = false
  showLogin.value = false
  enteringBlog.value = false
  returningToLanding.value = false
  animating.value = false
  resetAboutMusicForLanding()
  resetBlogStore()
  clearMusicPlayback()
}

onMounted(() => {
  if (loggedIn.value) {
    void reloadBlogData().catch(() => {})
    void triggerDailyCheckIn()
  } else {
    void loadLandingProfile()
  }
  window.addEventListener('wheel', onWheel, { passive: true })
  window.addEventListener('touchstart', onTouchStart, { passive: true })
  window.addEventListener('touchend', onTouchEnd, { passive: true })
  window.addEventListener('auth:logout', handleAuthLogout)
})

onUnmounted(() => {
  window.removeEventListener('wheel', onWheel)
  window.removeEventListener('touchstart', onTouchStart)
  window.removeEventListener('touchend', onTouchEnd)
  window.removeEventListener('auth:logout', handleAuthLogout)
})
</script>

<template>
  <div
    class="app"
    :class="{ loggedIn: inBlog, animating, loginOpen: showLogin }"
    :style="appSurfaceStyle"
  >
    <div v-if="animating" class="transition-scrim" aria-hidden="true" />

    <div class="bg-shell">
      <div class="bg-panel bg-panel--tl" />
      <div class="bg-panel bg-panel--tr" />
      <div class="bg-panel bg-panel--bl" />
      <div class="bg-panel bg-panel--br" />
    </div>

    <div
      v-if="landingVisible"
      class="landing-wrap"
      :class="{
        'is-leaving': enteringBlog && animating,
        'is-returning': returningToLanding && animating,
      }"
    >
      <div class="landing-inner">
        <LandingHero
          :logged-in="loggedIn"
          @login="openLogin"
          @guest="enterAsGuest"
          @enter-blog="enterBlogLoggedIn"
        />
      </div>
    </div>

    <Transition name="blog-reveal">
      <div v-if="showBlog" key="blog" class="blog-stage">
        <div v-if="animating" class="blog-frost" aria-hidden="true" />
        <BlogLayout
          :guest-mode="guestMode && !loggedIn"
          @request-login="openLogin"
          @leave-guest="leaveGuest"
          @return-landing="returnToLanding"
        />
      </div>
    </Transition>

    <div id="qq-music-offscreen" class="qq-music-offscreen" aria-hidden="true" />
    <QqMusicPersistentHost />
    <MusicAudioHost v-if="inBlog" />
    <DesktopPetAssistant :logged-in="loggedIn" @request-login="openLogin" />

    <LoginModal
      :open="showLogin"
      @close="showLogin = false"
      @success="onLoginSuccess"
    />
  </div>
</template>

<style scoped>
.app {
  position: relative;
  height: 100%;
  overflow: hidden;
  background: var(--color-bg-dark);
  transition: background 1.05s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 进入博客过渡：先铺主题深色底，再叠博客内容 */
.transition-scrim {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background: var(--color-bg-dark);
  opacity: 0;
  animation: scrim-in 1.05s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
@keyframes scrim-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* 四向展开的「盒子」背景 */
.bg-shell {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
.bg-panel {
  position: absolute;
  width: 52%;
  height: 52%;
  background: inherit;
  transition:
    transform 1.15s cubic-bezier(0.32, 0.72, 0, 1),
    opacity 0.9s cubic-bezier(0.4, 0, 0.2, 1),
    border-radius 1.05s cubic-bezier(0.32, 0.72, 0, 1),
    width 1.05s cubic-bezier(0.32, 0.72, 0, 1),
    height 1.05s cubic-bezier(0.32, 0.72, 0, 1);
  filter: brightness(1.03) saturate(1.05);
}
.bg-panel--tl {
  top: 0;
  left: 0;
  border-radius: 0 0 48% 0;
  transform: translate(14%, 14%) scale(0.88);
}
.bg-panel--tr {
  top: 0;
  right: 0;
  border-radius: 0 0 0 48%;
  transform: translate(-14%, 14%) scale(0.88);
}
.bg-panel--bl {
  bottom: 0;
  left: 0;
  border-radius: 0 48% 0 0;
  transform: translate(14%, -14%) scale(0.88);
}
.bg-panel--br {
  bottom: 0;
  right: 0;
  border-radius: 48% 0 0 0;
  transform: translate(-14%, -14%) scale(0.88);
}

.app.animating .bg-panel {
  transform: translate(0, 0) scale(1);
  border-radius: 0;
  width: 50%;
  height: 50%;
}

.app.animating,
.app.loggedIn {
  background: var(--color-bg-dark) !important;
}
.app.loggedIn .bg-shell,
.app.animating .bg-shell {
  opacity: 0;
  visibility: hidden;
  transition:
    opacity 0.85s cubic-bezier(0.4, 0, 0.2, 1),
    visibility 0s linear 0.85s;
}

.blog-stage {
  position: absolute;
  inset: 0;
  z-index: 2;
  overflow: hidden;
  background: var(--color-bg-dark);
  will-change: transform, filter, opacity;
}

/* 滑入时毛玻璃渐隐，避免内容「硬切」出现 */
.blog-frost {
  position: absolute;
  inset: 0;
  z-index: 20;
  pointer-events: none;
  background: color-mix(in srgb, var(--color-bg-dark) 55%, transparent);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  animation: blog-frost-out 1.05s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
@keyframes blog-frost-out {
  0% {
    opacity: 1;
  }
  100% {
    opacity: 0;
  }
}

.landing-wrap {
  position: absolute;
  inset: 0;
  z-index: 3;
  height: 100%;
  display: flex;
  flex-direction: column;
  pointer-events: auto;
}
.landing-wrap.is-leaving {
  pointer-events: none;
}
.landing-inner {
  width: 100%;
  height: 100%;
  will-change: transform, opacity, filter;
  transition:
    transform 1.15s cubic-bezier(0.32, 0.72, 0, 1),
    opacity 0.95s cubic-bezier(0.4, 0, 0.2, 1),
    filter 1s cubic-bezier(0.4, 0, 0.2, 1);
}
.landing-wrap.is-leaving .landing-inner {
  transform: translateY(26vh) scale(0.94);
  opacity: 0;
  filter: blur(10px);
}

.blog-reveal-enter-active {
  transition:
    transform 1.2s cubic-bezier(0.32, 0.72, 0, 1),
    filter 1.05s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 1s cubic-bezier(0.4, 0, 0.2, 1);
}
.blog-reveal-enter-from {
  transform: translateY(16vh) scale(0.985);
  filter: blur(20px);
  opacity: 0.62;
}
.blog-reveal-enter-to {
  transform: translateY(0) scale(1);
  filter: blur(0);
  opacity: 1;
}

.blog-reveal-leave-active {
  transition:
    transform 0.72s cubic-bezier(0.32, 0.72, 0, 1),
    filter 0.65s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.65s cubic-bezier(0.4, 0, 0.2, 1);
}
.blog-reveal-leave-to {
  transform: translateY(14vh) scale(0.985);
  filter: blur(16px);
  opacity: 0;
}

.landing-wrap.is-returning .landing-inner {
  animation: landing-return-in 0.72s cubic-bezier(0.32, 0.72, 0, 1) forwards;
}
@keyframes landing-return-in {
  from {
    transform: translateY(18vh) scale(0.96);
    opacity: 0.35;
    filter: blur(8px);
  }
  to {
    transform: none;
    opacity: 1;
    filter: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .transition-scrim,
  .blog-frost {
    animation: none;
    opacity: 0;
  }
  .landing-inner,
  .bg-panel,
  .blog-reveal-enter-active {
    transition-duration: 0.01ms !important;
  }
  .landing-wrap.is-leaving .landing-inner {
    transform: none;
    filter: none;
    opacity: 0;
  }
  .blog-reveal-enter-from {
    transform: none;
    filter: none;
    opacity: 1;
  }
}

.app.loginOpen .landing-wrap {
  filter: blur(2px);
  opacity: 0.85;
}

.qq-music-offscreen {
  position: fixed;
  left: -10000px;
  top: 0;
  width: 330px;
  height: 86px;
  overflow: hidden;
  opacity: 0;
  z-index: -1;
}
</style>
