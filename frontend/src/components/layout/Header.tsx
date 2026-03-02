import { useHardwareStore } from '@/store/hardwareStore'
import { cn } from '@/lib/utils'
import { Wifi, WifiOff, RefreshCw } from 'lucide-react'

const STATUS_CONFIG = {
  connected:    { label: 'Conectado',    className: 'text-green-400',         icon: Wifi       },
  connecting:   { label: 'Conectando…',  className: 'text-yellow-400',        icon: RefreshCw  },
  disconnected: { label: 'Desconectado', className: 'text-muted-foreground',  icon: WifiOff    },
  error:        { label: 'Erro',         className: 'text-destructive',       icon: WifiOff    },
}

export default function Header() {
  const status = useHardwareStore((s) => s.status)
  const connect = useHardwareStore((s) => s.connect)
  const snapshot = useHardwareStore((s) => s.snapshot)

  const { label, className, icon: Icon } = STATUS_CONFIG[status]

  const lastUpdate = snapshot
    ? new Date(snapshot.timestamp * 1000).toLocaleTimeString()
    : '—'

  return (
    <header className="flex items-center justify-between border-b border-border bg-card px-6 py-3">
      <div className="flex items-center gap-2">
        <span
          className={cn('h-2 w-2 rounded-full', {
            'bg-green-400': status === 'connected',
            'bg-yellow-400': status === 'connecting',
            'bg-muted-foreground': status === 'disconnected',
            'bg-destructive': status === 'error',
          })}
        />
        <span className={cn('text-xs font-medium', className)}>
          <Icon className="mr-1 inline-block h-3 w-3" />
          {label}
        </span>
      </div>

      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        {snapshot && <span>Última atualização: {lastUpdate}</span>}
        {status !== 'connected' && (
          <button
            onClick={connect}
            className="rounded px-2 py-1 text-xs text-primary hover:bg-primary/10 transition-colors"
          >
            Reconectar
          </button>
        )}
      </div>
    </header>
  )
}
