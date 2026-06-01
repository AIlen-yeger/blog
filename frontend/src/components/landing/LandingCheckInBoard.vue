<script setup lang="ts">
import { useLandingCheckIn } from '@/composables/useLandingCheckIn'

const { grid, totalDays, checkedInToday, todayKey, weekCount } = useLandingCheckIn()

const weekdays = ['日', '一', '二', '三', '四', '五', '六']
</script>

<template>
  <section class="check-in-board" aria-label="签到板">
    <header class="board-head">
      <h2 class="board-title">签到板</h2>
      <p class="board-sub">
        共 {{ totalDays }} 天 · 今日{{ checkedInToday ? '已签到' : '未签到' }}
      </p>
    </header>
    <div class="board-grid-wrap">
      <div class="weekday-labels" aria-hidden="true">
        <span v-for="w in weekdays" :key="w" class="weekday">{{ w }}</span>
      </div>
      <div
        class="board-grid"
        role="img"
        :aria-label="`最近 ${weekCount} 周签到记录，共 ${totalDays} 天`"
        :style="{ '--week-cols': weekCount }"
      >
        <span
          v-for="(cell, i) in grid"
          :key="`${cell.key}-${i}`"
          class="cell"
          :class="{
            lit: cell.level > 0,
            today: cell.key === todayKey,
            future: cell.future,
          }"
          :title="cell.key"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.check-in-board {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0.55rem 0.65rem;
  border-radius: 16px;
  background: rgba(32, 52, 88, 0.24);
  border: 1px solid rgba(150, 195, 255, 0.24);
  -webkit-backdrop-filter: blur(7px);
  backdrop-filter: blur(7px);
}
.board-head {
  flex-shrink: 0;
  margin-bottom: 0.4rem;
}
.board-title {
  margin: 0;
  font-size: 0.8rem;
  font-weight: 600;
  color: rgba(240, 248, 255, 0.95);
}
.board-sub {
  margin: 0.15rem 0 0;
  font-size: 0.65rem;
  color: rgba(180, 210, 255, 0.55);
}
.board-grid-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 0.35rem;
  align-items: stretch;
}
.weekday-labels {
  display: grid;
  grid-template-rows: repeat(7, 1fr);
  gap: var(--cell-gap, 4px);
  width: 1.1rem;
  flex-shrink: 0;
  font-size: 0.58rem;
  color: rgba(180, 210, 255, 0.45);
}
.weekday {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  line-height: 1;
}
.board-grid {
  --cell-gap: 5px;
  flex: 1;
  min-width: 0;
  height: 100%;
  display: grid;
  grid-template-rows: repeat(7, 1fr);
  grid-template-columns: repeat(var(--week-cols, 12), minmax(0, 1fr));
  grid-auto-flow: column;
  gap: var(--cell-gap);
  align-content: stretch;
}
.cell {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 12px;
  border-radius: 5px;
  background: rgba(52, 78, 120, 0.5);
  border: 1px solid rgba(100, 150, 220, 0.16);
  transition: background 0.25s ease, box-shadow 0.25s ease;
}
.cell.lit {
  background: linear-gradient(145deg, #34d399, #10b981);
  border-color: rgba(52, 211, 153, 0.45);
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.35);
}
.cell.today:not(.lit) {
  box-shadow: 0 0 0 1px rgba(125, 211, 252, 0.45);
}
.cell.future {
  opacity: 0.28;
  pointer-events: none;
}

@media (max-width: 767px) {
  .check-in-board {
    padding: 0.5rem 0.55rem;
    min-height: 6.25rem;
    max-height: 8.5rem;
    flex: 0 1 auto;
  }
  .board-title {
    font-size: 0.85rem;
  }
  .board-sub {
    font-size: 0.7rem;
  }
  .weekday-labels {
    width: 1.25rem;
    font-size: 0.62rem;
  }
  .board-grid {
    --cell-gap: 4px;
  }
  .cell {
    min-height: 10px;
    border-radius: 4px;
  }
}

@media (max-width: 380px) {
  .board-grid {
    --cell-gap: 3px;
  }
  .cell {
    min-height: 8px;
  }
}
</style>
