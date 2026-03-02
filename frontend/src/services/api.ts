import axios from 'axios'
import type {
  FanProfile,
  FanProfileCreate,
  FanProfileUpdate,
  FanReading,
  HardwareSnapshot,
} from '@/types/hardware'

const BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://127.0.0.1:8765'

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})

export const api = {
  // ── Hardware ──────────────────────────────────────────────────────────────
  /** Retorna o snapshot mais recente de hardware. */
  async getSnapshot(): Promise<HardwareSnapshot> {
    const { data } = await client.get<HardwareSnapshot>('/api/hardware/snapshot')
    return data
  },

  // ── Ventoinhas ────────────────────────────────────────────────────────────
  /** Retorna todas as ventoinhas detectadas e suas leituras atuais. */
  async getFans(): Promise<FanReading[]> {
    const { data } = await client.get<FanReading[]>('/api/fans/')
    return data
  },

  async setFanSpeed(fanId: string, percent: number): Promise<void> {
    await client.post(`/api/fans/${fanId}/speed`, { fan_id: fanId, percent })
  },

  async restoreFanAuto(fanId: string): Promise<void> {
    await client.post(`/api/fans/${fanId}/auto`)
  },

  async restoreAllFansAuto(): Promise<void> {
    await client.post('/api/fans/auto')
  },

  // ── Perfis ────────────────────────────────────────────────────────────────
  /** Retorna todos os perfis de ventoinha (padrões + personalizados). */
  async getProfiles(): Promise<FanProfile[]> {
    const { data } = await client.get<FanProfile[]>('/api/profiles/')
    return data
  },

  async getActiveProfile(): Promise<FanProfile> {
    const { data } = await client.get<FanProfile>('/api/profiles/active')
    return data
  },

  async createProfile(payload: FanProfileCreate): Promise<FanProfile> {
    const { data } = await client.post<FanProfile>('/api/profiles/', payload)
    return data
  },

  async updateProfile(id: string, payload: FanProfileUpdate): Promise<FanProfile> {
    const { data } = await client.put<FanProfile>(`/api/profiles/${id}`, payload)
    return data
  },

  async deleteProfile(id: string): Promise<void> {
    await client.delete(`/api/profiles/${id}`)
  },

  async activateProfile(id: string): Promise<FanProfile> {
    const { data } = await client.post<FanProfile>(`/api/profiles/${id}/activate`)
    return data
  },
}
