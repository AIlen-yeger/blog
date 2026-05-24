<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import type { ArchiveMonthItem, TagCountItem } from '@/data/mockContent'
import { useTheme } from '@/composables/useTheme'

const props = defineProps<{
  tags: TagCountItem[]
  archiveMonths: ArchiveMonthItem[]
  loading?: boolean
  showDraftFilter?: boolean
}>()

const emit = defineEmits<{
  search: [keyword: string]
  filterTag: [tag: string | null]
  filterMonth: [month: string | null]
  filterStatus: [status: 'published' | 'draft' | null]
  clear: []
}>()

const { theme, toggleTheme } = useTheme()

const rootRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)
const expanded = ref(false)

const keyword = ref('')
const activeTag = ref<string | null>(null)
const activeMonth = ref<string | null>(null)
const activeStatus = ref<'published' | 'draft' | null>(null)

let debounceTimer: ReturnType<typeof setTimeout> | undefined

const hasActiveFilters = computed(
  () => !!(keyword.value.trim() || activeTag.value || activeMonth.value || activeStatus.value),
)

const briefLabel = computed(() => {
  const kw = keyword.value.trim()
  if (kw) return kw
  const parts: string[] = []
  if (activeStatus.value === 'draft') parts.push('草稿')
  if (activeStatus.value === 'published') parts.push('已发布')
  if (activeTag.value) parts.push(activeTag.value)
  if (activeMonth.value) parts.push(activeMonth.value)
  if (parts.length) return `已筛选：${parts.join(' · ')}`
  return '搜索笔记与生活记录'
})

const showFilters = computed(
  () =>
    expanded.value &&
    (props.showDraftFilter || props.tags.length > 0 || props.archiveMonths.length > 0),
)

watch(keyword, (v) => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => emit('search', v.trim()), 320)
})

function expand() {
  expanded.value = true
  void nextTick(() => searchInputRef.value?.focus())
}

function collapse() {
  expanded.value = false
  searchInputRef.value?.blur()
}

function onDocumentPointerDown(e: PointerEvent) {
  if (!expanded.value) return
  const target = e.target as Node
  if (rootRef.value && !rootRef.value.contains(target)) {
    collapse()
  }
}

function selectTag(tag: string) {
  activeTag.value = activeTag.value === tag ? null : tag
  emit('filterTag', activeTag.value)
}

function selectMonth(month: string) {
  activeMonth.value = activeMonth.value === month ? null : month
  emit('filterMonth', activeMonth.value)
}

function selectStatus(status: 'published' | 'draft') {
  activeStatus.value = activeStatus.value === status ? null : status
  emit('filterStatus', activeStatus.value)
}

function clearAll() {
  keyword.value = ''
  activeTag.value = null
  activeMonth.value = null
  activeStatus.value = null
  emit('clear')
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  clearTimeout(debounceTimer)
})
</script>

<template>
  <div
    ref="rootRef"
    class="discover-bar"
    :class="{ loading, expanded, 'has-filters': hasActiveFilters }"
  >
    <div class="discover-top">
      <button
        v-if="!expanded"
        type="button"
        class="search-wrap search-trigger"
        aria-label="展开搜索与筛选"
        @click="expand"
      >
        <span class="search-icon" aria-hidden="true">⌕</span>
        <span class="search-brief">{{ briefLabel }}</span>
        <span v-if="hasActiveFilters" class="filter-badge">已筛选</span>
      </button>

      <div v-else class="search-wrap search-expanded" @click.stop>
        <span class="search-icon" aria-hidden="true">⌕</span>
        <input
          ref="searchInputRef"
          v-model="keyword"
          type="search"
          class="search-input"
          placeholder="搜索笔记与生活记录（标题、摘要、正文）"
          autocomplete="off"
          @keydown.esc="collapse"
        />
        <button
          v-if="hasActiveFilters"
          type="button"
          class="clear-btn"
          @click.stop="clearAll"
        >
          清除
        </button>
      </div>

      <button
        type="button"
        class="theme-btn"
        :title="theme === 'dark' ? '切换浅色模式' : '切换深色模式'"
        @click.stop="toggleTheme"
      >
        {{ theme === 'dark' ? '☀️' : '🌙' }}
      </button>
    </div>

    <Transition name="filters">
      <div v-if="showFilters" class="discover-filters">
        <div v-if="showDraftFilter" class="chip-row">
          <span class="chip-label">状态</span>
          <button
            type="button"
            class="chip"
            :class="{ active: activeStatus === 'draft' }"
            @click="selectStatus('draft')"
          >
            草稿
          </button>
          <button
            type="button"
            class="chip"
            :class="{ active: activeStatus === 'published' }"
            @click="selectStatus('published')"
          >
            已发布
          </button>
        </div>

        <div v-if="tags.length" class="chip-row">
          <span class="chip-label">标签</span>
          <button
            v-for="item in tags"
            :key="item.tag"
            type="button"
            class="chip"
            :class="{ active: activeTag === item.tag }"
            @click="selectTag(item.tag)"
          >
            {{ item.tag }}
            <span class="chip-count">{{ item.count }}</span>
          </button>
        </div>

        <div v-if="archiveMonths.length" class="chip-row">
          <span class="chip-label">归档</span>
          <button
            v-for="item in archiveMonths"
            :key="item.month"
            type="button"
            class="chip"
            :class="{ active: activeMonth === item.month }"
            @click="selectMonth(item.month)"
          >
            {{ item.month }}
            <span class="chip-count">{{ item.count }}</span>
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.discover-bar {
  margin-bottom: 1.25rem;
  padding: 0.5rem 0.65rem;
  border-radius: 14px;
  background: var(--discover-bar-bg);
  border: 1px solid rgba(148, 163, 184, 0.2);
  transition: padding 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
}
.discover-bar.expanded {
  padding: 0.85rem 1rem;
  border-color: rgba(59, 130, 246, 0.28);
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.12);
}
.discover-bar.has-filters:not(.expanded) {
  border-color: rgba(59, 130, 246, 0.22);
}
.discover-bar.loading {
  opacity: 0.75;
  pointer-events: none;
}
.discover-top {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.search-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
  padding: 0.4rem 0.7rem;
  border-radius: 12px;
  background: var(--discover-chip-bg);
  border: 1px solid rgba(148, 163, 184, 0.25);
}
.search-trigger {
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: inherit;
  transition: background 0.15s, border-color 0.15s;
}
.search-trigger:hover {
  border-color: rgba(59, 130, 246, 0.35);
  background: rgba(59, 130, 246, 0.08);
}
.search-expanded {
  border-color: rgba(59, 130, 246, 0.35);
}
.search-icon {
  flex-shrink: 0;
  color: var(--color-text-muted);
  font-size: 0.95rem;
}
.search-brief {
  flex: 1;
  min-width: 0;
  font-size: 0.86rem;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.discover-bar.has-filters:not(.expanded) .search-brief {
  color: var(--color-accent-muted);
}
.filter-badge {
  flex-shrink: 0;
  font-size: 0.68rem;
  font-weight: 600;
  padding: 0.1rem 0.4rem;
  border-radius: 6px;
  background: rgba(59, 130, 246, 0.2);
  color: var(--color-accent-light);
}
.search-input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  font-size: 0.9rem;
  color: var(--color-text-on-dark);
  outline: none;
}
[data-theme='light'] .search-input {
  color: var(--color-text);
}
.clear-btn {
  border: none;
  background: none;
  font-size: 0.78rem;
  color: var(--color-accent-light);
  cursor: pointer;
  white-space: nowrap;
}
.theme-btn {
  flex-shrink: 0;
  width: 2.15rem;
  height: 2.15rem;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: var(--discover-chip-bg);
  cursor: pointer;
  font-size: 1rem;
  transition: width 0.22s, height 0.22s;
}
.discover-bar.expanded .theme-btn {
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 12px;
  font-size: 1.05rem;
}
.discover-filters {
  padding-top: 0.15rem;
}
.chip-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.65rem;
}
.chip-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-text-muted);
  margin-right: 0.2rem;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.22rem 0.55rem;
  border-radius: 999px;
  border: 1px solid transparent;
  background: var(--discover-chip-bg);
  color: var(--color-text-on-dark);
  font-size: 0.78rem;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
[data-theme='light'] .chip {
  color: var(--color-text);
}
.chip.active {
  background: var(--discover-chip-active);
  border-color: rgba(59, 130, 246, 0.45);
  color: var(--color-accent-light);
}
[data-theme='light'] .chip.active {
  color: var(--color-accent-dark);
}
.chip-count {
  font-size: 0.68rem;
  opacity: 0.75;
}

.filters-enter-active,
.filters-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.filters-enter-from,
.filters-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
