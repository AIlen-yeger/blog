export interface DesktopPetSprite {
  id: string
  src: string
  label: string
  /** 在统一舞台内微调显示比例，避免两张原图人物占比不同（默认 1） */
  fitScale?: number
}

import { petSpriteSrc } from '@/utils/petSpriteSrc'

/** 桌宠立绘：请使用 PNG 透明底；JPG 会把透明压成白/灰底 */
export const desktopPetSprites: DesktopPetSprite[] = [
  { id: 'idle', src: petSpriteSrc('idle'), label: '待机' },
  { id: 'happy', src: petSpriteSrc('happy'), label: '开心' },
]
