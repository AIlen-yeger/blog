import { onMounted, onUnmounted, ref } from 'vue'
import type { SectionId } from '@/data/mockContent'
import { navSections } from '@/data/mockContent'

export function useSectionScroll(mainRef: () => HTMLElement | null) {
  const activeSection = ref<SectionId>('about')

  let observer: IntersectionObserver | null = null

  function scrollToSection(id: SectionId) {
    const root = mainRef()
    const el = root?.querySelector(`#${id}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      activeSection.value = id
    }
  }

  onMounted(() => {
    const root = mainRef()
    if (!root) return

    observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
        if (visible?.target.id) {
          activeSection.value = visible.target.id as SectionId
        }
      },
      { root, threshold: [0.25, 0.45, 0.6], rootMargin: '-8% 0px -55% 0px' },
    )

    navSections.forEach(({ id }) => {
      const el = root.querySelector(`#${id}`)
      if (el) observer?.observe(el)
    })
  })

  onUnmounted(() => {
    observer?.disconnect()
  })

  return { activeSection, scrollToSection }
}
