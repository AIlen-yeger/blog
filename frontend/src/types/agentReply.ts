/** 蕾西亚对笔记 / 生活记录的自动回复展示配置 */
export interface AgentReplySettings {
  /** 是否对笔记展示 Agent 回复 */
  noteEnabled: boolean
  /** 是否对生活记录展示 Agent 回复 */
  lifeEnabled: boolean
  /** 卡片预览最大字符数，超出显示省略号 */
  previewMaxChars: number
  /** 为 true 时仅管理员（站点本人）可见回复，访客不展示 */
  ownerOnlyVisible: boolean
}

export type AgentReplyContentKind = 'note' | 'life'
