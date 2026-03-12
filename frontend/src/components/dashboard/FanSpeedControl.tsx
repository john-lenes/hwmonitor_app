/**
 * FanSpeedControl – cartão estilo Nitro Sense para controle de ventoinhas.
 *
 * Exibe:
 *  - RPM atual e RPM máximo observado
 *  - Barra de progresso RPM atual / máximo
 *  - Sparkline do histórico de RPM
 *  - Seletor de 3 modos (Silencioso / Balanceado / Turbo) + botão Auto
 */
import { useState, memo } from 'react'
import { Leaf, SlidersHorizontal, Zap, RotateCcw, Wind } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useHardwareStore } from '@/store/hardwareStore'
import type { FanReading } from '@/types/hardware'

// ---------------------------------------------------------------------------
// Definição dos 3 modos de velocidade (espelhado em fan.py / SPEED_MODES)
// ---------------------------------------------------------------------------
interface ModeConfig {
  key: string
  label: string
  desc: string
  percent: number
  icon: React.ElementType
  /** Classes estáticas Tailwind para o estado ATIVO do botão. */
  activeClasses: string
  /** Classe da pill de status no header. */
  pillClasses: string
}

const MODES: ModeConfig[] = [
  {
    key: 'quiet',
    label: 'Silencioso',
    desc: '~30 %',
    percent: 30,
    icon: Leaf,
    activeClasses: 'bg-emerald-500/20 border-emerald-500 text-emerald-400',
    pillClasses: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40',
  },
  {
    key: 'balanced',
    label: 'Balanceado',
    desc: '~60 %',
    percent: 60,
    icon: SlidersHorizontal,
    activeClasses: 'bg-amber-500/20 border-amber-500 text-amber-400',
    pillClasses: 'bg-amber-500/20 text-amber-400 border border-amber-500/40',
  },
  {
    key: 'turbo',
    label: 'Turbo',
    desc: '~100 %',
    percent: 100,
    icon: Zap,
    activeClasses: 'bg-red-500/20 border-red-500 text-red-400',
    pillClasses: 'bg-red-500/20 text-red-400 border border-red-500/40',
  },
]

// ---------------------------------------------------------------------------
// Sub-componentes
// ---------------------------------------------------------------------------

/** Mini sparkline SVG com histórico de RPM. */
function RpmSparkline({ data }: { data: number[] }) {
  if (data.length < 2) return null
  const W = 100
  const H = 30
  const maxVal = Math.max(...data, 500)
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * W
    const y = H - (v / maxVal) * H
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  // Área preenchida sob a linha
  const area = `${pts[0]} ${pts.join(' ')} ${W.toFixed(1)},${H} 0,${H}`
  return (
    <svg width={W} height={H} className="shrink-0" aria-hidden="true">
      <defs>
        <linearGradient id="rpm-gradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.4" />
          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill="url(#rpm-gradient)" />
      <polyline
        points={pts.join(' ')}
        fill="none"
        stroke="hsl(var(--primary))"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}

/** Indicador numérico animado de RPM com ícone de rotação. */
function RpmDisplay({ rpm, maxRpm }: { rpm: number; maxRpm: number | null | undefined }) {
  const spinSpeed = rpm > 3000 ? '0.3s' : rpm > 1500 ? '0.6s' : rpm > 500 ? '1.2s' : '3s'
  const rpmPercent = maxRpm && maxRpm > 0 ? Math.min((rpm / maxRpm) * 100, 100) : null

  return (
    <div className="flex items-center gap-3">
      {/* Ícone girando na velocidade proporcional ao RPM */}
      <Wind
        className="h-5 w-5 text-primary shrink-0"
        style={{ animation: rpm > 100 ? `spin ${spinSpeed} linear infinite` : 'none' }}
      />
      <div>
        <div className="flex items-baseline gap-1.5">
          <span className="font-mono text-2xl font-bold tabular-nums text-foreground leading-none">
            {rpm.toLocaleString('pt-BR')}
          </span>
          <span className="text-xs text-muted-foreground font-medium">RPM</span>
        </div>
        {maxRpm ? (
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Máx:{' '}
            <span className="font-mono font-medium text-foreground/70">
              {maxRpm.toLocaleString('pt-BR')} RPM
            </span>
            {rpmPercent !== null && (
              <span className="ml-1.5 text-primary/80">({rpmPercent.toFixed(0)} %)</span>
            )}
          </p>
        ) : (
          <p className="text-[11px] text-muted-foreground mt-0.5">Calibrando máximo…</p>
        )}
      </div>
    </div>
  )
}

/** Barra de progresso RPM atual / máximo. */
function RpmBar({
  rpm,
  maxRpm,
  mode,
}: {
  rpm: number
  maxRpm: number | null | undefined
  mode: string | null | undefined
}) {
  const pct = maxRpm && maxRpm > 0 ? Math.min((rpm / maxRpm) * 100, 100) : null
  if (pct === null) return null

  const barColor =
    mode === 'turbo'
      ? 'bg-red-500'
      : mode === 'balanced'
        ? 'bg-amber-500'
        : mode === 'quiet'
          ? 'bg-emerald-500'
          : 'bg-primary'

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>0 RPM</span>
        <span>{maxRpm?.toLocaleString('pt-BR')} RPM (máx)</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted/60 relative">
        <div
          className={cn('h-full rounded-full transition-all duration-700', barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

interface FanSpeedControlProps {
  fan: FanReading
  rpmHistory?: number[]
}

function FanSpeedControl({ fan, rpmHistory }: FanSpeedControlProps) {
  const setFanMode = useHardwareStore((s) => s.setFanMode)
  const restoreFanAuto = useHardwareStore((s) => s.restoreFanAuto)

  // Usa o modo vindo do backend; enquanto não chega, assume "auto"
  const currentMode = fan.speed_mode ?? 'auto'
  const [pending, setPending] = useState<string | null>(null)

  const handleMode = async (modeKey: string) => {
    if (pending) return
    setPending(modeKey)
    try {
      if (modeKey === 'auto') {
        await restoreFanAuto(fan.id)
      } else {
        await setFanMode(fan.id, modeKey)
      }
    } finally {
      setPending(null)
    }
  }

  // Pill de status no header
  const activeModeConfig = MODES.find((m) => m.key === currentMode)

  return (
    <div
      className={cn(
        'rounded-xl border bg-card/60 backdrop-blur-sm p-4 space-y-4 transition-all duration-300',
        currentMode === 'turbo' && 'border-red-500/40 shadow-red-900/20 shadow-lg',
        currentMode === 'balanced' && 'border-amber-500/40',
        currentMode === 'quiet' && 'border-emerald-500/40',
        currentMode === 'auto' && 'border-border',
      )}
    >
      {/* ── Header: nome + pill de modo ───────────────────────────── */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground truncate">{fan.label}</p>
          <p className="text-[11px] text-muted-foreground font-mono truncate mt-0.5">{fan.id}</p>
        </div>
        {activeModeConfig ? (
          <span
            className={cn(
              'shrink-0 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
              activeModeConfig.pillClasses,
            )}
          >
            <activeModeConfig.icon className="h-2.5 w-2.5" />
            {activeModeConfig.label}
          </span>
        ) : (
          <span className="shrink-0 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide bg-muted/60 text-muted-foreground border border-border">
            <RotateCcw className="h-2.5 w-2.5" />
            Auto
          </span>
        )}
      </div>

      {/* ── RPM atual + máximo ─────────────────────────────────────── */}
      <RpmDisplay rpm={fan.rpm} maxRpm={fan.max_rpm} />

      {/* ── Barra de progresso ─────────────────────────────────────── */}
      <RpmBar rpm={fan.rpm} maxRpm={fan.max_rpm} mode={currentMode} />

      {/* ── Sparkline histórico ────────────────────────────────────── */}
      {rpmHistory && rpmHistory.length > 1 && (
        <div className="flex items-center justify-between gap-2">
          <span className="text-[10px] text-muted-foreground whitespace-nowrap">
            Histórico ({rpmHistory.length} leituras)
          </span>
          <RpmSparkline data={rpmHistory} />
        </div>
      )}

      {/* ── Seletor de 3 modos ─────────────────────────────────────── */}
      <div className="space-y-2">
        <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
          Modo de velocidade
        </p>

        <div className="grid grid-cols-3 gap-2">
          {MODES.map((m) => {
            const isActive = currentMode === m.key
            const isLoading = pending === m.key
            return (
              <button
                key={m.key}
                onClick={() => handleMode(m.key)}
                disabled={pending !== null}
                title={`${m.label} — ${m.desc}`}
                className={cn(
                  'flex flex-col items-center gap-1 rounded-lg border px-2 py-2.5 text-center transition-all duration-200',
                  'hover:scale-[1.03] active:scale-[0.97]',
                  'disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100',
                  isActive
                    ? m.activeClasses
                    : 'border-border bg-card/40 text-muted-foreground hover:text-foreground hover:border-muted-foreground/50',
                )}
              >
                {isLoading ? (
                  <span className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
                ) : (
                  <m.icon className="h-4 w-4" />
                )}
                <span className="text-[11px] font-semibold leading-none">{m.label}</span>
                <span className="text-[10px] opacity-70 leading-none">{m.desc}</span>
              </button>
            )
          })}
        </div>

        {/* Botão restaurar automático */}
        <button
          onClick={() => handleMode('auto')}
          disabled={pending !== null || currentMode === 'auto'}
          className={cn(
            'w-full flex items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-xs transition-all duration-200',
            currentMode === 'auto'
              ? 'border-primary/50 bg-primary/10 text-primary font-semibold cursor-default'
              : 'border-border text-muted-foreground hover:text-foreground hover:border-muted-foreground/50 hover:bg-muted/40',
            'disabled:opacity-50 disabled:cursor-not-allowed',
          )}
        >
          {pending === 'auto' ? (
            <span className="h-3 w-3 rounded-full border-2 border-current border-t-transparent animate-spin" />
          ) : (
            <RotateCcw className="h-3 w-3" />
          )}
          {currentMode === 'auto' ? 'Automático (BIOS) — ativo' : 'Restaurar automático (BIOS)'}
        </button>

        {/* Aviso Windows */}
        {!fan.controllable && currentMode !== 'auto' && (
          <p className="text-[10px] text-muted-foreground/70 text-center leading-tight">
            Modo salvo — controle físico requer Nitro Sense ou drivers do fabricante.
          </p>
        )}
      </div>
    </div>
  )
}

export default memo(FanSpeedControl)

