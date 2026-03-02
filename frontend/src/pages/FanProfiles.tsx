/**
 * Página de gerenciamento de perfis de ventoinha.
 * Permite visualizar, criar, editar, excluir e ativar perfis de curva de velocidade.
 */

import { useState } from 'react'
import { Wind, CheckCircle2, Trash2, Plus, Zap } from 'lucide-react'
import { useHardwareStore } from '@/store/hardwareStore'
import { api } from '@/services/api'
import { cn } from '@/lib/utils'
import type { FanProfile, FanProfileCreate, CurvePoint } from '@/types/hardware'
import HardwareCard from '@/components/dashboard/HardwareCard'

// ─────────────────────────────────────────────────────────────
// Subcomponente: card de perfil individual
// ─────────────────────────────────────────────────────────────
interface ProfileCardProps {
  profile: FanProfile
  onActivate: (id: string) => void
  onDelete: (id: string) => void
  loading: boolean
}

function ProfileCard({ profile, onActivate, onDelete, loading }: ProfileCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border p-5 space-y-3 transition-all',
        profile.is_active
          ? 'border-primary/60 bg-primary/5'
          : 'border-border bg-card',
      )}
    >
      {/* Cabeçalho */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
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
        <div className="flex items-center gap-1.5 shrink-0">
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

      {/* Sensor de origem */}
      <p className="text-[11px] text-muted-foreground font-mono">
        Sensor: {profile.sensor_source}
      </p>

      {/* Visualização da curva de temperatura */}
      <div className="space-y-1">
        <p className="text-[11px] font-medium text-muted-foreground">Curva de velocidade</p>
        <div className="flex items-end gap-1 h-12">
          {profile.curve.map((point, idx) => (
            <div key={idx} className="flex flex-col items-center gap-0.5 flex-1">
              <div
                className={cn(
                  'w-full rounded-sm transition-all',
                  profile.is_active ? 'bg-primary/60' : 'bg-muted-foreground/40',
                )}
                style={{ height: `${Math.max(4, (point.fan_percent / 100) * 40)}px` }}
              />
              <span className="text-[8px] text-muted-foreground leading-none">
                {point.temperature}°
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Subcomponente: formulário de novo perfil
// ─────────────────────────────────────────────────────────────
interface NewProfileFormProps {
  onCreated: () => void
  onCancel: () => void
}

/** Ponto padrão de curva para novos perfis. */
const DEFAULT_CURVE: CurvePoint[] = [
  { temperature: 0,  fan_percent: 20  },
  { temperature: 50, fan_percent: 40  },
  { temperature: 70, fan_percent: 70  },
  { temperature: 85, fan_percent: 100 },
]

function NewProfileForm({ onCreated, onCancel }: NewProfileFormProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [sensorSource, setSensorSource] = useState('cpu_package')
  const [curve, setCurve] = useState<CurvePoint[]>(DEFAULT_CURVE)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /** Atualiza um ponto específico da curva. */
  const updateCurvePoint = (idx: number, field: keyof CurvePoint, value: number) => {
    setCurve((prev) =>
      prev.map((p, i) => (i === idx ? { ...p, [field]: value } : p)),
    )
  }

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('O nome do perfil é obrigatório.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const payload: FanProfileCreate = {
        name: name.trim(),
        description: description.trim() || undefined,
        sensor_source: sensorSource,
        curve,
      }
      await api.createProfile(payload)
      onCreated()
    } catch {
      setError('Erro ao criar perfil. Verifique os dados e tente novamente.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-xl border border-primary/40 bg-primary/5 p-5 space-y-4">
      <h3 className="text-sm font-semibold text-foreground">Novo Perfil</h3>

      {error && (
        <p className="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {error}
        </p>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {/* Nome */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">Nome *</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Meu perfil silencioso"
            className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* Sensor */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">Sensor de origem</label>
          <input
            value={sensorSource}
            onChange={(e) => setSensorSource(e.target.value)}
            placeholder="cpu_package"
            className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm font-mono text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* Descrição */}
        <div className="space-y-1 sm:col-span-2">
          <label className="text-xs font-medium text-muted-foreground">Descrição (opcional)</label>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Descrição do perfil…"
            className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
      </div>

      {/* Curva de temperatura */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-muted-foreground">
          Curva de temperatura → velocidade (°C → %)
        </p>
        <div className="space-y-2">
          {curve.map((point, idx) => (
            <div key={idx} className="flex items-center gap-3 text-xs">
              <span className="w-6 text-center text-muted-foreground">{idx + 1}.</span>
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min={0}
                  max={110}
                  value={point.temperature}
                  onChange={(e) => updateCurvePoint(idx, 'temperature', Number(e.target.value))}
                  className="w-16 rounded border border-border bg-background px-2 py-1 font-mono text-center text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <span className="text-muted-foreground">°C →</span>
              </div>
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={point.fan_percent}
                  onChange={(e) => updateCurvePoint(idx, 'fan_percent', Number(e.target.value))}
                  className="w-16 rounded border border-border bg-background px-2 py-1 font-mono text-center text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <span className="text-muted-foreground">%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Botões */}
      <div className="flex gap-2 pt-1">
        <button
          onClick={handleSubmit}
          disabled={saving}
          className="flex-1 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-opacity disabled:opacity-50"
        >
          {saving ? 'Salvando…' : 'Criar perfil'}
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

// ─────────────────────────────────────────────────────────────
// Componente principal – FanProfiles
// ─────────────────────────────────────────────────────────────
export default function FanProfiles() {
  const profiles = useHardwareStore((s) => s.profiles)
  const activateProfile = useHardwareStore((s) => s.activateProfile)
  const fetchProfiles = useHardwareStore((s) => s.fetchProfiles)

  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)

  /** Ativa um perfil e atualiza o estado global. */
  const handleActivate = async (id: string) => {
    setLoading(true)
    try {
      await activateProfile(id)
    } finally {
      setLoading(false)
    }
  }

  /** Exclui um perfil do usuário após confirmação. */
  const handleDelete = async (id: string) => {
    if (!confirm('Tem certeza que deseja excluir este perfil?')) return
    setLoading(true)
    try {
      await api.deleteProfile(id)
      await fetchProfiles()
    } finally {
      setLoading(false)
    }
  }

  /** Recarrega perfis após criação de um novo. */
  const handleCreated = async () => {
    await fetchProfiles()
    setShowForm(false)
  }

  return (
    <div className="space-y-6">
      {/* Cabeçalho da página */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-foreground">Perfis de Ventoinha</h1>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-opacity hover:opacity-90"
          >
            <Plus className="h-3.5 w-3.5" />
            Novo Perfil
          </button>
        )}
      </div>

      {/* Formulário de criação de novo perfil */}
      {showForm && (
        <NewProfileForm
          onCreated={handleCreated}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* Estado vazio */}
      {profiles.length === 0 && (
        <HardwareCard
          title="Sem perfis"
          icon={<Wind className="h-4 w-4 text-muted-foreground" />}
        >
          <p className="text-sm text-muted-foreground">
            Nenhum perfil de ventoinha foi carregado. Verifique a conexão com o backend.
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
            loading={loading}
          />
        ))}
      </div>
    </div>
  )
}
