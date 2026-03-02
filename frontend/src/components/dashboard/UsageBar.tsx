import { cn } from '@/lib/utils'

interface UsageBarProps {
  label: string
  value: number
  max?: number
  unit?: string
  showPercent?: boolean
  subtitle?: string
}

function getBarColour(pct: number): string {
  if (pct >= 90) return 'bg-red-500'
  if (pct >= 70) return 'bg-amber-500'
  return 'bg-blue-500'
}

export default function UsageBar({
  label,
  value,
  max = 100,
  unit = '%',
  showPercent = true,
  subtitle,
}: UsageBarProps) {
  const pct = Math.min((value / max) * 100, 100)
  const barColour = getBarColour(pct)

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <div>
          <span className="font-medium text-foreground">{label}</span>
          {subtitle && <span className="ml-1.5 text-muted-foreground">{subtitle}</span>}
        </div>
        <span className="font-mono font-semibold text-foreground">
          {value.toFixed(unit === '%' ? 0 : 1)}
          {unit}
          {showPercent && unit !== '%' && (
            <span className="ml-1 text-muted-foreground">({pct.toFixed(0)}%)</span>
          )}
        </span>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn('h-full rounded-full transition-all duration-500', barColour)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
