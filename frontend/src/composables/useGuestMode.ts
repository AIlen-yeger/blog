import { ref } from 'vue'
import { getStoredGuestMode, setStoredGuestMode } from '@/utils/blogViewStorage'

/** 全站共享：着陆页下滑进入的只读预览（与是否登录无关） */
const guestMode = ref(getStoredGuestMode())

export function useGuestMode() {
  function setGuestMode(on: boolean) {
    guestMode.value = on
    setStoredGuestMode(on)
  }

  function syncGuestModeFromStorage() {
    guestMode.value = getStoredGuestMode()
  }

  return { guestMode, setGuestMode, syncGuestModeFromStorage }
}
