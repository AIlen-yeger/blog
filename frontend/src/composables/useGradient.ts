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
    const l1 = 14 + shift * 0.3
    const l2 = 22 + shift * 0.35
    const l3 = 32 + shift * 0.3
    return {
      background: `linear-gradient(165deg,
        hsl(222, 48%, ${l1}%) 0%,
        hsl(215, 52%, ${l2}%) 50%,
        hsl(210, 55%, ${l3}%) 100%)`,
    }
  })

  return { gradientStyle }
}
