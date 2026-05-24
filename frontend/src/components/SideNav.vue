<script setup lang="ts">
import type { SectionId } from '@/data/mockContent'
import { navSections } from '@/data/mockContent'
import { logout, useSession } from '@/composables/useSession'

defineProps<{
  active: SectionId
  isAdmin?: boolean
  guestMode?: boolean
}>()

const emit = defineEmits<{
  navigate: [id: SectionId]
  publishLife: []
  publish: []
  requestLogin: []
  leaveGuest: []
}>()

const { currentUser } = useSession()

function handleLogout() {
  if (!confirm('确定要退出登录吗？')) return
  logout()
}
</script>

<template>
  <aside class="side-nav">
    <div class="brand">
      <span class="brand-icon">📚</span>
      <span class="brand-name">学习笔记</span>
      <span class="brand-sub">Learning Blog</span>
    </div>
    <nav class="nav-list">
      <button
        v-for="item in navSections"
        :key="item.id"
        type="button"
        class="nav-item"
        :class="{ active: active === item.id }"
        @click="emit('navigate', item.id)"
      >
        <span class="nav-en">{{ item.en }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </button>
    </nav>
    <div v-if="isAdmin" class="publish-actions">
      <button type="button" class="btn-publish-side btn-publish-life" @click="emit('publishLife')">
        <span class="publish-plus">+</span>
        <span class="publish-text">发布日记</span>
      </button>
      <button type="button" class="btn-publish-side" @click="emit('publish')">
        <span class="publish-plus">+</span>
        <span class="publish-text">发布文章</span>
      </button>
    </div>
    <div class="nav-bottom">
      <button
        v-if="isAdmin"
        type="button"
        class="btn-publish-mobile"
        @click="emit('publishLife')"
      >
        + 日记
      </button>
      <button
        v-if="isAdmin"
        type="button"
        class="btn-publish-mobile"
        @click="emit('publish')"
      >
        + 文章
      </button>
      <p v-if="currentUser?.email" class="user-email" :title="currentUser.email">
        {{ currentUser.email }}
      </p>
      <template v-if="guestMode">
        <button type="button" class="btn-logout btn-login" @click="emit('requestLogin')">
          登录
        </button>
        <button type="button" class="btn-logout btn-leave" @click="emit('leaveGuest')">
          返回首页
        </button>
      </template>
      <button v-else type="button" class="btn-logout" @click="handleLogout">
        退出登录
      </button>
      <p class="nav-foot">记录 · 整理 · 复盘</p>
    </div>
  </aside>
</template>

<style scoped>
.side-nav {
  position: fixed;
  left: 0;
  top: 0;
  z-index: 20;
  width: 200px;
  height: 100%;
  padding: 1.75rem 1.1rem;
  display: flex;
  flex-direction: column;
  background: var(--color-sidebar);
  border-radius: 0 28px 28px 0;
  box-shadow: 4px 0 32px rgba(0, 0, 0, 0.12);
}
.brand {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  margin-bottom: 2rem;
  padding-bottom: 1.25rem;
  border-bottom: 2px solid rgba(255, 255, 255, 0.2);
}
.brand-icon {
  font-size: 1.5rem;
  line-height: 1;
}
.brand-name {
  font-size: 1.05rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.06em;
}
.brand-sub {
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.nav-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1;
  min-height: 0;
}
.nav-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.1rem;
  padding: 0.65rem 0.75rem;
  border: none;
  border-radius: 14px;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: background 0.2s, transform 0.15s;
  color: #fff;
}
.nav-item:hover {
  background: rgba(255, 255, 255, 0.2);
}
.nav-item.active {
  background: rgba(255, 255, 255, 0.3);
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.nav-en {
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  opacity: 0.55;
}
.nav-item.active .nav-en {
  opacity: 0.85;
}
.nav-label {
  font-size: 0.92rem;
}

.publish-actions {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin: 0.5rem 0 0.75rem;
}

.btn-publish-side {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  width: 100%;
  margin: 0;
  padding: 0.62rem 0.85rem;
  border: 1px dashed rgba(255, 255, 255, 0.45);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 0.86rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, transform 0.15s;
}

.btn-publish-side:hover {
  background: rgba(255, 255, 255, 0.22);
  border-color: rgba(255, 255, 255, 0.65);
  transform: translateY(-1px);
}

.btn-publish-life {
  background: rgba(255, 255, 255, 0.08);
  border-style: solid;
  border-color: rgba(255, 255, 255, 0.28);
}

.publish-plus {
  font-size: 1.05rem;
  line-height: 1;
  opacity: 0.9;
}

.publish-text {
  letter-spacing: 0.04em;
}

.btn-publish-mobile {
  display: none;
}

.nav-bottom {
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.15);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.user-email {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.75);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.btn-logout {
  width: 100%;
  padding: 0.55rem 0.75rem;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}
.btn-logout:hover {
  background: rgba(255, 255, 255, 0.18);
  border-color: rgba(255, 255, 255, 0.5);
}
.nav-foot {
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.55);
  letter-spacing: 0.1em;
  margin: 0;
  text-align: center;
}

@media (max-width: 768px) {
  .side-nav {
    width: 100%;
    height: auto;
    position: fixed;
    bottom: 0;
    top: auto;
    left: 0;
    flex-direction: row;
    align-items: center;
    padding: 0.5rem 0.65rem;
    border-radius: 20px 20px 0 0;
    gap: 0.35rem;
  }
  .brand,
  .nav-foot,
  .user-email,
  .publish-actions {
    display: none;
  }
  .btn-publish-mobile {
    display: inline-flex;
    align-items: center;
    padding: 0.45rem 0.75rem;
    border: 1px dashed rgba(255, 255, 255, 0.45);
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.14);
    color: #fff;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }
  .nav-bottom {
    flex-direction: row;
    margin-top: 0;
    padding-top: 0;
    border-top: none;
    flex-shrink: 0;
  }
  .btn-logout {
    width: auto;
    padding: 0.45rem 0.75rem;
    font-size: 0.78rem;
    white-space: nowrap;
  }
  .nav-list {
    flex-direction: row;
    flex: 1;
    justify-content: space-around;
    overflow-x: auto;
  }
  .nav-item {
    padding: 0.45rem 0.55rem;
    min-width: 4.5rem;
    align-items: center;
  }
  .nav-en {
    display: none;
  }
  .nav-label {
    font-size: 0.78rem;
  }
}
</style>
