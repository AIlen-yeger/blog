import { ref } from 'vue'
import { desktopPetSprites, type DesktopPetSprite } from '@/data/desktopPetSprites'

const idleSprite =
  desktopPetSprites.find((s) => s.id === 'idle') ?? desktopPetSprites[0]
const happySprite = desktopPetSprites.find((s) => s.id === 'happy')

const currentSprite = ref<DesktopPetSprite>(idleSprite)

function setChatOpen(open: boolean) {
  if (open && happySprite) {
    currentSprite.value = happySprite
    return
  }
  currentSprite.value = idleSprite
}

export function useDesktopPetSprite() {
  return {
    currentSprite,
    setChatOpen,
  }
}
