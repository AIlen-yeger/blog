<script setup lang="ts">
import { ref, watch } from 'vue'
import { useAuth } from '@/composables/useAuth'
import { useBlogStore } from '@/composables/useBlogStore'
import { setSessionFromLogin } from '@/composables/useSession'
import type { LoginResult } from '@/types/auth'
import AvatarImage from './AvatarImage.vue'

const { profile } = useBlogStore()

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: []; success: [] }>()
const isDev = import.meta.env.DEV

const email = ref('')
const password = ref('')
const code = ref('')
const {
  step,
  error,
  verifyHint,
  pendingEmail,
  submitting,
  sendingCode,
  resendSecondsLeft,
  resetFlow,
  submitCredentials,
  submitVerify,
  resendCode,
  backToCredentials,
} = useAuth()

watch(
  () => props.open,
  (v) => {
    if (v) {
      resetFlow()
      email.value = ''
      password.value = ''
      code.value = ''
    }
  },
)

function finishLogin(result: LoginResult) {
  setSessionFromLogin(result)
  emit('success')
  emit('close')
}

async function onSubmitCredentials() {
  const result = await submitCredentials(email.value, password.value)
  if (result) finishLogin(result)
}

async function onSubmitVerify() {
  const result = await submitVerify(
    pendingEmail.value || email.value,
    password.value,
    code.value,
  )
  if (result) finishLogin(result)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
        <div class="modal card" role="dialog" aria-labelledby="login-title">
          <div class="card-accent" />
          <button type="button" class="close" aria-label="关闭" @click="emit('close')">
            ×
          </button>
          <div class="modal-head">
            <AvatarImage :src="profile.avatarUrl" size="sm" shape="round" />
            <div>
              <h2 id="login-title">{{ step === 'credentials' ? '登录 / 注册' : '邮箱验证' }}</h2>
              <p class="modal-sub">学习笔记 · Personal Blog</p>
            </div>
          </div>
          <p v-if="step === 'verify'" class="sub">
            <template v-if="verifyHint">{{ verifyHint }}</template>
            <template v-else>验证码已发送至</template>
            <strong>{{ pendingEmail }}</strong>
            <span v-if="isDev" class="dev">（开发环境可用 123456）</span>
          </p>
          <p v-if="error" class="err" role="alert">{{ error }}</p>
          <p v-if="step === 'verify' && sendingCode" class="info">正在发送验证码…</p>

          <form v-if="step === 'credentials'" @submit.prevent="onSubmitCredentials">
            <label for="email">QQ 邮箱</label>
            <input
              id="email"
              v-model="email"
              type="email"
              placeholder="name@qq.com"
              autocomplete="email"
            />
            <label for="password">密码</label>
            <input
              id="password"
              v-model="password"
              type="password"
              placeholder="至少 6 位"
              autocomplete="current-password"
            />
            <button type="submit" class="btn primary" :disabled="submitting">
              {{ submitting ? '处理中…' : '继续' }}
            </button>
            <p class="tip">已有账号将直接登录；新账号将进入验证码步骤</p>
          </form>

          <form v-else @submit.prevent="onSubmitVerify">
            <p class="verify-email">注册邮箱：<strong>{{ pendingEmail }}</strong></p>
            <label for="code">6 位验证码</label>
            <input
              id="code"
              v-model="code"
              maxlength="6"
              inputmode="numeric"
              placeholder="请输入验证码"
              autocomplete="one-time-code"
            />
            <button type="submit" class="btn primary" :disabled="sendingCode">
              完成注册并登录
            </button>
            <button
              type="button"
              class="btn ghost"
              :disabled="sendingCode || resendSecondsLeft > 0"
              @click="resendCode"
            >
              {{
                sendingCode
                  ? '发送中…'
                  : resendSecondsLeft > 0
                    ? `${resendSecondsLeft} 秒后可重新发送`
                    : '重新发送验证码'
              }}
            </button>
            <button type="button" class="btn link" @click="backToCredentials">
              返回修改邮箱与密码
            </button>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(28, 28, 32, 0.62);
  display: grid;
  place-items: center;
  z-index: 100;
  backdrop-filter: blur(10px);
  padding: 1rem;
}
.card {
  width: min(92vw, 420px);
  padding: 1.75rem 1.75rem 1.85rem;
  border-radius: var(--radius-card);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.06);
}
.card-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(
    90deg,
    var(--color-accent-dark),
    var(--color-accent-light)
  );
}
.modal-head {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.1rem;
}
.modal-head h2 {
  margin: 0;
  font-weight: 650;
  color: var(--color-text);
  font-size: 1.2rem;
}
.modal-sub {
  margin-top: 0.2rem;
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  color: var(--color-text-muted);
  text-transform: uppercase;
}
.close {
  position: absolute;
  top: 0.85rem;
  right: 1rem;
  border: none;
  background: none;
  font-size: 1.6rem;
  line-height: 1;
  cursor: pointer;
  color: #888;
  border-radius: 8px;
  width: 2rem;
  height: 2rem;
  z-index: 1;
}
.close:hover {
  background: rgba(0, 0, 0, 0.06);
  color: var(--color-text);
}
.sub {
  font-size: 0.86rem;
  color: var(--color-text-muted);
  margin-bottom: 0.85rem;
  line-height: 1.45;
}
.dev {
  color: var(--color-accent-dark);
}
.err {
  color: #a63d32;
  font-size: 0.88rem;
  margin-bottom: 0.55rem;
  padding: 0.5rem 0.65rem;
  background: #fdecea;
  border-radius: 10px;
}
.info {
  color: var(--color-accent-dark);
  font-size: 0.86rem;
  margin-bottom: 0.55rem;
}
.verify-email {
  font-size: 0.86rem;
  color: var(--color-text-muted);
  margin: 0 0 0.35rem;
}
.btn.link {
  margin-top: 0.35rem;
  padding: 0.5rem;
  background: none;
  color: var(--color-text-muted);
  font-size: 0.82rem;
  font-weight: 500;
}
.btn.link:hover {
  color: var(--color-accent-dark);
}
.btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
form {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: 0.35rem;
}
input {
  padding: 0.7rem 0.9rem;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 14px;
  outline: none;
  background: var(--color-surface-card);
  transition: border-color 0.2s, box-shadow 0.2s;
}
input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
}
.btn {
  margin-top: 0.65rem;
  padding: 0.72rem;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  font-weight: 600;
  transition: transform 0.15s, opacity 0.15s;
}
.btn:active {
  transform: scale(0.98);
}
.btn.primary {
  background: linear-gradient(
    135deg,
    var(--color-accent-dark),
    var(--color-accent-light)
  );
  color: #fff;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.35);
}
.btn.ghost {
  background: transparent;
  color: var(--color-accent-dark);
  margin-top: 0.25rem;
}
.tip {
  font-size: 0.78rem;
  color: #999;
  margin-top: 0.35rem;
  line-height: 1.4;
}
</style>
