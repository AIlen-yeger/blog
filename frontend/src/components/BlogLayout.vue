<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import SideNav from './SideNav.vue'
import BlogSection from './BlogSection.vue'
import NoteCard from './NoteCard.vue'
import LifeCard from './LifeCard.vue'
import AboutProfilePanel from './AboutProfilePanel.vue'
import ProfileSettingsModal from './ProfileSettingsModal.vue'
import NoteEditorModal from './NoteEditorModal.vue'
import LifeEditorModal from './LifeEditorModal.vue'
import BlogDiscoverBar from './BlogDiscoverBar.vue'
import { useSectionScroll } from '@/composables/useSectionScroll'
import { useBlogStore } from '@/composables/useBlogStore'
import { useSession } from '@/composables/useSession'
import type { LifeItem, NoteItem, ProfileData } from '@/data/mockContent'

defineProps<{
  guestMode?: boolean
}>()

const emit = defineEmits<{
  requestLogin: []
  leaveGuest: []
}>()

const mainRef = ref<HTMLElement | null>(null)
const { activeSection, scrollToSection } = useSectionScroll(() => mainRef.value)

const { isAdmin } = useSession()

const {
  profile,
  topics,
  timeline,
  loading,
  loadError,
  ensureLoaded,
  updateProfile,
  deleteNote,
  pinNote,
  deleteLife,
  pinLife,
  tagCloud,
  archiveMonths,
  searchResult,
  applyContentFilters,
  clearContentFilters,
  getVisibleNotes,
  getVisibleLife,
} = useBlogStore()

onMounted(() => {
  void ensureLoaded()
})

const selectedTopicFilter = ref<'all' | string>('all')
const noteEditorOpen = ref(false)
const lifeEditorOpen = ref(false)
const editingNote = ref<NoteItem | null>(null)
const editingLife = ref<LifeItem | null>(null)
const profileModalOpen = ref(false)

const displayedTopics = computed(() => {
  if (selectedTopicFilter.value === 'all') return topics.value
  return topics.value.filter((t) => t.id === selectedTopicFilter.value)
})

const visibleLife = computed(() => getVisibleLife())

const isSearchMode = computed(() => !!searchResult.value)

const searchNoteCount = computed(() => searchResult.value?.noteTotal ?? searchResult.value?.notes.length ?? 0)
const searchLifeCount = computed(() => searchResult.value?.lifeTotal ?? searchResult.value?.life.length ?? 0)

function onDiscoverSearch(keyword: string) {
  void applyContentFilters({ keyword })
}

function onDiscoverTag(tag: string | null) {
  void applyContentFilters({ tag: tag ?? '' })
}

function onDiscoverMonth(month: string | null) {
  void applyContentFilters({ yearMonth: month ?? '' })
}

function onDiscoverStatus(status: 'published' | 'draft' | null) {
  void applyContentFilters({ status: status ?? undefined })
}

function onDiscoverClear() {
  void clearContentFilters()
}

async function onPinNote(id: string) {
  try {
    await pinNote(id)
  } catch (e) {
    const msg = e instanceof Error ? e.message : '置顶失败'
    window.alert(msg.includes('pinned') ? '置顶失败：请确认数据库已执行 migration-note-pinned.sql' : msg)
  }
}

async function onPinLife(id: string) {
  try {
    await pinLife(id)
  } catch (e) {
    const msg = e instanceof Error ? e.message : '置顶失败'
    window.alert(msg.includes('pinned') ? '置顶失败：请确认数据库已执行 migration-life-pinned.sql' : msg)
  }
}

function selectTopicFilter(id: 'all' | string) {
  selectedTopicFilter.value = id
}

function openNoteEditor(item: NoteItem | null = null) {
  editingNote.value = item
  noteEditorOpen.value = true
}

function openLifeEditor(item: LifeItem | null = null) {
  editingLife.value = item
  lifeEditorOpen.value = true
}

async function onSaveProfile(data: ProfileData) {
  try {
    await updateProfile(data)
  } catch (e) {
    throw e instanceof Error ? e : new Error('保存失败')
  }
}
</script>

<template>
  <div class="blog-layout">
    <SideNav
      :active="activeSection"
      :is-admin="isAdmin"
      :guest-mode="guestMode"
      @navigate="scrollToSection"
      @publish-life="openLifeEditor(null)"
      @publish="openNoteEditor(null)"
      @request-login="emit('requestLogin')"
      @leave-guest="emit('leaveGuest')"
    />

    <main ref="mainRef" class="main-scroll">
      <p v-if="loading" class="load-hint">正在从服务器加载内容…</p>
      <p v-else-if="loadError" class="load-err" role="alert">{{ loadError }}</p>
      <p v-if="!isAdmin" class="readonly-banner">当前为浏览模式，仅管理员可发布与编辑内容</p>

      <BlogDiscoverBar
        :tags="tagCloud"
        :archive-months="archiveMonths"
        :loading="loading"
        :show-draft-filter="isAdmin"
        @search="onDiscoverSearch"
        @filter-tag="onDiscoverTag"
        @filter-month="onDiscoverMonth"
        @filter-status="onDiscoverStatus"
        @clear="onDiscoverClear"
      />

      <BlogSection id="about" title-en="A B O U T" title-zh="关于我">
        <AboutProfilePanel
          :profile="profile"
          :show-edit="isAdmin"
          @edit="profileModalOpen = true"
        />
      </BlogSection>

      <BlogSection id="notes" title-en="N O T E S" title-zh="学习笔记">
        <p class="section-desc">
          点击「阅读全文」在弹窗中查看完整内容。
          <template v-if="isAdmin">管理员可使用左侧栏「发布文章」添加内容，或通过卡片右上角 ··· 菜单编辑、置顶或删除。</template>
        </p>

        <div class="topic-filter-bar">
          <button
            type="button"
            class="filter-tag"
            :class="{ active: selectedTopicFilter === 'all' }"
            @click="selectTopicFilter('all')"
          >
            全部
          </button>
          <button
            v-for="topic in topics"
            :key="topic.id"
            type="button"
            class="filter-tag"
            :class="{ active: selectedTopicFilter === topic.id }"
            @click="selectTopicFilter(topic.id)"
          >
            {{ topic.title }}
          </button>
        </div>

        <p v-if="isSearchMode" class="search-hint">
          搜索到 {{ searchNoteCount }} 篇笔记（关键词匹配标题、摘要与正文）
        </p>

        <div v-if="isSearchMode" class="notes-list search-results">
          <NoteCard
            v-for="note in searchResult!.notes"
            :key="note.id"
            :item="note"
            :editable="isAdmin"
            @edit="openNoteEditor"
            @delete="deleteNote"
            @pin="onPinNote"
          />
          <p v-if="searchResult!.notes.length === 0" class="empty-hint">未找到匹配的笔记</p>
        </div>

        <template v-else>
          <div
            v-for="topic in displayedTopics"
            :key="topic.id"
            :id="`notes-topic-${topic.id}`"
            class="topic-notes-group"
          >
            <h4 class="group-title">{{ topic.title }}</h4>
            <div class="notes-list">
              <NoteCard
                v-for="note in getVisibleNotes(topic.id)"
                :key="note.id"
                :item="note"
                :editable="isAdmin"
                @edit="openNoteEditor"
                @delete="deleteNote"
                @pin="onPinNote"
              />
              <p
                v-if="getVisibleNotes(topic.id).length === 0"
                class="empty-hint"
              >
                {{ isAdmin ? '该专题下暂无文章，点击「发布文章」添加' : '该专题下暂无文章' }}
              </p>
            </div>
          </div>
        </template>
      </BlogSection>

      <BlogSection id="life" title-en="L I F E" title-zh="生活记录">
        <p class="section-desc">
          记录生活片段，点击「阅读全文」查看详情。
          <template v-if="isAdmin">
            管理员可使用左侧栏「发布日记」添加内容，或通过卡片右上角 ··· 菜单编辑、置顶或删除。
          </template>
        </p>
        <p v-if="isSearchMode" class="search-hint">
          搜索到 {{ searchLifeCount }} 条生活记录
        </p>
        <div class="notes-list">
          <LifeCard
            v-for="item in visibleLife"
            :key="item.id"
            :item="item"
            :editable="isAdmin"
            @edit="openLifeEditor"
            @delete="deleteLife"
            @pin="onPinLife"
          />
          <p v-if="visibleLife.length === 0" class="empty-hint">
            {{ isAdmin ? '暂无生活记录，点击左侧「发布日记」添加' : '暂无生活记录' }}
          </p>
        </div>
      </BlogSection>

      <BlogSection id="timeline" title-en="T I M E L I N E" title-zh="学习轨迹">
        <p class="section-desc">阶段性学习目标与完成情况，方便复盘进度。</p>
        <ul class="timeline-list">
          <li v-for="item in timeline" :key="item.id" class="timeline-item">
            <span class="period">{{ item.period }}</span>
            <div class="timeline-body">
              <h4>{{ item.title }}</h4>
              <p>{{ item.desc }}</p>
            </div>
          </li>
        </ul>
      </BlogSection>

      <footer class="site-foot">Personal Learning Blog · 仅供学习记录</footer>
    </main>

    <ProfileSettingsModal
      v-if="isAdmin"
      :open="profileModalOpen"
      :profile="profile"
      :on-save="onSaveProfile"
      @close="profileModalOpen = false"
    />

    <template v-if="isAdmin">
      <NoteEditorModal
        :open="noteEditorOpen"
        :editing="editingNote"
        @close="noteEditorOpen = false"
      />
      <LifeEditorModal
        :open="lifeEditorOpen"
        :editing="editingLife"
        @close="lifeEditorOpen = false"
      />
    </template>

  </div>
</template>

<style scoped>
.blog-layout {
  display: flex;
  height: 100%;
  background: var(--color-bg-dark);
}

.main-scroll {
  flex: 1;
  margin-left: 200px;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 1rem 1.75rem 5rem;
  scroll-behavior: smooth;
}

.load-hint {
  margin: 0 0 1rem;
  font-size: 0.88rem;
  color: var(--color-text-muted);
}
.load-err {
  margin: 0 0 1rem;
  padding: 0.55rem 0.85rem;
  border-radius: 12px;
  background: #fdecea;
  color: #a63d32;
  font-size: 0.88rem;
}

.search-hint {
  margin: 0 0 0.85rem;
  font-size: 0.84rem;
  color: var(--color-accent-muted);
}
.search-results {
  margin-bottom: 1.5rem;
}

.readonly-banner {
  margin: 0 0 1rem;
  padding: 0.55rem 0.85rem;
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.2);
  color: var(--color-text-muted);
  font-size: 0.86rem;
  line-height: 1.45;
}

.link-btn {
  margin-left: 0.35rem;
  padding: 0;
  border: none;
  background: none;
  color: var(--color-accent);
  font-size: inherit;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.link-btn:hover {
  color: var(--color-accent-dark);
}

.section-desc {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  margin: 0 0 1rem;
  line-height: 1.5;
}

.topic-filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.35rem;
}
.filter-tag {
  padding: 0.42rem 1rem;
  border-radius: 999px;
  border: 1px solid rgba(59, 130, 246, 0.25);
  background: var(--color-surface-elevated);
  color: var(--color-text-muted);
  font-size: 0.84rem;
  cursor: pointer;
}
.filter-tag.active {
  background: #dbeafe;
  border-color: var(--color-accent-light);
  color: var(--color-accent-dark);
  font-weight: 600;
}

.topic-notes-group {
  scroll-margin-top: 1.5rem;
  margin-bottom: 1.75rem;
}
.group-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-accent-dark);
  margin-bottom: 0.75rem;
}
.notes-list {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.empty-hint {
  font-size: 0.88rem;
  color: var(--color-text-muted);
  padding: 1rem;
  text-align: center;
}

.timeline-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.timeline-item {
  display: flex;
  gap: 1.25rem;
  padding: 1.1rem 1.25rem;
  border-radius: 16px;
  background: var(--color-surface-elevated);
  border: 1px solid rgba(59, 130, 246, 0.1);
}
.period {
  flex-shrink: 0;
  min-width: 5.5rem;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--color-accent-dark);
}
.timeline-body h4 {
  font-size: 1rem;
  color: var(--color-text);
  margin-bottom: 0.25rem;
}
.timeline-body p {
  font-size: 0.88rem;
  color: var(--color-text-muted);
}

.site-foot {
  text-align: center;
  padding: 2rem 0 1rem;
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.35);
}

@media (max-width: 768px) {
  .main-scroll {
    margin-left: 0;
    padding: 1rem 1rem 6rem;
  }
}
</style>
