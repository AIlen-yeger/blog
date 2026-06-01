<script setup lang="ts">
import ScrollHint from './ScrollHint.vue'
import AvatarImage from './AvatarImage.vue'
import LandingCheckInBoard from './landing/LandingCheckInBoard.vue'
import LandingClock from './landing/LandingClock.vue'
import LandingMusicPanel from './landing/LandingMusicPanel.vue'
import LandingRainParticles from './landing/LandingRainParticles.vue'
import { useBlogStore } from '@/composables/useBlogStore'

defineProps<{
  mini?: boolean
  loggedIn?: boolean
}>()

const emit = defineEmits<{
  login: []
  guest: []
  enterBlog: []
}>()

const { profile } = useBlogStore()

/** public 下默认 landing-rain.mp4；设 VITE_LANDING_VIDEO_URL=off 可关闭 */
function resolveLandingVideoUrl(): string | undefined {
  const raw = import.meta.env.VITE_LANDING_VIDEO_URL as string | undefined
  if (raw === 'off' || raw === 'false' || raw === '0') return undefined
  const trimmed = raw?.trim()
  if (trimmed) return trimmed
  return '/landing-rain.mp4'
}

const landingVideo = resolveLandingVideoUrl()
</script>

<template>
  <header class="hero" :class="{ mini }">
    <template v-if="!mini">
      <video
        v-if="landingVideo"
        class="hero-video"
        :src="landingVideo"
        autoplay
        muted
        loop
        playsinline
        aria-hidden="true"
      />
      <LandingRainParticles v-if="landingVideo" />
      <div class="hero-scrim" :class="{ 'hero-scrim--video': !!landingVideo }" aria-hidden="true" />

      <div class="hero-center">
        <div class="hero-layout">
          <aside class="hero-left">
            <div class="avatar-frame">
              <AvatarImage :src="profile.avatarUrl" size="hero" />
            </div>
            <div class="identity">
              <h1 class="name">{{ profile.name }}</h1>
              <p class="caption-sub">{{ profile.subtitle }}</p>
              <p class="intro">
                {{ profile.bio || '记录前端学习与知识整理的个人空间。' }}
              </p>
            </div>
          </aside>

          <div class="hero-right">
            <LandingCheckInBoard />
            <div class="hero-widgets-row">
              <LandingClock />
              <LandingMusicPanel />
            </div>
          </div>
        </div>
      </div>

      <div class="hero-footer">
        <ScrollHint
          :logged-in="loggedIn"
          @login="emit('login')"
          @guest="emit('guest')"
          @enter-blog="emit('enterBlog')"
        />
      </div>
    </template>

    <template v-else>
      <AvatarImage :src="profile.avatarUrl" size="sm" shape="round" />
      <h1 class="name">{{ profile.name }}</h1>
    </template>
  </header>
</template>

<style scoped>
.hero {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-on-dark);
  overflow: hidden;
}
.hero-center {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 1180px;
  padding: 1rem var(--landing-gap-x) 4.5rem;
  box-sizing: border-box;
}
.hero.mini {
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem 1.25rem;
  height: auto;
}
.hero-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
  pointer-events: none;
}
.hero-scrim {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  -webkit-backdrop-filter: blur(4px) saturate(1.04);
  backdrop-filter: blur(4px) saturate(1.04);
  background: linear-gradient(
    135deg,
    rgba(6, 12, 28, 0.62) 0%,
    rgba(10, 22, 48, 0.56) 45%,
    rgba(8, 18, 40, 0.64) 100%
  );
}
.hero-scrim--video {
  -webkit-backdrop-filter: blur(3px) saturate(1.06);
  backdrop-filter: blur(3px) saturate(1.06);
  background:
    radial-gradient(
      ellipse 92% 88% at 50% 42%,
      rgba(8, 18, 40, 0.42) 0%,
      rgba(8, 18, 40, 0.28) 52%,
      rgba(6, 12, 28, 0.14) 100%
    ),
    linear-gradient(
      180deg,
      rgba(6, 12, 28, 0.22) 0%,
      rgba(10, 22, 48, 0.18) 50%,
      rgba(6, 12, 28, 0.26) 100%
    );
  mask-image: radial-gradient(ellipse 96% 94% at 50% 45%, #000 58%, transparent 100%);
  -webkit-mask-image: radial-gradient(ellipse 96% 94% at 50% 45%, #000 58%, transparent 100%);
}
.hero-layout {
  --landing-avatar-base: min(260px, calc(100vw - 2 * var(--landing-gap-x) - 2rem));
  --landing-avatar-width: var(--landing-avatar-base);
  --landing-avatar-height: min(330px, calc(var(--landing-avatar-base) * 1.22));
  display: grid;
  grid-template-columns: auto minmax(260px, 1fr);
  gap: clamp(1rem, 2.5vw, 1.75rem);
  align-items: start;
  width: 100%;
  box-sizing: border-box;
}
.hero-left {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 1rem;
  min-width: 0;
  width: var(--landing-avatar-width);
}
.avatar-frame {
  position: relative;
  width: var(--landing-avatar-width);
  height: var(--landing-avatar-height);
  flex-shrink: 0;
  margin: 0;
  border-radius: 24px;
  overflow: hidden;
  box-shadow:
    0 24px 48px rgba(0, 0, 0, 0.38),
    0 0 0 1px rgba(160, 210, 255, 0.28);
}
.avatar-frame::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  background: linear-gradient(
    165deg,
    rgba(255, 255, 255, 0.35) 0%,
    rgba(255, 255, 255, 0.12) 50%,
    rgba(255, 255, 255, 0.04) 100%
  );
}
.avatar-frame :deep(.avatar-img.hero) {
  width: 100%;
  height: 100%;
  border-radius: 24px;
  opacity: 0.88;
  filter: brightness(1.18) contrast(0.94) saturate(0.9);
}
.identity {
  text-align: left;
  max-width: 360px;
  margin: 0 auto;
  width: 100%;
}
.identity .name {
  margin: 0;
  font-size: clamp(1.75rem, 4vw, 2.35rem);
  font-weight: 700;
  color: #fff;
  line-height: 1.15;
}
.caption-sub {
  margin: 0.4rem 0 0;
  font-size: 0.78rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: rgba(186, 220, 255, 0.8);
}
.intro {
  margin: 0.85rem 0 0;
  line-height: 1.6;
  font-size: 0.92rem;
  color: rgba(220, 235, 255, 0.82);
}
.hero-right {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
  height: var(--landing-avatar-height);
  max-height: var(--landing-avatar-height);
  min-width: 0;
  overflow: hidden;
}
.hero-widgets-row {
  display: flex;
  gap: 0.5rem;
  flex: 0 0 96px;
  height: 96px;
  min-height: 96px;
}
.hero-footer {
  position: absolute;
  left: 0;
  right: 0;
  bottom: max(1rem, env(safe-area-inset-bottom, 0px));
  z-index: 3;
  display: flex;
  justify-content: center;
  padding: 0 var(--landing-gap-x);
  pointer-events: none;
}
.hero-footer :deep(.scroll-hint) {
  pointer-events: auto;
}
.hero.mini .name {
  margin: 0;
  font-size: 1.2rem;
}

@media (max-width: 900px) {
  .hero {
    justify-content: flex-start;
  }
  .hero-center {
    padding-top: var(--landing-gap-top);
    padding-bottom: 1rem;
  }
  .hero-layout {
    grid-template-columns: 1fr;
    gap: 0.85rem;
  }
  .hero-left {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: center;
    gap: 0.75rem;
  }
  .avatar-frame {
    width: min(38vw, 140px);
    height: min(46vw, 172px);
    margin: 0;
    flex-shrink: 0;
  }
  .identity {
    flex: 1;
    min-width: 0;
    max-width: none;
  }
  .identity .name {
    font-size: clamp(1.35rem, 5vw, 1.75rem);
  }
  .intro {
    font-size: 0.85rem;
    margin-top: 0.5rem;
  }
  .hero-right {
    height: auto;
    max-height: none;
    min-height: 0;
    gap: 0.45rem;
    overflow: visible;
  }
  .hero-widgets-row {
    flex-direction: row;
    flex-wrap: wrap;
    min-height: 5.75rem;
    height: auto;
    gap: 0.45rem;
  }
  .hero-widgets-row > :deep(.landing-clock) {
    flex: 1 1 42%;
    min-width: 9.5rem;
  }
  .hero-widgets-row > :deep(.landing-music) {
    flex: 1 1 52%;
    min-width: 10rem;
  }
}

@media (max-width: 520px) {
  .hero-left {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  .identity {
    text-align: center;
    width: 100%;
  }
  .avatar-frame {
    width: min(52vw, 156px);
    height: min(64vw, 192px);
    margin: 0 auto;
  }
  .hero-right :deep(.check-in-board) {
    min-height: 6.5rem;
    max-height: 8.5rem;
  }
  .hero-widgets-row {
    flex-direction: column;
    min-height: 0;
  }
  .hero-widgets-row > :deep(.landing-clock),
  .hero-widgets-row > :deep(.landing-music) {
    flex: 1 1 auto;
    width: 100%;
    min-width: 0;
  }
  .hero-widgets-row > :deep(.landing-music) {
    min-height: 5.5rem;
  }
  .hero-widgets-row > :deep(.landing-music .music-embed-wrap) {
    min-height: 62px;
  }
}
</style>
