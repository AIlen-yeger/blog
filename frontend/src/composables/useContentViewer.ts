import { computed } from 'vue'
import { useGuestMode } from '@/composables/useGuestMode'
import { useSession } from '@/composables/useSession'

/** 博客内容可见性：预览模式 / 访客 vs 完整管理视角 */
export function useContentViewer() {
  const { isAdmin } = useSession()
  const { guestMode } = useGuestMode()

  /** 完整管理视角：可编辑、看草稿、看 Agent 回复（需 ownerOnly 关闭或在此模式下） */
  const isManageView = computed(() => isAdmin.value && !guestMode.value)

  /** 列表/搜索应使用访客 API（不带 JWT） */
  const usePublicContentApi = computed(() => guestMode.value)

  return { isManageView, usePublicContentApi, guestMode }
}
