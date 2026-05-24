export function genId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

export function todayISO(): string {
  return new Date().toISOString().slice(0, 10)
}
