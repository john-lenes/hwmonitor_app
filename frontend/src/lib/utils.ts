import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Retorna a classe de cor baseada no valor de temperatura. */
export function tempColour(temp: number | null): string {
  if (temp === null) return 'text-muted-foreground'
  if (temp >= 90) return 'text-purple-400'
  if (temp >= 75) return 'text-red-400'
  if (temp >= 60) return 'text-amber-400'
  return 'text-green-400'
}

/** Formata gigabytes para uma string legível (GB ou TB). */
export function formatBytes(gb: number): string {
  if (gb >= 1024) return `${(gb / 1024).toFixed(1)} TB`
  return `${gb.toFixed(1)} GB`
}

/** Retorna a classe de cor para um percentual de uso. */
export function usageColour(percent: number): string {
  if (percent >= 90) return 'text-red-400'
  if (percent >= 70) return 'text-amber-400'
  return 'text-green-400'
}

/** Interpola entre duas cores hexadecimais com base em t (0-1). */
export function lerpColour(a: string, b: string, t: number): string {
  const parse = (hex: string) => [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ]
  const ca = parse(a)
  const cb = parse(b)
  const r = Math.round(ca[0] + (cb[0] - ca[0]) * t)
  const g = Math.round(ca[1] + (cb[1] - ca[1]) * t)
  const bv = Math.round(ca[2] + (cb[2] - ca[2]) * t)
  return `rgb(${r},${g},${bv})`
}
