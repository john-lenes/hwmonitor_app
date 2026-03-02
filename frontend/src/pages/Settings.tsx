/**
 * Página de configurações da aplicação.
 * Exibe detalhes de conexão, variáveis de ambiente e informações da versão.
 */

import { useState } from 'react'
import { Settings2, Wifi, Info, RefreshCw } from 'lucide-react'
import { useHardwareStore } from '@/store/hardwareStore'
import HardwareCard from '@/components/dashboard/HardwareCard'
import { cn } from '@/lib/utils'

// ─────────────────────────────────────────────────────────────
// Leitura de variáveis de ambiente em tempo de build (Vite)
// ─────────────────────────────────────────────────────────────
const DEFAULT_API_URL = 'http://127.0.0.1:8765'
const DEFAULT_WS_URL = `ws://${window.location.hostname}:8765/ws`

const configuredApiUrl =
  (import.meta.env.VITE_API_URL as string | undefined) ?? DEFAULT_API_URL

const configuredWsUrl =
  (import.meta.env.VITE_WS_URL as string | undefined) ?? DEFAULT_WS_URL

// ─────────────────────────────────────────────────────────────
// Subcomponente: linha de configuração (chave → valor)
// ─────────────────────────────────────────────────────────────
interface ConfigRowProps {
  label: string
  value: string
  description?: string
  mono?: boolean
}

function ConfigRow({ label, value, description, mono = false }: ConfigRowProps) {
  return (
    <div className="flex flex-col gap-0.5 py-3 border-b border-border last:border-0">
      <div className="flex items-start justify-between gap-4">
        <span className="text-sm font-medium text-foreground">{label}</span>
        <span
          className={cn(
            'text-sm text-right break-all',
            mono ? 'font-mono text-primary' : 'text-muted-foreground',
          )}
        >
          {value}
        </span>
      </div>
      {description && (
        <p className="text-[11px] text-muted-foreground">{description}</p>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Componente de badge de status da conexão
// ─────────────────────────────────────────────────────────────
const STATUS_LABELS: Record<string, { label: string; className: string }> = {
  connected:    { label: 'Conectado',      className: 'bg-green-500/20 text-green-400' },
  connecting:   { label: 'Conectando…',    className: 'bg-yellow-500/20 text-yellow-400' },
  disconnected: { label: 'Desconectado',   className: 'bg-muted text-muted-foreground' },
  error:        { label: 'Erro',           className: 'bg-destructive/20 text-destructive' },
}

// ─────────────────────────────────────────────────────────────
// Página principal – Settings
// ─────────────────────────────────────────────────────────────
export default function Settings() {
  const status = useHardwareStore((s) => s.status)
  const connect = useHardwareStore((s) => s.connect)
  const disconnect = useHardwareStore((s) => s.disconnect)
  const snapshot = useHardwareStore((s) => s.snapshot)

  const [reconnecting, setReconnecting] = useState(false)

  const { label: statusLabel, className: statusClass } =
    STATUS_LABELS[status] ?? STATUS_LABELS['disconnected']

  /** Força reconexão ao backend WebSocket. */
  const handleReconnect = async () => {
    setReconnecting(true)
    disconnect()
    // Aguarda 500 ms para garantir que a conexão anterior seja encerrada
    await new Promise((resolve) => setTimeout(resolve, 500))
    connect()
    setReconnecting(false)
  }

  const lastUpdate = snapshot
    ? new Date(snapshot.timestamp * 1000).toLocaleString('pt-BR')
    : '—'

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-xl font-semibold text-foreground">Configurações</h1>

      {/* ── Conexão ── */}
      <HardwareCard
        title="Conexão com o backend"
        icon={<Wifi className="h-4 w-4 text-blue-400" />}
        accent="blue"
      >
        {/* Badge de status */}
        <div className="flex items-center justify-between mb-4">
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold',
              statusClass,
            )}
          >
            <span className={cn('h-1.5 w-1.5 rounded-full', {
              'bg-green-400':          status === 'connected',
              'bg-yellow-400':         status === 'connecting',
              'bg-muted-foreground':   status === 'disconnected',
              'bg-destructive':        status === 'error',
            })} />
            {statusLabel}
          </span>

          <button
            onClick={handleReconnect}
            disabled={reconnecting || status === 'connecting'}
            className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', reconnecting && 'animate-spin')} />
            Reconectar
          </button>
        </div>

        <ConfigRow
          label="URL da API REST"
          value={configuredApiUrl}
          description="Defina VITE_API_URL no arquivo .env para alterar."
          mono
        />
        <ConfigRow
          label="URL do WebSocket"
          value={configuredWsUrl}
          description="Defina VITE_WS_URL no arquivo .env para alterar."
          mono
        />
        <ConfigRow
          label="Último dado recebido"
          value={lastUpdate}
        />
      </HardwareCard>

      {/* ── Como configurar ── */}
      <HardwareCard
        title="Variáveis de ambiente"
        icon={<Settings2 className="h-4 w-4 text-amber-400" />}
        accent="amber"
      >
        <p className="text-xs text-muted-foreground mb-3">
          Crie um arquivo <code className="font-mono bg-muted px-1 rounded">.env</code> na
          pasta <code className="font-mono bg-muted px-1 rounded">frontend/</code> com as
          variáveis abaixo para customizar os endpoints:
        </p>
        <pre className="rounded-lg bg-muted/60 p-4 text-xs font-mono text-foreground leading-relaxed overflow-x-auto">
{`# URL base da API REST do backend
VITE_API_URL=http://127.0.0.1:8765

# URL do WebSocket para dados em tempo real
VITE_WS_URL=ws://127.0.0.1:8765/ws`}
        </pre>
      </HardwareCard>

      {/* ── Sobre ── */}
      <HardwareCard
        title="Sobre"
        icon={<Info className="h-4 w-4 text-purple-400" />}
        accent="purple"
      >
        <ConfigRow label="Aplicação" value="HardwareMonitor" />
        <ConfigRow label="Versão" value="1.0.0" mono />
        <ConfigRow
          label="Stack"
          value="React 18 · Vite · TypeScript · Tailwind CSS · FastAPI · WebSocket"
        />
        <ConfigRow
          label="Monitoramento"
          value="psutil · lm-sensors (Linux) · LibreHardwareMonitor (Windows)"
        />
      </HardwareCard>
    </div>
  )
}
