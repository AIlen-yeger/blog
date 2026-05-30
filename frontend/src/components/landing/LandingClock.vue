<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

const now = ref(new Date())
let timer: ReturnType<typeof setInterval> | undefined

const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

onMounted(() => {
  timer = setInterval(() => {
    now.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

function pad(n: number) {
  return String(n).padStart(2, '0')
}
</script>

<template>
  <div class="landing-clock" aria-live="polite">
    <p class="clock-time">
      {{ pad(now.getHours()) }}<span class="colon">:</span>{{ pad(now.getMinutes()) }}
      <span class="clock-sec">:{{ pad(now.getSeconds()) }}</span>
    </p>
    <p class="clock-date">
      {{ now.getFullYear() }}年{{ now.getMonth() + 1 }}月{{ now.getDate() }}日
      {{ weekdays[now.getDay()] }}
    </p>
  </div>
</template>

<style scoped>
.landing-clock {
  flex: 1;
  min-width: 0;
  padding: 0.5rem 0.65rem;
  border-radius: 14px;
  background: rgba(32, 52, 88, 0.24);
  border: 1px solid rgba(150, 195, 255, 0.24);
  -webkit-backdrop-filter: blur(7px);
  backdrop-filter: blur(7px);
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.clock-time {
  margin: 0;
  font-size: clamp(1.65rem, 4.2vw, 2.15rem);
  font-weight: 300;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: #f0f9ff;
  line-height: 1.1;
}
.colon {
  animation: blink 1.2s step-end infinite;
  opacity: 0.85;
}
.clock-sec {
  font-size: 0.78em;
  color: rgba(186, 230, 253, 0.72);
  margin-left: 0.15rem;
}
.clock-date {
  margin: 0.35rem 0 0;
  font-size: clamp(0.78rem, 1.8vw, 0.88rem);
  color: rgba(186, 210, 240, 0.78);
  letter-spacing: 0.04em;
}
@keyframes blink {
  50% {
    opacity: 0.25;
  }
}
</style>
