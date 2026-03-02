import { cn, tempColour } from '@/lib/utils'

interface TemperatureGaugeProps {
  label: string
  temperature: number | null
  max?: number
  size?: 'sm' | 'md' | 'lg'
}

const SIZE_MAP = {
  sm: { outer: 'h-16 w-16', text: 'text-lg', sub: 'text-[10px]' },
  md: { outer: 'h-24 w-24', text: 'text-2xl', sub: 'text-xs' },
  lg: { outer: 'h-32 w-32', text: 'text-3xl', sub: 'text-sm' },
}

function getTempBgColour(temp: number | null): string {
  if (temp === null) return '#374151'
  if (temp >= 90) return '#7c3aed'
  if (temp >= 75) return '#ef4444'
  if (temp >= 60) return '#f59e0b'
  return '#22c55e'
}

export default function TemperatureGauge({
  label,
  temperature,
  max = 100,
  size = 'md',
}: TemperatureGaugeProps) {
  const sizes = SIZE_MAP[size]
  const pct = temperature !== null ? Math.min((temperature / max) * 100, 100) : 0
  const circumference = 2 * Math.PI * 38
  const strokeDashoffset = circumference - (pct / 100) * circumference
  const colour = getTempBgColour(temperature)

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className={cn('relative flex items-center justify-center', sizes.outer)}>
        {/* SVG ring */}
        <svg className="absolute inset-0 -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50" cy="50" r="38"
            fill="none"
            stroke="hsl(var(--muted))"
            strokeWidth="8"
          />
          <circle
            cx="50" cy="50" r="38"
            fill="none"
            stroke={colour}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{ transition: 'stroke-dashoffset 0.6s ease, stroke 0.6s ease' }}
          />
        </svg>

        {/* Centre text */}
        <div className="relative flex flex-col items-center">
          <span className={cn('font-mono font-bold leading-none', sizes.text, tempColour(temperature))}>
            {temperature !== null ? Math.round(temperature) : '—'}
          </span>
          <span className={cn('text-muted-foreground', sizes.sub)}>°C</span>
        </div>
      </div>

      <span className="text-xs font-medium text-muted-foreground">{label}</span>
    </div>
  )
}
