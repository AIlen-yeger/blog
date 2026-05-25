/** QQ 音乐官方外链播放器（outchain） */
export function buildQqMusicPlayerUrl(songId: string, songtype = '0'): string {
  const id = songId.trim()
  return `https://i.y.qq.com/n2/m/outchain/player/index.html?songid=${encodeURIComponent(id)}&songtype=${songtype}`
}
