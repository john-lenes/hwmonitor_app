/**
 * Página principal do painel de monitoramento de hardware.
 * Exibe dados em tempo real de CPU, memória, discos, GPUs e ventoinhas.
 */

import { Cpu, MemoryStick, HardDrive, Thermometer, Wind } from 'lucide-react'
import { useHardwareStore } from '@/store/hardwareStore'
import HardwareCard from '@/components/dashboard/HardwareCard'
import TemperatureGauge from '@/components/dashboard/TemperatureGauge'
import UsageBar from '@/components/dashboard/UsageBar'
import HistoryChart from '@/components/dashboard/HistoryChart'
import FanSpeedControl from '@/components/dashboard/FanSpeedControl'
import { formatBytes } from '@/lib/utils'

export default function Dashboard() {
  const snapshot = useHardwareStore((s) => s.snapshot)
  const fans = useHardwareStore((s) => s.fans)
  const status = useHardwareStore((s) => s.status)

  // Exibe mensagem enquanto aguarda o primeiro snapshot
  if (!snapshot) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-2">
          <div className="text-muted-foreground text-sm">
            {status === 'connecting'
              ? 'Conectando ao servidor…'
              : status === 'error'
              ? 'Erro na conexão com o backend.'
              : 'Aguardando dados de hardware…'}
          </div>
        </div>
      </div>
    )
  }

  const { cpu, memory, disks, gpus, temperatures } = snapshot

  // Temperatura do pacote CPU a partir do mapa de sensores
  const cpuPackageTemp =
    cpu.temperature ??
    temperatures
      .flatMap((t) => t.sensors)
      .find((s) => /package|tdie|cpu temp/i.test(s.label))?.current ??
    null

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-foreground">Painel</h1>

      {/* ── Linha 1: CPU, Memória, GPU ── */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {/* CPU */}
        <HardwareCard
          title="CPU"
          subtitle={`${cpu.per_core.length} núcleos${cpu.frequency_mhz ? ` · ${(cpu.frequency_mhz / 1000).toFixed(2)} GHz` : ''}`}
          icon={<Cpu className="h-4 w-4 text-blue-400" />}
          accent="blue"
        >
          <div className="flex items-center gap-6">
            <TemperatureGauge
              label="Temperatura"
              temperature={cpuPackageTemp}
              size="md"
            />
            <div className="flex-1 space-y-3">
              <UsageBar label="Uso total" value={cpu.usage_percent} />
              {cpu.per_core.slice(0, 4).map((v, i) => (
                <UsageBar
                  key={i}
                  label={`Núcleo ${i}`}
                  value={v}
                />
              ))}
              {cpu.per_core.length > 4 && (
                <p className="text-[10px] text-muted-foreground">
                  +{cpu.per_core.length - 4} núcleos omitidos
                </p>
              )}
            </div>
          </div>
        </HardwareCard>

        {/* Memória */}
        <HardwareCard
          title="Memória RAM"
          subtitle={`${formatBytes(memory.total_gb)} total`}
          icon={<MemoryStick className="h-4 w-4 text-purple-400" />}
          accent="purple"
        >
          <div className="space-y-4 pt-2">
            <UsageBar
              label="Usada"
              value={memory.used_gb}
              max={memory.total_gb}
              unit=" GB"
              showPercent
            />
            <UsageBar
              label="Disponível"
              value={memory.available_gb}
              max={memory.total_gb}
              unit=" GB"
              showPercent={false}
            />
            <UsageBar
              label="Uso"
              value={memory.percent}
            />
          </div>
        </HardwareCard>

        {/* GPU (primeira detectada) */}
        {gpus.length > 0 ? (
          <HardwareCard
            title={gpus[0].name}
            subtitle="GPU"
            icon={<Thermometer className="h-4 w-4 text-amber-400" />}
            accent="amber"
          >
            <div className="flex items-center gap-6">
              <TemperatureGauge
                label="Temperatura"
                temperature={gpus[0].temperature}
                size="md"
              />
              <div className="flex-1 space-y-3">
                <UsageBar label="Carga" value={gpus[0].load_percent} />
                <UsageBar
                  label="VRAM"
                  value={gpus[0].memory_used_mb}
                  max={gpus[0].memory_total_mb}
                  unit=" MB"
                  showPercent
                />
              </div>
            </div>
          </HardwareCard>
        ) : (
          <HardwareCard
            title="GPU"
            subtitle="Nenhuma GPU detectada"
            icon={<Thermometer className="h-4 w-4 text-amber-400" />}
            accent="amber"
          >
            <p className="text-sm text-muted-foreground">
              Nenhuma GPU compatível foi encontrada. GPUs NVIDIA requerem GPUtil.
            </p>
          </HardwareCard>
        )}
      </div>

      {/* ── Linha 2: Histórico ── */}
      <HardwareCard
        title="Histórico (últimos 2 min)"
        subtitle="Temperatura e uso ao longo do tempo"
        icon={<Thermometer className="h-4 w-4 text-green-400" />}
        accent="green"
      >
        <HistoryChart />
      </HardwareCard>

      {/* ── Linha 3: Discos ── */}
      {disks.length > 0 && (
        <HardwareCard
          title="Armazenamento"
          subtitle={`${disks.length} partição${disks.length !== 1 ? 'ões' : ''} detectada${disks.length !== 1 ? 's' : ''}`}
          icon={<HardDrive className="h-4 w-4 text-green-400" />}
          accent="green"
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {disks.map((disk) => (
              <div
                key={disk.mountpoint}
                className="rounded-lg border border-border bg-muted/30 p-3 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-foreground">
                    {disk.mountpoint}
                  </span>
                  <span className="text-[10px] text-muted-foreground font-mono">
                    {disk.device}
                  </span>
                </div>
                <UsageBar
                  label="Usado"
                  value={disk.used_gb}
                  max={disk.total_gb}
                  unit=" GB"
                  showPercent
                />
              </div>
            ))}
          </div>
        </HardwareCard>
      )}

      {/* ── Linha 4: Ventoinhas ── */}
      {fans.length > 0 && (
        <HardwareCard
          title="Ventoinhas"
          subtitle={`${fans.length} ventoinha${fans.length !== 1 ? 's' : ''} detectada${fans.length !== 1 ? 's' : ''}`}
          icon={<Wind className="h-4 w-4 text-blue-400" />}
          accent="blue"
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {fans.map((fan) => (
              <FanSpeedControl key={fan.id} fan={fan} />
            ))}
          </div>
        </HardwareCard>
      )}
    </div>
  )
}
