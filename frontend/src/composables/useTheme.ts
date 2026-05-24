import { ref, watch } from 'vue'

export type ThemeMode = 'light' | 'dark'

const STORAGE_KEY = 'personal-blog-theme'

const theme = ref<ThemeMode>(readStored())

function readStored(): ThemeMode {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'light' || v === 'dark') return v
  } catch {
    /* ignore */
  }
  return 'dark'
}

function applyTheme(mode: ThemeMode) {
  document.documentElement.dataset.theme = mode
}

applyTheme(theme.value)

watch(theme, (mode) => {
  applyTheme(mode)
  try {
    localStorage.setItem(STORAGE_KEY, mode)
  } catch {
    /* ignore */
  }
})

export function useTheme() {
  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  function setTheme(mode: ThemeMode) {
    theme.value = mode
  }

  return {
    theme,
    toggleTheme,
    setTheme,
  }
}

/** 在 main.ts 之前于 index.html 内联调用，避免闪烁 */
export function initThemeFromStorage() {
  applyTheme(readStored())
}
