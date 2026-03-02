import { create } from 'zustand'
import { immer } from 'zustand/middleware/immer'
import type {
  ConnectionStatus,
  FanProfile,
  FanReading,
  HardwareSnapshot,
} from '@/types/hardware'
import { api } from '@/services/api'

/** Número máximo de entradas no histórico (~2 min com intervalo de 2 s). */
const MAX_HISTORY = 60

interface HistoryEntry {
  timestamp: number
  cpuTemp: number | null
  cpuUsage: number
  memPercent: number
  gpuTemp: number | null
}

interface HardwareState {
  // Connection
  status: ConnectionStatus
  ws: WebSocket | null
  connect: () => void
  disconnect: () => void

  // Live data
  snapshot: HardwareSnapshot | null
  history: HistoryEntry[]
  fans: FanReading[]
  profiles: FanProfile[]

  // Actions
  fetchFans: () => Promise<void>
  fetchProfiles: () => Promise<void>
  activateProfile: (id: string) => Promise<void>
  setFanSpeed: (fanId: string, percent: number) => Promise<void>
  restoreFanAuto: (fanId: string) => Promise<void>
}

const WS_URL =
  (import.meta.env.VITE_WS_URL as string | undefined) ??
  `ws://${window.location.hostname}:8765/ws`

export const useHardwareStore = create<HardwareState>()(
  immer((set, get) => ({
    status: 'disconnected',
    ws: null,
    snapshot: null,
    history: [],
    fans: [],
    profiles: [],

    connect() {
      if (get().ws) return
      set((s) => { s.status = 'connecting' })

      const ws = new WebSocket(WS_URL)

      ws.onopen = () => {
        set((s) => { s.status = 'connected' })
        // Busca inicial de dados
        get().fetchFans()
        get().fetchProfiles()
      }

      ws.onmessage = (event) => {
        try {
          const snapshot: HardwareSnapshot = JSON.parse(event.data)
          set((s) => {
            s.snapshot = snapshot
            const entry: HistoryEntry = {
              timestamp: snapshot.timestamp,
              cpuTemp: snapshot.cpu.temperature,
              cpuUsage: snapshot.cpu.usage_percent,
              memPercent: snapshot.memory.percent,
              gpuTemp: snapshot.gpus[0]?.temperature ?? null,
            }
            s.history.push(entry)
            if (s.history.length > MAX_HISTORY) {
              s.history.splice(0, s.history.length - MAX_HISTORY)
            }
          })
        } catch {
          // ignora erros de parse de mensagens WebSocket
        }
      }

      ws.onerror = () => {
        set((s) => { s.status = 'error' })
      }

      ws.onclose = () => {
        set((s) => {
          s.status = 'disconnected'
          s.ws = null
        })
        // Reconexão automática após 3 segundos
        setTimeout(() => {
          if (get().status === 'disconnected') {
            get().connect()
          }
        }, 3000)
      }

      set((s) => { s.ws = ws })
    },

    disconnect() {
      const ws = get().ws
      if (ws) {
        ws.close()
        set((s) => { s.ws = null; s.status = 'disconnected' })
      }
    },

    /** Busca a lista de ventoinhas detectadas pelo backend. */
    async fetchFans() {
      try {
        const fans = await api.getFans()
        set((s) => { s.fans = fans })
      } catch {
        // ignora silenciosamente falhas temporárias de rede
      }
    },

    /** Busca todos os perfis de ventoinha do backend. */
    async fetchProfiles() {
      try {
        const profiles = await api.getProfiles()
        set((s) => { s.profiles = profiles })
      } catch {
        // ignora silenciosamente falhas temporárias de rede
      }
    },

    async activateProfile(id: string) {
      const profile = await api.activateProfile(id)
      set((s) => {
        s.profiles.forEach((p) => { p.is_active = false })
        const idx = s.profiles.findIndex((p) => p.id === id)
        if (idx !== -1) s.profiles[idx] = profile
      })
    },

    async setFanSpeed(fanId: string, percent: number) {
      await api.setFanSpeed(fanId, percent)
      await get().fetchFans()
    },

    async restoreFanAuto(fanId: string) {
      await api.restoreFanAuto(fanId)
      await get().fetchFans()
    },
  })),
)
