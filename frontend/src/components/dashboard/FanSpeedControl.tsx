import { useState } from 'react'
import { Wind, RotateCcw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useHardwareStore } from '@/store/hardwareStore'
import type { FanReading } from '@/types/hardware'

interface FanSpeedControlProps {
  fan: FanReading
}

function RpmIndicator({ rpm }: { rpm: number }) {
  const angle = Math.min((rpm / 3000) * 180, 180)
  return (
    <div className="flex items-center gap-1.5">
      <Wind
        className="h-4 w-4 text-blue-400"
        style={{ transform: `rotate(${angle}deg)`, transition: 'transform 0.5s ease' }}
      />
      <span className="font-mono text-sm font-semibold text-foreground">
        {rpm.toLocaleString()} RPM
      </span>
    </div>
  )
}

export default function FanSpeedControl({ fan }: FanSpeedControlProps) {
  const [targetPercent, setTargetPercent] = useState(fan.percent ?? 50)
  const [applying, setApplying] = useState(false)
  const setFanSpeed = useHardwareStore((s) => s.setFanSpeed)
  const restoreFanAuto = useHardwareStore((s) => s.restoreFanAuto)

  const handleApply = async () => {
    setApplying(true)
    await setFanSpeed(fan.id, targetPercent)
    setApplying(false)
  }

  const handleAuto = async () => {
    setApplying(true)
    await restoreFanAuto(fan.id)
    setApplying(false)
  }

  return (
    <div className="rounded-lg border border-border bg-card/50 p-4 space-y-3">
      {/* Fan header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-foreground">{fan.label}</p>
          <p className="text-xs text-muted-foreground font-mono">{fan.id}</p>
        </div>
        <RpmIndicator rpm={fan.rpm} />
      </div>

      {/* Percent bar (read-only view of current RPM) */}
      {fan.percent !== null && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-blue-500 transition-all duration-500"
            style={{ width: `${fan.percent}%` }}
          />
        </div>
      )}

      {/* Controls – only for controllable fans */}
      {fan.controllable ? (
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={targetPercent}
              onChange={(e) => setTargetPercent(Number(e.target.value))}
              className="flex-1 accent-blue-500"
            />
            <span className="w-10 text-right font-mono text-sm font-medium text-foreground">
              {targetPercent}%
            </span>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleApply}
              disabled={applying}
              className={cn(
                'flex-1 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-opacity',
                applying && 'opacity-50 cursor-not-allowed',
              )}
            >
              {applying ? 'Aplicando…' : 'Definir Velocidade'}
            </button>
            <button
              onClick={handleAuto}
              disabled={applying}
              title="Restaurar controle automático"
              className="rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground italic">Read-only sensor</p>
      )}
    </div>
  )
}
