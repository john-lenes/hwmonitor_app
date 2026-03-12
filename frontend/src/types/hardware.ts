// Tipos TypeScript espelhando os modelos Pydantic do backend

export interface TemperatureSensor {
  label: string
  current: number
  high: number | null
  critical: number | null
}

export interface TemperatureComponent {
  component: string
  sensors: TemperatureSensor[]
}

export interface CpuStats {
  usage_percent: number
  per_core: number[]
  frequency_mhz: number | null
  temperature: number | null
  /** Motivo pelo qual a temperatura não está disponível. 'run_as_admin' = precisa de privilégio Admin. */
  temperature_note?: string | null
}

export interface MemorySlot {
  device_locator: string
  size_gb: number
  speed_mhz: number | null
  manufacturer: string | null
  part_number: string | null
  form_factor: string | null
  memory_type: string | null
}

export interface MemoryStats {
  total_gb: number
  used_gb: number
  available_gb: number
  percent: number
  /** Total físico real via dmidecode (soma dos slots instalados). */
  hardware_total_gb: number | null
  /** Detalhes de cada slot físico de memória. */
  slots: MemorySlot[]
}

export interface DiskStats {
  device: string
  mountpoint: string
  total_gb: number
  used_gb: number
  percent: number
  /** Modelo do disco físico (ex: Samsung SSD 870 EVO). */
  model?: string | null
  /** Tipo de mídia: NVMe | SSD | HDD | Unknown. */
  media_type?: string | null
  /** Capacidade real do disco físico em GB (pode diferir do volume lógico). */
  physical_size_gb?: number | null
}

export interface GpuStats {
  name: string
  load_percent: number
  memory_used_mb: number
  memory_total_mb: number
  temperature: number | null
  vendor: string | null
  driver_version: string | null
  vram_gb: number | null
}

export interface HardwareSnapshot {
  timestamp: number
  cpu: CpuStats
  memory: MemoryStats
  disks: DiskStats[]
  gpus: GpuStats[]
  temperatures: TemperatureComponent[]
}

export interface FanReading {
  id: string
  label: string
  rpm: number
  min_rpm: number | null
  /** RPM máximo observado/registrado (histórico do backend). */
  max_rpm: number | null
  percent: number | null
  controllable: boolean
  /** Modo de velocidade ativo: 'auto' | 'quiet' | 'balanced' | 'turbo' */
  speed_mode?: string | null
}

export interface CurvePoint {
  temperature: number
  fan_percent: number
}

export interface FanProfile {
  id: string
  name: string
  description: string | null
  sensor_source: string
  curve: CurvePoint[]
  is_active: boolean
  is_builtin: boolean
}

export interface FanProfileCreate {
  name: string
  description?: string
  sensor_source: string
  curve: CurvePoint[]
}

export interface FanProfileUpdate {
  name?: string
  description?: string
  sensor_source?: string
  curve?: CurvePoint[]
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'
