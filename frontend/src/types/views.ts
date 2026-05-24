/** 可统计浏览的内容类型 */
export type ContentKind = 'note' | 'life'

/** POST /notes|life/{id}/views 响应 */
export interface ViewRecordResult {
  /** 当前总浏览量（去重后） */
  viewCount: number
  /** 本次是否新计入一条浏览（false 表示该访客此前已浏览过） */
  recorded: boolean
}
