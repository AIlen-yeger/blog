<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useGradient } from '@/composables/useGradient'
import LandingHero from '@/components/LandingHero.vue'
import LoginModal from '@/components/LoginModal.vue'
import BlogLayout from '@/components/BlogLayout.vue'
import MusicAudioHost from '@/components/MusicAudioHost.vue'
import DesktopPetAssistant from '@/components/DesktopPetAssistant.vue'
import AgentChatPage from '@/components/AgentChatPage.vue'
import {
  loadLandingProfile,
  reloadBlogData,
  resetBlogStore,
} from '@/composables/useBlogStore'
import { syncAgentReplySettingsFromServer } from '@/composables/useAgentReplySettings'
import { initSessionFromStorage } from '@/composables/useSession'
import { triggerDailyCheckIn } from '@/composables/useDailyCheckIn'
import { clearMusicPlayback } from '@/utils/musicPlaybackStorage'
import QqMusicPersistentHost from '@/components/QqMusicPersistentHost.vue'
import { handoffLandingMusicToBlog } from '@/composables/useAboutMusic'
import { applyQqTeleportSlot, useGlobalQqPlayer } from '@/composables/useGlobalQqPlayer'
import { isBlogHash, readBlogRouteFromUrl } from '@/utils/blogRoute'
import { isAgentHash, readAgentRouteFromUrl } from '@/utils/agentRoute'
import {
  clearBlogViewStorage,
  getPreferLanding,
  getStoredGuestMode,
  markSkipEnterAnim,
  setPreferLanding,
  setStoredGuestMode,
  takeSkipEnterAnim,
} from '@/utils/blogViewStorage'

const { gradientStyle } = useGradient()
const loggedIn = ref(initSessionFromStorage())
const guestMode = ref(getStoredGuestMode())
const preferLanding = ref(getPreferLanding())
const blogHashActive = ref(
  typeof window !== 'undefined' ? readBlogRouteFromUrl() === 'blog' : false,
)
const agentPageActive = ref(
  typeof window !== 'undefined' ? readAgentRouteFromUrl() === 'chat' : false,
)
/** 用户主动进入博客后为 true；刷新时仅当 URL 为 #/blog 时恢复 */
const blogViewActive = ref(blogHashActive.value)
const showLogin = ref(false)
const animating = ref(false)
/** 进入博客过渡（着陆页下滑淡出） */
const enteringBlog = ref(false)
/** 过渡期间预挂载博客层，与着陆页动画重叠 */
const pendingBlog = ref(false)

const ENTER_MS = 1240
/** 递增以作废尚未完成的进入博客定时器（返回首页时避免旧回调改乱状态） */
let enterAnimGeneration = 0
/** 着陆层 remount，确保离开动画 class 能再次触发 */
const landingMountKey = ref(0)

function canAccessBlog() {
  return loggedIn.value || guestMode.value
}

function enterBlogUrl() {
  if (typeof window !== 'undefined' && window.location.hash !== '#/blog') {
    window.location.hash = '/blog'
  }
  blogHashActive.value = true
}

function enterLandingUrl() {
  if (typeof window !== 'undefined' && window.location.hash) {
    history.replaceState(
      null,
      '',
      window.location.pathname + window.location.search,
    )
  }
  blogHashActive.value = false
}

function resolveInBlog(): boolean {
  if (!canAccessBlog()) return false
  if (preferLanding.value) return false
  if (blogViewActive.value || guestMode.value) return true
  return isBlogHash() || blogHashActive.value
}

const inBlog = computed(() => resolveInBlog())
const showBlog = computed(() => inBlog.value || pendingBlog.value)

watch(
  () =>
    [
      agentPageActive.value,
      preferLanding.value,
      showBlog.value,
      pendingBlog.value,
      animating.value,
      enteringBlog.value,
    ] as const,
  ([onAgent, prefer, show, pending, anim, entering]) => {
    if (onAgent) return
    if (prefer) {
      enterLandingUrl()
      return
    }
    if (show || pending || anim || entering) {
      enterBlogUrl()
    }
  },
  { immediate: true },
)

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

/** 着陆页可滚动容器（与 mobile.css 中 .landing-wrap 滚动策略一致） */
function findLandingScroller(): HTMLElement | null {
  if (typeof document === 'undefined') return null
  const wrap = document.querySelector('.landing-wrap') as HTMLElement | null
  if (!wrap || wrap.classList.contains('is-leaving')) return null
  return wrap
}

function openLogin() {
  if (!loggedIn.value && !showLogin.value) {
    showLogin.value = true
  }
}

function startBlogEnter(onComplete: () => void) {
  if (animating.value) return
  const generation = ++enterAnimGeneration
  preferLanding.value = false
  setPreferLanding(false)
  enterBlogUrl()
  if (takeSkipEnterAnim()) {
    void (async () => {
      try {
        await handoffLandingMusicToBlog()
      } catch {
        /* ignore */
      }
      void reloadBlogData().catch(() => {})
    })()
    onComplete()
    return
  }
  enteringBlog.value = true
  animating.value = true
  pendingBlog.value = true
  void (async () => {
    try {
      await handoffLandingMusicToBlog()
    } catch {
      /* 音乐 handoff 失败不阻塞进入博客 */
    }
    void reloadBlogData().catch(() => {
      /* 错误由 BlogLayout 展示 loadError */
    })
  })()
  window.setTimeout(() => {
    if (generation !== enterAnimGeneration) return
    onComplete()
    pendingBlog.value = false
    window.setTimeout(() => {
      if (generation !== enterAnimGeneration) return
      enteringBlog.value = false
      animating.value = false
      const g = useGlobalQqPlayer()
      if (g.qqPlaying.value) void applyQqTeleportSlot('about')
    }, 80)
  }, ENTER_MS)
}

/** 向下滑动 /「向下滑动预览」：只读预览（游客模式），与上滑进入管理区分离 */
function enterAsGuest() {
  if (animating.value) return
  guestMode.value = true
  setStoredGuestMode(true)
  startBlogEnter(() => {
    blogViewActive.value = true
  })
}

function enterBlogLoggedIn() {
  if (!loggedIn.value || animating.value) return
  guestMode.value = false
  setStoredGuestMode(false)
  void triggerDailyCheckIn()
  startBlogEnter(() => {
    blogViewActive.value = true
  })
}

function enterPreviewDown() {
  enterAsGuest()
}

/** 预览模式下已登录管理员切回完整管理 */
function exitGuestPreview() {
  if (!loggedIn.value) {
    openLogin()
    return
  }
  guestMode.value = false
  setStoredGuestMode(false)
  void reloadBlogData().catch(() => {})
}

function onWheel(e: WheelEvent) {
  if (agentPageActive.value || inBlog.value || showLogin.value || animating.value || !isPC()) {
    return
  }
  if (e.deltaY > 25) {
    enterPreviewDown()
  } else if (e.deltaY < -25) {
    if (loggedIn.value) enterBlogLoggedIn()
    else openLogin()
  }
}

function onTouchStart(e: TouchEvent) {
  touchStartY = e.touches[0]?.clientY ?? 0
}

function onTouchEnd(e: TouchEvent) {
  if (agentPageActive.value || inBlog.value || showLogin.value || animating.value || isPC()) {
    return
  }
  const endY = e.changedTouches[0]?.clientY ?? 0
  const deltaY = endY - touchStartY

  const scroller = findLandingScroller()
  const scrollable =
    scroller != null && scroller.scrollHeight > scroller.clientHeight + 8

  // 真机「手指上移看下方内容」会被误判为「向上进入博客」；仅在滚到顶/底时才响应滑动手势
  if (scrollable && scroller) {
    const atTop = scroller.scrollTop <= 8
    const atBottom =
      scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 8
    if (deltaY > 60 && !atTop) return
    if (deltaY < -60 && !atBottom) return
  }

  if (deltaY > 60) {
    enterPreviewDown()
  } else if (deltaY < -60) {
    if (loggedIn.value) enterBlogLoggedIn()
    else openLogin()
  }
}

function onLoginSuccess() {
  showLogin.value = false
  guestMode.value = false
  setStoredGuestMode(false)
  loggedIn.value = true
  startBlogEnter(() => {
    blogViewActive.value = true
  })
  void triggerDailyCheckIn()
}

function returnToLanding() {
  enterAnimGeneration += 1
  blogViewActive.value = false
  preferLanding.value = true
  setPreferLanding(true)
  enterLandingUrl()
  guestMode.value = false
  pendingBlog.value = false
  showLogin.value = false
  enteringBlog.value = false
  animating.value = false
  setStoredGuestMode(false)
  clearMusicPlayback()
  landingMountKey.value += 1
  void loadLandingProfile()
}

function leaveGuest() {
  returnToLanding()
  clearBlogViewStorage()
  resetBlogStore()
}

function syncAgentRouteFromHash() {
  agentPageActive.value = isAgentHash()
}

function handleAuthLogout() {
  loggedIn.value = false
  preferLanding.value = false
  setPreferLanding(false)
  returnToLanding()
  clearBlogViewStorage()
  resetBlogStore()
}

onMounted(async () => {
  if (typeof window !== 'undefined' && /[?&]home=/.test(window.location.search)) {
    const url = new URL(window.location.href)
    url.searchParams.delete('home')
    const clean = url.pathname + (url.search || '') + url.hash
    window.history.replaceState(null, '', clean || '/')
  }

  await syncAgentReplySettingsFromServer()

  const urlBlog = isBlogHash()

  if (canAccessBlog() && urlBlog && !getPreferLanding()) {
    blogViewActive.value = true
    preferLanding.value = false
    setPreferLanding(false)
    enterBlogUrl()
    markSkipEnterAnim()
    void reloadBlogData().catch(() => {})
    if (loggedIn.value) void triggerDailyCheckIn()
  } else {
    if (getPreferLanding()) {
      preferLanding.value = true
      blogViewActive.value = false
      enterLandingUrl()
    }
    void loadLandingProfile()
  }

  window.addEventListener('wheel', onWheel, { passive: true })
  window.addEventListener('touchstart', onTouchStart, { passive: true })
  window.addEventListener('touchend', onTouchEnd, { passive: true })
  window.addEventListener('auth:logout', handleAuthLogout)
  window.addEventListener('blog:return-landing', returnToLanding)
  window.addEventListener('hashchange', syncAgentRouteFromHash)
  syncAgentRouteFromHash()
})

onUnmounted(() => {
  window.removeEventListener('wheel', onWheel)
  window.removeEventListener('touchstart', onTouchStart)
  window.removeEventListener('touchend', onTouchEnd)
  window.removeEventListener('auth:logout', handleAuthLogout)
  window.removeEventListener('blog:return-landing', returnToLanding)
  window.removeEventListener('hashchange', syncAgentRouteFromHash)
})
</script>

<template>
  <div
    class="app"
    :class="{ loggedIn: inBlog, animating, loginOpen: showLogin }"
    :style="appSurfaceStyle"
  >
    <div v-if="animating" class="transition-scrim" aria-hidden="true" />

    <div v-if="!agentPageActive" class="bg-shell">
      <div class="bg-panel bg-panel--tl" />
      <div class="bg-panel bg-panel--tr" />
      <div class="bg-panel bg-panel--bl" />
      <div class="bg-panel bg-panel--br" />
    </div>

    <div
      v-if="landingVisible && !agentPageActive"
      :key="landingMountKey"
      class="landing-wrap"
      :class="{ 'is-leaving': animating }"
    >
      <div class="landing-inner">
        <LandingHero
          :logged-in="loggedIn"
          @login="openLogin"
          @guest="enterPreviewDown"
          @enter-blog="enterBlogLoggedIn"
        />
      </div>
    </div>

    <div v-if="showBlog && !agentPageActive" key="blog" class="blog-stage">
      <div v-if="animating" class="blog-frost" aria-hidden="true" />
      <BlogLayout
        :guest-mode="guestMode"
        @request-login="openLogin"
        @leave-guest="leaveGuest"
        @enter-manage="exitGuestPreview"
        @return-landing="returnToLanding"
      />
    </div>

    <div id="qq-music-offscreen" class="qq-music-offscreen" aria-hidden="true" />
    <QqMusicPersistentHost />
    <MusicAudioHost v-if="inBlog" />
    <DesktopPetAssistant
      v-if="!agentPageActive"
      :logged-in="loggedIn"
      @request-login="openLogin"
    />

    <AgentChatPage
      v-if="agentPageActive"
      :logged-in="loggedIn"
      @request-login="openLogin"
    />

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
