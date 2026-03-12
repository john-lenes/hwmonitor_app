"""Serviço de persistência e aplicação de perfis de ventoinha."""

from __future__ import annotations

import bisect
import json
import logging
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.models.profile import CurvePoint, FanProfile, FanProfileCreate, FanProfileUpdate
from app.services.fan_controller import FanController

logger = logging.getLogger(__name__)

_PROFILES_FILE = Path(settings.DATA_DIR) / "profiles.json"

# ---------------------------------------------------------------------------
# Perfis padrões integrados
# ---------------------------------------------------------------------------

_BUILTIN_PROFILES: list[FanProfile] = [
    FanProfile(
        id="builtin_silent",
        name="Silencioso",
        description="Prioriza o silêncio. Ventoinhas em baixa velocidade. Ideal para trabalho leve (navegação, textos, reuniões). Pode esquentar mais em tarefas pesadas.",
        sensor_source="cpu_package",
        curve=[
            CurvePoint(temperature=0,  fan_percent=0),
            CurvePoint(temperature=50, fan_percent=20),
            CurvePoint(temperature=65, fan_percent=40),
            CurvePoint(temperature=80, fan_percent=70),
            CurvePoint(temperature=90, fan_percent=100),
        ],
        is_builtin=True,
    ),
    FanProfile(
        id="builtin_balanced",
        name="Balanceado",
        description="Equilíbrio entre silêncio e resfriamento. Recomendado para uso diário, jogos leves e multitarefas. Ponto de partida seguro para a maioria dos usuários.",
        sensor_source="cpu_package",
        curve=[
            CurvePoint(temperature=0,  fan_percent=20),
            CurvePoint(temperature=50, fan_percent=40),
            CurvePoint(temperature=65, fan_percent=60),
            CurvePoint(temperature=75, fan_percent=80),
            CurvePoint(temperature=85, fan_percent=100),
        ],
        is_builtin=True,
        is_active=True,
    ),
    FanProfile(
        id="builtin_performance",
        name="Performance",
        description="Resfriamento máximo desde o início. Ventoinhas em alta velocidade para manter temperatura baixa. Indicado para jogos intensos, renderização e streaming. Pode ser mais barulhento.",
        sensor_source="cpu_package",
        curve=[
            CurvePoint(temperature=0,  fan_percent=50),
            CurvePoint(temperature=40, fan_percent=60),
            CurvePoint(temperature=60, fan_percent=80),
            CurvePoint(temperature=75, fan_percent=100),
        ],
        is_builtin=True,
    ),
    FanProfile(
        id="builtin_gaming_gpu",
        name="Gamer (GPU)",
        description="Controla as ventoinhas pela temperatura da placa de vídeo. Ideal para gamers onde a GPU aquece mais que o processador. Mantém a GPU fria durante sessões longas.",
        sensor_source="gpu",
        curve=[
            CurvePoint(temperature=0,  fan_percent=30),
            CurvePoint(temperature=50, fan_percent=50),
            CurvePoint(temperature=70, fan_percent=80),
            CurvePoint(temperature=80, fan_percent=100),
        ],
        is_builtin=True,
    ),
]


def _interpolate(curve: list[CurvePoint], temperature: float) -> float:
    """Interpolação linear da velocidade do fan a partir de uma curva de temperatura ordenada."""
    if not curve:
        return 50.0
    sorted_curve = sorted(curve, key=lambda p: p.temperature)
    temps = [p.temperature for p in sorted_curve]
    idx = bisect.bisect_right(temps, temperature)
    if idx == 0:
        return sorted_curve[0].fan_percent
    if idx >= len(sorted_curve):
        return sorted_curve[-1].fan_percent
    lower = sorted_curve[idx - 1]
    upper = sorted_curve[idx]
    ratio = (temperature - lower.temperature) / (upper.temperature - lower.temperature)
    return lower.fan_percent + ratio * (upper.fan_percent - lower.fan_percent)


class ProfileManager:
    """Operações CRUD e aplicação em tempo real de perfis de ventoinha."""

    def __init__(self) -> None:
        self._profiles: dict[str, FanProfile] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._profiles = {p.id: p for p in _BUILTIN_PROFILES}
        if _PROFILES_FILE.exists():
            try:
                raw: list[dict] = json.loads(_PROFILES_FILE.read_text())
                for entry in raw:
                    profile = FanProfile(**entry)
                    if not profile.is_builtin:
                        self._profiles[profile.id] = profile
            except Exception as exc:  # noqa: BLE001
                logger.error("Falha ao carregar perfis: %s", exc)

    def _save(self) -> None:
        """
        Persiste perfis no arquivo JSON.

        Salva:
        - Perfis criados pelo usuário (não-builtins)
        - Versões modificadas de perfis builtin (override)
        """
        builtin_defaults = {p.id: p for p in _BUILTIN_PROFILES}
        to_save: list[dict] = []
        for p in self._profiles.values():
            if not p.is_builtin:
                to_save.append(p.model_dump())
            else:
                # Salva apenas se diferir do original (excluindo is_active)
                original = builtin_defaults.get(p.id)
                if original:
                    orig_dump = {k: v for k, v in original.model_dump().items() if k != "is_active"}
                    curr_dump = {k: v for k, v in p.model_dump().items() if k != "is_active"}
                    if orig_dump != curr_dump:
                        to_save.append(p.model_dump())
        _PROFILES_FILE.write_text(json.dumps(to_save, indent=2, default=str))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def list_profiles(self) -> list[FanProfile]:
        """Retorna todos os perfis cadastrados."""
        return list(self._profiles.values())

    def get_profile(self, profile_id: str) -> Optional[FanProfile]:
        return self._profiles.get(profile_id)

    def create_profile(self, data: FanProfileCreate) -> FanProfile:
        profile = FanProfile(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            sensor_source=data.sensor_source,
            curve=data.curve,
        )
        self._profiles[profile.id] = profile
        self._save()
        return profile

    def update_profile(self, profile_id: str, data: FanProfileUpdate) -> Optional[FanProfile]:
        """
        Atualiza um perfil existente.

        Perfis builtin podem ser editados (suas modificações são salvas como
        overrides no arquivo JSON, mantendo o perfil original como referência).
        Para resetar um builtin ao padrão, use reset_to_default().
        """
        profile = self._profiles.get(profile_id)
        if not profile:
            return None
        updated = profile.model_copy(
            update={k: v for k, v in data.model_dump(exclude_none=True).items()}
        )
        self._profiles[profile_id] = updated
        self._save()
        return updated

    def reset_to_default(self, profile_id: str) -> Optional[FanProfile]:
        """Restaura um perfil builtin aos seus valores padrão originais."""
        original = next((p for p in _BUILTIN_PROFILES if p.id == profile_id), None)
        if not original:
            return None
        # Presérva o estado de ativo
        was_active = self._profiles.get(profile_id, original).is_active
        restored = original.model_copy(update={"is_active": was_active})
        self._profiles[profile_id] = restored
        self._save()
        return restored

    def delete_profile(self, profile_id: str) -> bool:
        profile = self._profiles.get(profile_id)
        if not profile or profile.is_builtin:
            return False
        del self._profiles[profile_id]
        self._save()
        return True

    def activate_profile(self, profile_id: str) -> Optional[FanProfile]:
        if profile_id not in self._profiles:
            return None
        for p in self._profiles.values():
            p.is_active = False
        self._profiles[profile_id].is_active = True
        self._save()
        return self._profiles[profile_id]

    def get_active_profile(self) -> Optional[FanProfile]:
        return next((p for p in self._profiles.values() if p.is_active), None)

    # ------------------------------------------------------------------
    # Aplicação em tempo real
    # ------------------------------------------------------------------

    def apply_profile(
        self,
        profile: FanProfile,
        current_temp: float,
        fan_controller: FanController,
    ) -> None:
        """Calcula a velocidade alvo e a aplica a todas as ventoinhas controláveis."""
        target_percent = _interpolate(profile.curve, current_temp)
        for fan in fan_controller.list_fans():
            if fan.controllable:
                fan_controller.set_speed(fan.id, target_percent)
