/**
 * Página principal do painel de monitoramento de hardware.
 * Exibe dados em tempo real de CPU, memória, discos, GPUs e ventoinhas.
 */

import { useMemo } from 'react'
import { Cpu, MemoryStick, HardDrive, Thermometer, Wind } from 'lucide-react'
import { useHardwareStore } from '@/store/hardwareStore'
import HardwareCard from '@/components/dashboard/HardwareCard'
import TemperatureGauge from '@/components/dashboard/TemperatureGauge'
import UsageBar from '@/components/dashboard/UsageBar'
import HistoryChart from '@/components/dashboard/HistoryChart'
import FanSpeedControl from '@/components/dashboard/FanSpeedControl'

export default function Dashboard() {
  const snapshot = useHardwareStore((s) => s.snapshot)
  const fans = useHardwareStore((s) => s.fans)
  const fanRpmHistory = useHardwareStore((s) => s.fanRpmHistory)
  const status = useHardwareStore((s) => s.status)

  // Temperatura do pacote CPU a partir do mapa de sensores
  // (computado antes do early return para obedecer as Rules of Hooks)
  const cpuPackageTemp = useMemo(() => {
    if (!snapshot) return null
    const { cpu, temperatures } = snapshot
    return (
      cpu.temperature ??
      temperatures
        .flatMap((t) => t.sensors)
        .find((s) => /package|tdie|cpu temp/i.test(s.label))?.current ??
      null
    )
  }, [snapshot])

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

  const { cpu, memory, disks, gpus } = snapshot

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
            <div className="flex flex-col items-center gap-1">
              <TemperatureGauge
                label="Temperatura"
                temperature={cpuPackageTemp}
                size="md"
              />
              {cpuPackageTemp === null && cpu.temperature_note === 'run_as_admin' && (
                <span className="rounded bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-400">
                  Admin necessário
                </span>
              )}
            </div>
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
          subtitle={
            memory.hardware_total_gb
              ? `${memory.hardware_total_gb} GB físico (${memory.slots.length} slot${memory.slots.length !== 1 ? 's' : ''})`
              : `${memory.total_gb} GB visível`
          }
          icon={<MemoryStick className="h-4 w-4 text-purple-400" />}
          accent="purple"
        >
          <div className="space-y-4 pt-2">
            {memory.hardware_total_gb && memory.hardware_total_gb !== memory.total_gb && (
              <p className="text-[11px] text-amber-400 bg-amber-500/10 rounded px-2 py-1">
                ⚠ Container vê {memory.total_gb} GB (limite do VM). Físico real:{' '}
                <strong>{memory.hardware_total_gb} GB</strong>
              </p>
            )}
            <UsageBar
              label="Usada"
              value={memory.used_gb}
              max={memory.hardware_total_gb ?? memory.total_gb}
              unit=" GB"
              showPercent
            />
            <UsageBar
              label="Disponível"
              value={memory.available_gb}
              max={memory.hardware_total_gb ?? memory.total_gb}
              unit=" GB"
              showPercent={false}
            />
            <UsageBar label="Uso" value={memory.percent} />
            {memory.slots.length > 0 && (
              <div className="space-y-1 pt-1">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Slots</p>
                {memory.slots.map((slot, i) => (
                  <div key={i} className="flex items-center justify-between text-[11px]">
                    <span className="text-muted-foreground font-mono">
                      {slot.device_locator || `Slot ${i + 1}`}
                    </span>
                    <span className="font-semibold">
                      {slot.size_gb} GB
                      {slot.speed_mhz ? ` · ${slot.speed_mhz} MHz` : ''}
                      {slot.memory_type ? ` · ${slot.memory_type}` : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </HardwareCard>

        {/* GPU (primeira detectada) */}
        {gpus.length > 0 ? (
          <HardwareCard
            title={gpus[0].name}
            subtitle={
              [
                gpus[0].vendor ?? 'GPU',
                gpus[0].vram_gb ? `${gpus[0].vram_gb} GB VRAM` : null,
                gpus[0].driver_version ? `Driver ${gpus[0].driver_version}` : null,
              ]
                .filter(Boolean)
                .join(' · ')
            }
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
                {gpus[0].memory_total_mb > 0 && (
                  <UsageBar
                    label="VRAM"
                    value={gpus[0].memory_used_mb}
                    max={gpus[0].memory_total_mb}
                    unit=" MB"
                    showPercent
                  />
                )}
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
              Nenhuma GPU compatível encontrada. Detectadas via GPUtil (NVIDIA),
              sysfs DRM (AMD/Intel) ou lspci.
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
                  <div className="min-w-0">
                    <span className="text-xs font-semibold text-foreground block">
                      {disk.mountpoint}
                    </span>
                    {disk.model && (
                      <span className="text-[10px] text-muted-foreground truncate block" title={disk.model}>
                        {disk.model}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-0.5 shrink-0">
                    {disk.media_type && (
                      <span className={[
                        'rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider',
                        disk.media_type === 'NVMe' ? 'bg-purple-500/20 text-purple-400' :
                        disk.media_type === 'SSD'  ? 'bg-blue-500/20 text-blue-400' :
                        disk.media_type === 'HDD'  ? 'bg-amber-500/20 text-amber-400' :
                        'bg-muted text-muted-foreground',
                      ].join(' ')}>
                        {disk.media_type}
                      </span>
                    )}
                    {disk.physical_size_gb && (
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {disk.physical_size_gb} GB fís.
                      </span>
                    )}
                  </div>
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
              <FanSpeedControl key={fan.id} fan={fan} rpmHistory={fanRpmHistory[fan.id]} />
            ))}
          </div>
        </HardwareCard>
      )}
    </div>
  )
}
