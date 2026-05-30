import { computed, onMounted, onUnmounted, ref } from 'vue'

/** 蓝色系着陆页背景，随时间轻微变化 */
export function useGradient() {
  const tick = ref(0)
  let timer: ReturnType<typeof setInterval> | undefined

  onMounted(() => {
    timer = setInterval(() => {
      tick.value = Date.now()
    }, 5000)
  })

  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  const gradientStyle = computed(() => {
    const now = new Date()
    const shift = (now.getHours() * 2 + now.getMinutes() * 0.1) % 10
    void tick.value
    const l1 = 8 + shift * 0.15
    const l2 = 11 + shift * 0.18
    const l3 = 14 + shift * 0.2
    return {
      background: `linear-gradient(160deg,
        hsl(222, 42%, ${l1}%) 0%,
        hsl(218, 38%, ${l2}%) 48%,
        hsl(215, 35%, ${l3}%) 100%)`,
    }
  })

  return { gradientStyle }
}
