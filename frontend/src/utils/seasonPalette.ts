/** 北半球月份 → 花开 / 繁茂 / 花落 / 凋零 */
export type SeasonPhase = 'bloom' | 'lush' | 'fade' | 'wither'

export interface SakuraColors {
  petal: [number, number, number]
  center: [number, number, number]
}

export interface LeafColors {
  start: [number, number, number]
  mid: [number, number, number]
  end: [number, number, number]
  vein: [number, number, number]
}

export function getSeasonPhase(month = new Date().getMonth() + 1): SeasonPhase {
  if (month >= 3 && month <= 4) return 'bloom' // 春：花开
  if (month >= 5 && month <= 8) return 'lush' // 夏：繁茂
  if (month >= 9 && month <= 10) return 'fade' // 秋：花落叶黄
  return 'wither' // 11–2 月：凋零枯萎
}

const sakuraByPhase: Record<SeasonPhase, SakuraColors> = {
  bloom: {
    petal: [255, 150, 185],
    center: [255, 228, 238],
  },
  lush: {
    petal: [255, 175, 200],
    center: [255, 240, 245],
  },
  fade: {
    petal: [220, 140, 150],
    center: [240, 210, 215],
  },
  wither: {
    petal: [160, 130, 135],
    center: [190, 175, 180],
  },
}

const leafByPhase: Record<SeasonPhase, LeafColors> = {
  bloom: {
    start: [90, 150, 85],
    mid: [130, 190, 110],
    end: [170, 200, 100],
    vein: [55, 95, 50],
  },
  lush: {
    start: [55, 120, 70],
    mid: [85, 165, 95],
    end: [110, 185, 80],
    vein: [40, 85, 45],
  },
  fade: {
    start: [180, 110, 55],
    mid: [210, 140, 65],
    end: [165, 85, 45],
    vein: [120, 70, 35],
  },
  wither: {
    start: [120, 95, 75],
    mid: [145, 115, 90],
    end: [100, 80, 70],
    vein: [85, 70, 60],
  },
}

export function getSakuraPalette(month?: number): SakuraColors {
  return sakuraByPhase[getSeasonPhase(month)]
}

export function getLeafPalette(month?: number): LeafColors {
  return leafByPhase[getSeasonPhase(month)]
}

export function seasonPhaseLabel(phase: SeasonPhase): string {
  const map: Record<SeasonPhase, string> = {
    bloom: '花开',
    lush: '盛夏',
    fade: '花落',
    wither: '凋零',
  }
  return map[phase]
}
