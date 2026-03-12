"""Modelos Pydantic para sensores e controle de ventoinhas."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

# Modos de velocidade disponíveis → percentual equivalente (usado no controle de 3 níveis)
SPEED_MODES: dict[str, int] = {
    "quiet": 30,       # Silencioso  – baixo ruído, temperatura tolerável
    "balanced": 60,    # Balanceado  – uso geral, bom compromisso ruído/temperatura
    "turbo": 100,      # Turbo       – máxima performance, temperatura sob controle
}


class FanReading(BaseModel):
    """Leitura atual de uma única ventoinha."""

    id: str = Field(..., description="Identificador da ventoinha (ex: 'fan1')")
    label: str = Field(..., description="Label legível ao humano")
    rpm: int = Field(..., description="RPM atual")
    min_rpm: Optional[int] = None
    max_rpm: Optional[int] = Field(None, description="RPM máximo observado/registrado")
    percent: Optional[float] = Field(None, description="Velocidade como percentual do máximo")
    controllable: bool = Field(False, description="Se a velocidade pode ser definida")
    speed_mode: Optional[str] = Field(
        None,
        description="Modo de velocidade ativo: 'auto' | 'quiet' | 'balanced' | 'turbo'",
    )


class FanSpeedRequest(BaseModel):
    """Requisição para definir a velocidade de uma ventoinha específica (percentual)."""

    fan_id: str
    percent: float = Field(..., ge=0, le=100, description="Velocidade alvo de 0–100%")


class FanModeRequest(BaseModel):
    """Requisição para definir o modo de 3 níveis de uma ventoinha.

    Modos aceitos: ``quiet`` (30 %), ``balanced`` (60 %), ``turbo`` (100 %),
    ``auto`` (restaura controle automático da BIOS).
    """

    mode: str = Field(..., description="Modo de velocidade: quiet | balanced | turbo | auto")
