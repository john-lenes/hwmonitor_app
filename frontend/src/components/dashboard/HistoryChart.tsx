import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { useHardwareStore } from '@/store/hardwareStore'

interface TooltipPayload {
  color: string
  name: string
  value: number
  unit: string
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: TooltipPayload[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-lg">
      <p className="mb-1.5 text-xs text-muted-foreground">{label}</p>
      {payload.map((p) => (
        <p key={p.name} className="text-xs font-medium" style={{ color: p.color }}>
          {p.name}: {p.value.toFixed(1)}{p.unit}
        </p>
      ))}
    </div>
  )
}

export default function HistoryChart() {
  const history = useHardwareStore((s) => s.history)

  const data = history.map((h) => ({
    time: new Date(h.timestamp * 1000).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }),
    'Temp. CPU': h.cpuTemp ?? 0,
    'Uso CPU': h.cpuUsage,
    'Memória': h.memPercent,
    'Temp. GPU': h.gpuTemp ?? 0,
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis
          dataKey="time"
          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
          domain={[0, 100]}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: '11px', color: 'hsl(var(--muted-foreground))' }}
        />
        <Line
          type="monotone"
          dataKey="Temp. CPU"
          stroke="#ef4444"
          strokeWidth={1.5}
          dot={false}
          unit="°C"
        />
        <Line
          type="monotone"
          dataKey="Uso CPU"
          stroke="#3b82f6"
          strokeWidth={1.5}
          dot={false}
          unit="%"
        />
        <Line
          type="monotone"
          dataKey="Memória"
          stroke="#a855f7"
          strokeWidth={1.5}
          dot={false}
          unit="%"
        />
        <Line
          type="monotone"
          dataKey="Temp. GPU"
          stroke="#f59e0b"
          strokeWidth={1.5}
          dot={false}
          unit="°C"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
