const GUEST_KEY = 'personal-blog-guest'
const PREFER_LANDING_KEY = 'personal-blog-prefer-landing'
const SKIP_ANIM_KEY = 'personal-blog-skip-enter-anim'

export function getStoredGuestMode(): boolean {
  return sessionStorage.getItem(GUEST_KEY) === '1'
}

export function setStoredGuestMode(on: boolean) {
  if (on) sessionStorage.setItem(GUEST_KEY, '1')
  else sessionStorage.removeItem(GUEST_KEY)
}

export function getPreferLanding(): boolean {
  return sessionStorage.getItem(PREFER_LANDING_KEY) === '1'
}

export function setPreferLanding(on: boolean) {
  if (on) sessionStorage.setItem(PREFER_LANDING_KEY, '1')
  else sessionStorage.removeItem(PREFER_LANDING_KEY)
}

export function markSkipEnterAnim() {
  sessionStorage.setItem(SKIP_ANIM_KEY, '1')
}

export function takeSkipEnterAnim(): boolean {
  const skip = sessionStorage.getItem(SKIP_ANIM_KEY) === '1'
  sessionStorage.removeItem(SKIP_ANIM_KEY)
  return skip
}

export function clearBlogViewStorage() {
  sessionStorage.removeItem(GUEST_KEY)
  sessionStorage.removeItem(PREFER_LANDING_KEY)
}
