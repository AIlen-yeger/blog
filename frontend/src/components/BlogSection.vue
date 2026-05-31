<script setup lang="ts">
defineProps<{
  id: string
  titleEn: string
  titleZh?: string
}>()
</script>

<template>
  <section :id="id" class="blog-section">
    <div class="section-card">
      <header class="section-head">
        <span class="section-dot" />
        <h2 class="section-title">
          <span class="title-en">{{ titleEn }}</span>
          <span v-if="titleZh" class="title-zh">{{ titleZh }}</span>
        </h2>
      </header>
      <div class="section-body">
        <slot />
      </div>
    </div>
  </section>
</template>

<style scoped>
.blog-section {
  scroll-margin-top: 1.5rem;
  padding-bottom: 1.5rem;
}
.section-card {
  background: var(--color-surface);
  border-radius: 28px;
  padding: 1.75rem 1.85rem 2rem;
  box-shadow: var(--shadow-card);
  min-height: min(72vh, 640px);
  display: flex;
  flex-direction: column;
}
.section-head {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px dashed rgba(59, 130, 246, 0.15);
}
.section-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-accent-muted);
  box-shadow: 0 0 0 3px rgba(74, 122, 184, 0.2);
}
.section-title {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.title-en {
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: 0.28em;
  color: var(--color-text);
}
.title-zh {
  font-size: 0.82rem;
  color: var(--color-text-muted);
  letter-spacing: 0.08em;
}
.section-body {
  flex: 1;
}

@media (max-width: 768px) {
  .blog-section {
    scroll-margin-top: 0.5rem;
    padding-bottom: 1rem;
  }
  .section-card {
    border-radius: 18px;
    padding: 1.1rem 1rem 1.35rem;
    min-height: auto;
  }
  .section-head {
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
  }
  .title-en {
    font-size: 1.05rem;
    letter-spacing: 0.12em;
  }
  .title-zh {
    font-size: 0.78rem;
  }
}
</style>
