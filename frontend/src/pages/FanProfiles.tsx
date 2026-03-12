/**
 * Página de gerenciamento de perfis de ventoinha.
 * Permite visualizar, criar, editar, excluir, ativar e resetar perfis.
 */

import { useState, useMemo } from 'react'
import {
  Wind,
  CheckCircle2,
  Trash2,
  Plus,
  Zap,
  Pencil,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Info,
  AlertTriangle,
  ThermometerSun,
  Gauge,
  ShieldAlert,
  Cpu,
  Monitor,
  HardDrive,
} from 'lucide-react'
import { useHardwareStore } from '@/store/hardwareStore'
import { api } from '@/services/api'
import { cn } from '@/lib/utils'
import type { FanProfile, FanProfileCreate, FanProfileUpdate, CurvePoint } from '@/types/hardware'
import HardwareCard from '@/components/dashboard/HardwareCard'
import FanSpeedControl from '@/components/dashboard/FanSpeedControl'

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Helpers
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/** Mapeamento sensor → label amigável. */
const SENSOR_OPTIONS = [
  { value: 'cpu_package', label: 'Processador (CPU)' },
  { value: 'gpu',         label: 'Placa de Vídeo (GPU)' },
  { value: 'nvme',        label: 'SSD NVMe' },
]

function sensorLabel(value: string): string {
  return SENSOR_OPTIONS.find((o) => o.value === value)?.label ?? value
}

/** Converte Celsius para Fahrenheit (arredondado). */
function cToF(c: number): number {
  return Math.round(c * 9 / 5 + 32)
}

/** Tooltip simples via title nativo + ícone informativo. */
function Tooltip({ text }: { text: string }) {
  return (
    <span
      title={text}
      className="ml-1 inline-flex cursor-help text-muted-foreground hover:text-foreground"
    >
      <Info className="h-3 w-3" />
    </span>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Monitoramento em tempo real
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Interpola o percentual de velocidade para uma dada temperatura usando a
 * curva de um perfil (interpolação linear entre pontos adjacentes).
 */
function interpolateCurve(curve: CurvePoint[], temp: number): number {
  if (curve.length === 0) return 0
  if (temp <= curve[0].temperature) return curve[0].fan_percent
  if (temp >= curve[curve.length - 1].temperature) return curve[curve.length - 1].fan_percent
  for (let i = 1; i < curve.length; i++) {
    if (temp <= curve[i].temperature) {
      const t0 = curve[i - 1].temperature
      const t1 = curve[i].temperature
      const p0 = curve[i - 1].fan_percent
      const p1 = curve[i].fan_percent
      const ratio = (temp - t0) / (t1 - t0)
      return Math.round(p0 + ratio * (p1 - p0))
    }
  }
  return 100
}

/** Card de leitura de temperatura com código de cor por nível. */
function TempCard({
  label,
  temp,
  icon,
}: {
  label: string
  temp: number | null | undefined
  icon?: React.ReactNode
}) {
  const color =
    temp == null
      ? 'text-muted-foreground'
      : temp >= 85
        ? 'text-red-400'
        : temp >= 70
          ? 'text-amber-400'
          : temp >= 55
            ? 'text-yellow-400'
            : 'text-emerald-400'
  return (
    <div className="rounded-lg border border-border bg-background/50 p-3 space-y-1.5">
      <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1">
        {icon}
        {label}
      </p>
      {temp != null ? (
        <p className={cn('text-2xl font-bold font-mono tabular-nums leading-none', color)}>
          {temp.toFixed(1)}
          <span className="text-sm font-normal ml-0.5 text-muted-foreground">°C</span>
        </p>
      ) : (
        <p className="text-xl font-mono text-muted-foreground leading-none">—</p>
      )}
    </div>
  )
}

/**
 * Mini SVG da curva de perfil com um marcador animado na posição da temperatura
 * atual — permite visualizar onde o sistema está operando na curva.
 */
function CurveMarker({
  curve,
  currentTemp,
  expectedSpeed,
}: {
  curve: CurvePoint[]
  currentTemp: number
  expectedSpeed: number
}) {
  if (curve.length < 2) return null
  const W = 100
  const H = 48
  const minT = curve[0].temperature
  const maxT = curve[curve.length - 1].temperature
  const rangeT = maxT - minT || 1
  const toX = (t: number) => ((t - minT) / rangeT) * W
  const toY = (pct: number) => H - (pct / 100) * H
  const pts = curve
    .map((p) => `${toX(p.temperature).toFixed(1)},${toY(p.fan_percent).toFixed(1)}`)
    .join(' ')
  const mx = toX(currentTemp)
  const my = toY(expectedSpeed)
  const areaPoints = `0,${H} ${pts} ${W},${H}`
  return (
    <svg width={W} height={H} className="shrink-0" aria-hidden="true">
      <defs>
        <linearGradient id="cm-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.25" />
          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={areaPoints} fill="url(#cm-grad)" />
      <polyline
        points={pts}
        fill="none"
        stroke="hsl(var(--primary))"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* Linha vertical da posição atual */}
      <line
        x1={mx.toFixed(1)}
        y1="0"
        x2={mx.toFixed(1)}
        y2={H}
        stroke="hsl(var(--primary))"
        strokeWidth="1"
        strokeDasharray="2,2"
        opacity="0.5"
      />
      {/* Marcador da posição atual */}
      <circle cx={mx.toFixed(1)} cy={my.toFixed(1)} r="6" fill="hsl(var(--primary))" opacity="0.2" />
      <circle cx={mx.toFixed(1)} cy={my.toFixed(1)} r="3.5" fill="hsl(var(--primary))" />
    </svg>
  )
}

/**
 * Painel de monitoramento em tempo real — exibe temperatura dos componentes,
 * uso de recursos, posição na curva do perfil ativo e cartões de ventoinha.
 * Atualizado automaticamente via WebSocket a cada ~2 s.
 */
function LiveMonitorPanel() {
  const snapshot = useHardwareStore((s) => s.snapshot)
  const fans = useHardwareStore((s) => s.fans)
  const fanRpmHistory = useHardwareStore((s) => s.fanRpmHistory)
  const profiles = useHardwareStore((s) => s.profiles)

  const activeProfile = useMemo(() => profiles.find((p) => p.is_active) ?? null, [profiles])

  /** Temperatura atual do sensor que controla o perfil ativo. */
  const currentTemp = useMemo(() => {
    if (!snapshot || !activeProfile) return null
    switch (activeProfile.sensor_source) {
      case 'gpu': return snapshot.gpus[0]?.temperature ?? null
      case 'cpu_package':
      default: return snapshot.cpu.temperature
    }
  }, [snapshot, activeProfile])

  /** Velocidade esperada das ventoinhas interpolada na curva do perfil ativo. */
  const expectedSpeed = useMemo(() => {
    if (currentTemp === null || !activeProfile) return null
    return interpolateCurve(activeProfile.curve, currentTemp)
  }, [currentTemp, activeProfile])

  const cpuTemp = snapshot?.cpu.temperature ?? null
  const gpuTemp = snapshot?.gpus[0]?.temperature ?? null
  const cpuUsage = snapshot?.cpu.usage_percent ?? null
  const memPercent = snapshot?.memory.percent ?? null

  return (
    <div className="rounded-xl border border-border bg-card/60 p-5 space-y-5">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          Monitoramento em Tempo Real
        </h2>
        {!snapshot && (
          <span className="text-xs text-muted-foreground italic">Aguardando dados do WebSocket…</span>
        )}
      </div>

      {/* ── Temperatura + Uso de recursos ──────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <TempCard label="CPU Temp" temp={cpuTemp} icon={<Cpu className="h-3 w-3" />} />
        <TempCard label="GPU Temp" temp={gpuTemp} icon={<Monitor className="h-3 w-3" />} />

        {/* CPU Uso */}
        <div className="rounded-lg border border-border bg-background/50 p-3 space-y-1.5">
          <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1">
            <Cpu className="h-3 w-3" /> CPU Uso
          </p>
          {cpuUsage != null ? (
            <>
              <p className="text-2xl font-bold font-mono tabular-nums leading-none text-foreground">
                {cpuUsage.toFixed(0)}
                <span className="text-sm font-normal ml-0.5 text-muted-foreground">%</span>
              </p>
              <div className="h-1 w-full bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-700"
                  style={{ width: `${cpuUsage}%` }}
                />
              </div>
            </>
          ) : (
            <p className="text-xl font-mono text-muted-foreground leading-none">—</p>
          )}
        </div>

        {/* RAM */}
        <div className="rounded-lg border border-border bg-background/50 p-3 space-y-1.5">
          <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1">
            <HardDrive className="h-3 w-3" /> RAM Uso
          </p>
          {memPercent != null ? (
            <>
              <p className="text-2xl font-bold font-mono tabular-nums leading-none text-foreground">
                {memPercent.toFixed(0)}
                <span className="text-sm font-normal ml-0.5 text-muted-foreground">%</span>
              </p>
              <div className="h-1 w-full bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-violet-500 rounded-full transition-all duration-700"
                  style={{ width: `${memPercent}%` }}
                />
              </div>
            </>
          ) : (
            <p className="text-xl font-mono text-muted-foreground leading-none">—</p>
          )}
        </div>
      </div>

      {/* ── Perfil ativo + posição na curva ────────────────────────────── */}
      {activeProfile && currentTemp !== null && expectedSpeed !== null && (
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3">
          <div className="space-y-0.5 min-w-0">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Perfil ativo</p>
            <p className="text-sm font-bold text-foreground">{activeProfile.name}</p>
            <p className="text-xs text-muted-foreground">
              Sensor: {sensorLabel(activeProfile.sensor_source)} · {currentTemp.toFixed(1)}°C agora
            </p>
          </div>
          <div className="text-center shrink-0">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Velocidade alvo</p>
            <p className="text-3xl font-bold font-mono text-primary leading-none mt-0.5">{expectedSpeed}%</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">calculado pela curva</p>
          </div>
          <CurveMarker
            curve={activeProfile.curve}
            currentTemp={currentTemp}
            expectedSpeed={expectedSpeed}
          />
        </div>
      )}

      {/* ── Ventoinhas ─────────────────────────────────────────────────── */}
      <div className="space-y-2">
        <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
          <Wind className="h-3 w-3" />
          Ventoinhas detectadas
        </p>
        {fans.length > 0 ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {fans.map((fan) => (
              <FanSpeedControl key={fan.id} fan={fan} rpmHistory={fanRpmHistory[fan.id]} />
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-border p-6 text-center space-y-2">
            <Wind className="h-6 w-6 text-muted-foreground/40 mx-auto" />
            <p className="text-xs text-muted-foreground/80 max-w-xs mx-auto leading-relaxed">
              Nenhuma ventoinha detectada. O hardware deste dispositivo não expõe sensores de
              ventoinha ao software via LibreHardwareMonitor. O controle físico requer ferramentas
              do fabricante (ex: Nitro Sense, HP OMEN Command Center).
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Painel de ajuda / documentação
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function GuidePanel() {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-3 text-sm font-semibold text-foreground hover:bg-muted/40 transition-colors"
      >
        <span className="flex items-center gap-2">
          <Info className="h-4 w-4 text-primary" />
          Como funcionam os perfis de ventoinha
        </span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4 text-sm text-muted-foreground border-t border-border pt-4">

          <section className="space-y-2">
            <h3 className="flex items-center gap-1.5 font-semibold text-foreground text-xs">
              <ThermometerSun className="h-3.5 w-3.5 text-orange-400" />
              Curva de temperatura
            </h3>
            <p>
              Cada perfil define uma curva que relaciona <strong>temperatura (°C)</strong> com{' '}
              <strong>velocidade (%)</strong>. Quanto mais quente o componente, mais rápido giram
              as ventoinhas. O sistema interpola automaticamente entre os pontos configurados.
            </p>
            <div className="rounded-md bg-muted/50 p-3 font-mono text-xs space-y-0.5">
              <div className="text-muted-foreground">Exemplo simplificado:</div>
              <div>40°C → 30% &nbsp;•&nbsp; 70°C → 70% &nbsp;•&nbsp; 85°C → 100%</div>
              <div className="text-muted-foreground">A 55°C o sistema usa ~50% automaticamente.</div>
            </div>
          </section>

          <section className="space-y-2">
            <h3 className="flex items-center gap-1.5 font-semibold text-foreground text-xs">
              <Gauge className="h-3.5 w-3.5 text-blue-400" />
              Controlar por
            </h3>
            <ul className="space-y-1 text-xs">
              <li><strong>Processador (CPU)</strong> — recomendado para uso geral e jogos.</li>
              <li><strong>Placa de Vídeo (GPU)</strong> — use se a GPU é o componente mais quente.</li>
              <li><strong>SSD NVMe</strong> — para sistemas com SSD muito quente.</li>
            </ul>
          </section>

          <section className="space-y-2 rounded-md border border-amber-500/30 bg-amber-500/5 p-3">
            <h3 className="flex items-center gap-1.5 font-semibold text-amber-500 text-xs">
              <ShieldAlert className="h-3.5 w-3.5" />
              Cuidados importantes
            </h3>
            <ul className="space-y-1.5 text-xs">
              <li className="flex items-start gap-1.5">
                <AlertTriangle className="h-3 w-3 mt-0.5 text-amber-400 shrink-0" />
                <span>Mantenha as ventoinhas acima de 20% quando a temperatura ultrapassar 60°C.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <AlertTriangle className="h-3 w-3 mt-0.5 text-amber-400 shrink-0" />
                <span>Configure 100% antes de 90°C para evitar danos por superaquecimento.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <AlertTriangle className="h-3 w-3 mt-0.5 text-amber-400 shrink-0" />
                <span>Em caso de dúvida, use o perfil <strong>Balanceado</strong> — é seguro para a maioria dos casos.</span>
              </li>
            </ul>
          </section>

        </div>
      )}
    </div>
  )
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Formulário genérico de perfil (novo ou edição)
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

// Modelos pré-definidos para criação rápida
interface ProfileTemplate {
  name: string
  description: string
  sensor_source: string
  curve: CurvePoint[]
  badge: string
}

const PROFILE_TEMPLATES: ProfileTemplate[] = [
  {
    name: 'Silencioso',
    description: 'Prioriza o silêncio. Ventoinhas em baixa velocidade. Ideal para trabalho leve (textos, navegação, reuniões). Pode esquentar em tarefas pesadas.',
    sensor_source: 'cpu_package',
    curve: [
      { temperature: 0,  fan_percent: 0 },
      { temperature: 50, fan_percent: 20 },
      { temperature: 65, fan_percent: 40 },
      { temperature: 80, fan_percent: 70 },
      { temperature: 90, fan_percent: 100 },
    ],
    badge: 'Silencioso',
  },
  {
    name: 'Balanceado',
    description: 'Equilíbrio entre silêncio e resfriamento. Recomendado para uso diário, jogos leves e multitarefas. Ponto de partida seguro.',
    sensor_source: 'cpu_package',
    curve: [
      { temperature: 0,  fan_percent: 20 },
      { temperature: 50, fan_percent: 40 },
      { temperature: 65, fan_percent: 60 },
      { temperature: 75, fan_percent: 80 },
      { temperature: 85, fan_percent: 100 },
    ],
    badge: 'Balanceado',
  },
  {
    name: 'Performance',
    description: 'Resfriamento máximo desde o início. Indicado para jogos intensos, renderização e streaming. Pode ser mais barulhento.',
    sensor_source: 'cpu_package',
    curve: [
      { temperature: 0,  fan_percent: 50 },
      { temperature: 40, fan_percent: 60 },
      { temperature: 60, fan_percent: 80 },
      { temperature: 75, fan_percent: 100 },
    ],
    badge: 'Performance',
  },
  {
    name: 'Gamer (GPU)',
    description: 'Controla as ventoinhas pela temperatura da placa de vídeo. Ideal quando a GPU aquece mais que o processador.',
    sensor_source: 'gpu',
    curve: [
      { temperature: 0,  fan_percent: 30 },
      { temperature: 50, fan_percent: 50 },
      { temperature: 70, fan_percent: 80 },
      { temperature: 80, fan_percent: 100 },
    ],
    badge: 'Gamer GPU',
  },
]

interface TemplateCardProps {
  template: ProfileTemplate
  onUse: (t: ProfileTemplate) => void
}

function TemplateCard({ template, onUse }: TemplateCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-3 flex flex-col">
      <div>
        <span className="text-xs font-semibold rounded-full bg-muted px-2 py-0.5">{template.badge}</span>
        <p className="mt-2 text-xs text-muted-foreground leading-relaxed">{template.description}</p>
      </div>
      <div className="mt-auto">
        <p className="text-[10px] text-muted-foreground mb-2">
          {template.curve.length} pontos · {sensorLabel(template.sensor_source)}
        </p>
        <button
          onClick={() => onUse(template)}
          className="w-full rounded-md border border-primary/40 px-3 py-1.5 text-xs font-semibold text-primary hover:bg-primary/10 transition-colors"
        >
          Usar este modelo
        </button>
      </div>
    </div>
  )
}

const DEFAULT_CURVE: CurvePoint[] = [
  { temperature: 0,  fan_percent: 20  },
  { temperature: 50, fan_percent: 40  },
  { temperature: 70, fan_percent: 70  },
  { temperature: 85, fan_percent: 100 },
]

interface ProfileFormProps {
  initialProfile?: FanProfile
  initialValues?: { name?: string; description?: string; sensor_source?: string; curve?: CurvePoint[] }
  onSaved: () => void
  onCancel: () => void
}

function ProfileForm({ initialProfile, initialValues, onSaved, onCancel }: ProfileFormProps) {
  const isEdit = !!initialProfile
  const isBuiltin = initialProfile?.is_builtin ?? false

  const [name, setName] = useState(initialValues?.name ?? initialProfile?.name ?? '')
  const [description, setDescription] = useState(initialValues?.description ?? initialProfile?.description ?? '')
  const [sensorSource, setSensorSource] = useState(initialValues?.sensor_source ?? initialProfile?.sensor_source ?? 'cpu_package')
  const [curve, setCurve] = useState<CurvePoint[]>(
    initialValues?.curve ?? initialProfile?.curve ?? DEFAULT_CURVE,
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /** Atualiza um ponto específico da curva. */
  const updateCurvePoint = (idx: number, field: keyof CurvePoint, raw: string) => {
    const value = Number(raw)
    if (isNaN(value)) return
    setCurve((prev) => prev.map((p, i) => (i === idx ? { ...p, [field]: value } : p)))
  }

  /** Adiciona um novo ponto ao final da curva. */
  const addPoint = () => {
    const last = curve[curve.length - 1]
    setCurve((prev) => [
      ...prev,
      { temperature: Math.min((last?.temperature ?? 80) + 10, 110), fan_percent: 100 },
    ])
  }

  /** Remove um ponto da curva (mínimo de 2 pontos). */
  const removePoint = (idx: number) => {
    if (curve.length <= 2) return
    setCurve((prev) => prev.filter((_, i) => i !== idx))
  }

  /** Valida a curva: pontos de temperatura devem estar em ordem crescente. */
  const validateCurve = (): string | null => {
    for (let i = 1; i < curve.length; i++) {
      if (curve[i].temperature <= curve[i - 1].temperature) {
        return `Ponto ${i + 1}: temperatura (${curve[i].temperature}°C) deve ser maior que o ponto anterior (${curve[i - 1].temperature}°C).`
      }
    }
    for (const p of curve) {
      if (p.fan_percent < 0 || p.fan_percent > 100) {
        return `Velocidade deve estar entre 0% e 100%.`
      }
      if (p.temperature < 0 || p.temperature > 110) {
        return `Temperatura deve estar entre 0°C e 110°C.`
      }
    }
    return null
  }

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('O nome do perfil é obrigatório.')
      return
    }
    const curveError = validateCurve()
    if (curveError) {
      setError(curveError)
      return
    }
    setSaving(true)
    setError(null)
    try {
      if (isEdit && initialProfile) {
        const payload: FanProfileUpdate = {
          name: name.trim(),
          description: description.trim() || undefined,
          sensor_source: sensorSource,
          curve,
        }
        await api.updateProfile(initialProfile.id, payload)
      } else {
        const payload: FanProfileCreate = {
          name: name.trim(),
          description: description.trim() || undefined,
          sensor_source: sensorSource,
          curve,
        }
        await api.createProfile(payload)
      }
      onSaved()
    } catch {
      setError('Erro ao salvar perfil. Verifique os dados e tente novamente.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className={cn(
        'rounded-xl border p-5 space-y-4',
        isBuiltin
          ? 'border-amber-500/40 bg-amber-500/5'
          : 'border-primary/40 bg-primary/5',
      )}
    >
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold text-foreground">
          {isEdit ? `Editar: ${initialProfile?.name}` : 'Novo Perfil'}
        </h3>
        {isBuiltin && (
          <span className="rounded-full border border-amber-500/50 px-2 py-0.5 text-[10px] text-amber-500">
            Perfil padrão — será salvo como cópia personalizada
          </span>
        )}
      </div>

      {error && (
        <p className="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {error}
        </p>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {/* Nome */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">
            Nome *
          </label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Meu perfil silencioso"
            className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* Controlar por */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground flex items-center">
            Controlar por
            <Tooltip text="Qual componente aciona a curva de velocidade das ventoinhas." />
          </label>
          <select
            value={sensorSource}
            onChange={(e) => setSensorSource(e.target.value)}
            className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            {SENSOR_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Descrição */}
        <div className="space-y-1 sm:col-span-2">
          <label className="text-xs font-medium text-muted-foreground">
            Descrição (opcional)
          </label>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Para que serve este perfil…"
            className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
      </div>

      {/* Curva de temperatura */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-muted-foreground flex items-center">
          Curva de velocidade
          <Tooltip text="Defina a velocidade (%) das ventoinhas para cada temperatura (°C). Pontos em ordem crescente." />
        </p>

        {/* Cabeçalho da tabela de curva */}
        <div className="flex items-center gap-3 text-[10px] uppercase tracking-wider text-muted-foreground/60 font-medium px-1">
          <span className="w-6" />
          <span className="w-24 text-center">
            Temp. °C / °F
            <Tooltip text="Temperatura de acionamento em °C (com equivalência em °F). Ordene de forma crescente." />
          </span>
          <span className="w-24 text-center">
            Velocidade (%)
            <Tooltip text="Percentual da rotação máxima. Não use 0% acima de 40°C." />
          </span>
          <span className="w-8" />
        </div>

        <div className="space-y-1.5">
          {curve.map((point, idx) => (
            <div key={idx} className="flex items-center gap-3 text-xs">
              <span className="w-6 text-center text-muted-foreground shrink-0">{idx + 1}.</span>
              <div className="flex flex-col items-center w-24">
                <input
                  type="number"
                  min={0}
                  max={110}
                  value={point.temperature}
                  onChange={(e) => updateCurvePoint(idx, 'temperature', e.target.value)}
                  className="w-full rounded border border-border bg-background px-2 py-1 font-mono text-center text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <span className="text-[9px] text-muted-foreground/70 font-mono mt-0.5">
                  {cToF(point.temperature)}°F
                </span>
              </div>
              <input
                type="number"
                min={0}
                max={100}
                value={point.fan_percent}
                onChange={(e) => updateCurvePoint(idx, 'fan_percent', e.target.value)}
                className={cn(
                  'w-24 rounded border bg-background px-2 py-1 font-mono text-center text-xs focus:outline-none focus:ring-1 focus:ring-primary',
                  point.fan_percent < 20 && point.temperature > 50
                    ? 'border-amber-500 ring-1 ring-amber-500/30'
                    : 'border-border',
                )}
              />
              {/* Aviso de velocidade muito baixa em alta temperatura */}
              {point.fan_percent < 20 && point.temperature > 50 && (
                <span title="Velocidade muito baixa para esta temperatura. Risco de superaquecimento!">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                </span>
              )}
              {curve.length > 2 && (
                <button
                  onClick={() => removePoint(idx)}
                  className="w-6 text-muted-foreground hover:text-destructive transition-colors"
                  title="Remover ponto"
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>

        {curve.length < 8 && (
          <button
            onClick={addPoint}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors mt-1"
          >
            <Plus className="h-3 w-3" />
            Adicionar ponto
          </button>
        )}
      </div>

      {/* Botões */}
      <div className="flex gap-2 pt-1">
        <button
          onClick={handleSubmit}
          disabled={saving}
          className="flex-1 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-opacity disabled:opacity-50"
        >
          {saving ? 'Salvando…' : isEdit ? 'Salvar alterações' : 'Criar perfil'}
        </button>
        <button
          onClick={onCancel}
          className="rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// ProfileCard — card individual de perfil
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface ProfileCardProps {
  profile: FanProfile
  onActivate: (id: string) => void
  onDelete: (id: string) => void
  onEdit: (profile: FanProfile) => void
  onReset: (id: string) => void
  loading: boolean
}

function ProfileCard({ profile, onActivate, onDelete, onEdit, onReset, loading }: ProfileCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border p-5 space-y-3 transition-all',
        profile.is_active
          ? 'border-primary/60 bg-primary/5'
          : 'border-border bg-card',
      )}
    >
      {/* Cabeçalho do card */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-foreground truncate">
              {profile.name}
            </h3>
            {profile.is_active && (
              <span className="flex items-center gap-1 rounded-full bg-primary/20 px-2 py-0.5 text-[10px] font-semibold text-primary">
                <CheckCircle2 className="h-2.5 w-2.5" />
                Ativo
              </span>
            )}
            {profile.is_builtin && (
              <span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground">
                Padrão
              </span>
            )}
          </div>
          {profile.description && (
            <p className="text-xs text-muted-foreground mt-0.5">{profile.description}</p>
          )}
        </div>

        {/* Ações */}
        <div className="flex items-center gap-1 shrink-0">
          {!profile.is_active && (
            <button
              onClick={() => onActivate(profile.id)}
              disabled={loading}
              title="Ativar perfil"
              className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-opacity disabled:opacity-50"
            >
              <Zap className="h-3 w-3" />
              Ativar
            </button>
          )}
          {/* Editar */}
          <button
            onClick={() => onEdit(profile)}
            disabled={loading}
            title={profile.is_builtin ? 'Editar perfil (salva como cópia)' : 'Editar perfil'}
            className="rounded-md border border-border p-1.5 text-muted-foreground hover:text-foreground hover:border-foreground/40 transition-colors disabled:opacity-50"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          {/* Reset (somente builtins) */}
          {profile.is_builtin && (
            <button
              onClick={() => onReset(profile.id)}
              disabled={loading}
              title="Restaurar configuração original"
              className="rounded-md border border-border p-1.5 text-muted-foreground hover:text-amber-500 hover:border-amber-500/50 transition-colors disabled:opacity-50"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
          )}
          {/* Excluir (somente não-builtins) */}
          {!profile.is_builtin && (
            <button
              onClick={() => onDelete(profile.id)}
              disabled={loading}
              title="Excluir perfil"
              className="rounded-md border border-border p-1.5 text-muted-foreground hover:text-destructive hover:border-destructive transition-colors disabled:opacity-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      <p className="text-[11px] text-muted-foreground flex items-center gap-1">
        <ThermometerSun className="h-3 w-3" />
        Controla por: {sensorLabel(profile.sensor_source)}
      </p>

      {/* Visualização da curva de temperatura */}
      <div className="space-y-1">
        <p className="text-[11px] font-medium text-muted-foreground">Curva de velocidade</p>
        <div className="flex items-end gap-1 h-12">
          {profile.curve.map((point, idx) => (
            <div key={idx} className="flex flex-col items-center gap-0.5 flex-1" title={`${point.temperature}°C / ${cToF(point.temperature)}°F → ${point.fan_percent}%`}>
              <div
                className={cn(
                  'w-full rounded-sm transition-all',
                  profile.is_active ? 'bg-primary/60' : 'bg-muted-foreground/40',
                )}
                style={{ height: `${Math.max(4, (point.fan_percent / 100) * 40)}px` }}
              />
              <span className="text-[8px] text-muted-foreground leading-none">
                {point.temperature}°C
              </span>
            </div>
          ))}
        </div>
        {/* Tabela detalhada */}
        <div className="grid grid-cols-4 gap-0.5 mt-1">
          {profile.curve.map((p, i) => (
            <div key={i} className="text-center text-[9px] text-muted-foreground/70 font-mono">
              {p.fan_percent}%
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Componente principal — FanProfiles
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function FanProfiles() {
  const profiles = useHardwareStore((s) => s.profiles)
  const activateProfile = useHardwareStore((s) => s.activateProfile)
  const fetchProfiles = useHardwareStore((s) => s.fetchProfiles)

  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editingProfile, setEditingProfile] = useState<FanProfile | null>(null)
  const [showTemplates, setShowTemplates] = useState(false)
  const [templateValues, setTemplateValues] = useState<ProfileTemplate | null>(null)

  const handleActivate = async (id: string) => {
    setLoading(true)
    try { await activateProfile(id) } finally { setLoading(false) }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Tem certeza que deseja excluir este perfil?')) return
    setLoading(true)
    try {
      await api.deleteProfile(id)
      await fetchProfiles()
    } finally { setLoading(false) }
  }

  const handleEdit = (profile: FanProfile) => {
    setShowForm(false)
    setTemplateValues(null)
    setEditingProfile(profile)
  }

  const handleReset = async (id: string) => {
    if (!confirm('Restaurar este perfil à configuração original? Suas alterações serão perdidas.')) return
    setLoading(true)
    try {
      await api.resetProfile(id)
      await fetchProfiles()
    } finally { setLoading(false) }
  }

  const handleSaved = async () => {
    await fetchProfiles()
    setShowForm(false)
    setEditingProfile(null)
    setTemplateValues(null)
  }

  const handleCancelEdit = () => {
    setEditingProfile(null)
    setShowForm(false)
    setTemplateValues(null)
  }

  const handleUseTemplate = (t: ProfileTemplate) => {
    setEditingProfile(null)
    setTemplateValues(t)
    setShowForm(true)
    setShowTemplates(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-foreground">Perfis de Ventoinha</h1>
        {!showForm && !editingProfile && (
          <div className="flex gap-2">
            <button
              onClick={() => { setShowTemplates((v) => !v); setShowForm(false) }}
              className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-muted/50 transition-colors"
            >
              Modelos prontos
            </button>
            <button
              onClick={() => { setShowForm(true); setShowTemplates(false); setTemplateValues(null) }}
              className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-opacity hover:opacity-90"
            >
              <Plus className="h-3.5 w-3.5" />
              Novo Perfil
            </button>
          </div>
        )}
      </div>

      <LiveMonitorPanel />

      <GuidePanel />

      {showTemplates && (
        <div className="space-y-3">
          <p className="text-sm font-semibold text-foreground">Modelos prontos — clique em "Usar este modelo" para preencher o formulário:</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {PROFILE_TEMPLATES.map((t) => (
              <TemplateCard key={t.name} template={t} onUse={handleUseTemplate} />
            ))}
          </div>
        </div>
      )}

      {(showForm || editingProfile) && (
        <ProfileForm
          initialProfile={editingProfile ?? undefined}
          initialValues={templateValues ? {
            name: templateValues.name,
            description: templateValues.description,
            sensor_source: templateValues.sensor_source,
            curve: templateValues.curve,
          } : undefined}
          onSaved={handleSaved}
          onCancel={handleCancelEdit}
        />
      )}

      {/* Estado vazio */}
      {profiles.length === 0 && (
        <HardwareCard
          title="Sem perfis"
          icon={<Wind className="h-4 w-4 text-muted-foreground" />}
        >
          <p className="text-sm text-muted-foreground">
            Nenhum perfil carregado. Verifique a conexão com o servidor.
          </p>
        </HardwareCard>
      )}

      {/* Grade de perfis */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {profiles.map((profile) => (
          <ProfileCard
            key={profile.id}
            profile={profile}
            onActivate={handleActivate}
            onDelete={handleDelete}
            onEdit={handleEdit}
            onReset={handleReset}
            loading={loading}
          />
        ))}
      </div>
    </div>
  )
}

