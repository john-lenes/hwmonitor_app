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
}

export interface MemoryStats {
  total_gb: number
  used_gb: number
  available_gb: number
  percent: number
}

export interface DiskStats {
  device: string
  mountpoint: string
  total_gb: number
  used_gb: number
  percent: number
}

export interface GpuStats {
  name: string
  load_percent: number
  memory_used_mb: number
  memory_total_mb: number
  temperature: number | null
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
  max_rpm: number | null
  percent: number | null
  controllable: boolean
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
