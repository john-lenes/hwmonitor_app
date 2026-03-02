import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface HardwareCardProps {
  title: string
  subtitle?: string
  icon?: ReactNode
  children: ReactNode
  className?: string
  accent?: 'blue' | 'green' | 'amber' | 'red' | 'purple'
}

const ACCENT_MAP = {
  blue: 'border-blue-500/30 bg-blue-500/5',
  green: 'border-green-500/30 bg-green-500/5',
  amber: 'border-amber-500/30 bg-amber-500/5',
  red: 'border-red-500/30 bg-red-500/5',
  purple: 'border-purple-500/30 bg-purple-500/5',
}

export default function HardwareCard({
  title,
  subtitle,
  icon,
  children,
  className,
  accent,
}: HardwareCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-card p-5 shadow-sm transition-all',
        accent && ACCENT_MAP[accent],
        className,
      )}
    >
      {/* Header */}
      <div className="mb-4 flex items-center gap-2">
        {icon && (
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-muted">
            {icon}
          </div>
        )}
        <div>
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          {subtitle && (
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          )}
        </div>
      </div>

      {/* Content */}
      {children}
    </div>
  )
}
