"""Modelos Pydantic para sensores e controle de ventoinhas."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class FanReading(BaseModel):
    """Leitura atual de uma única ventoinha."""

    id: str = Field(..., description="Identificador da ventoinha (ex: 'fan1')")
    label: str = Field(..., description="Label legível ao humano")
    rpm: int = Field(..., description="RPM atual")
    min_rpm: Optional[int] = None
    max_rpm: Optional[int] = None
    percent: Optional[float] = Field(None, description="Velocidade como percentual do máximo")
    controllable: bool = Field(False, description="Se a velocidade pode ser definida")


class FanSpeedRequest(BaseModel):
    """Requisição para definir a velocidade de uma ventoinha específica."""

    fan_id: str
    percent: float = Field(..., ge=0, le=100, description="Velocidade alvo de 0–100%")
