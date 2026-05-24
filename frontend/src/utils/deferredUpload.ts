/** 选择图片后的本地草稿，发布/保存时再上传 */
export interface ImageDraftItem {
  key: string
  preview: string
  /** 已在服务器上的地址（编辑时保留的旧图） */
  url?: string
  file?: File
}

export function createDraftFromFile(file: File): ImageDraftItem {
  return {
    key: `f-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    preview: URL.createObjectURL(file),
    file,
  }
}

export function createDraftFromUrl(url: string, index: number): ImageDraftItem {
  return {
    key: `u-${index}-${url}`,
    preview: url,
    url,
  }
}

export function revokeDraftPreview(item: ImageDraftItem) {
  if (item.file && item.preview.startsWith('blob:')) {
    URL.revokeObjectURL(item.preview)
  }
}
