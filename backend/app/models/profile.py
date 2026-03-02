"""Modelos Pydantic para perfis de controle de ventoinhas."""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class CurvePoint(BaseModel):
    """Um ponto na curva temperatura→velocidade.

    Exemplo: a 60 °C o fan deve rodar a 50 %.
    """

    temperature: float = Field(..., ge=0, le=150, description="Temperatura de gatilho em °C")
    fan_percent: float = Field(..., ge=0, le=100, description="Velocidade da ventoinha em %")


class FanProfile(BaseModel):
    """Perfil de controle de ventoinha nomeado com uma curva de temperatura."""

    id: str
    name: str
    description: Optional[str] = None
    sensor_source: str = Field(
        "cpu_package",
        description="Sensor de temperatura a seguir (cpu_package | gpu | nvme)",
    )
    curve: List[CurvePoint] = Field(
        default_factory=list,
        description="Lista ordenada de pontos de controle (temperatura, percentual)",
    )
    is_active: bool = False
    is_builtin: bool = False  # Perfis padrões não podem ser excluídos


class FanProfileCreate(BaseModel):
    """Payload para criação de um novo perfil."""

    name: str
    description: Optional[str] = None
    sensor_source: str = "cpu_package"
    curve: List[CurvePoint] = Field(default_factory=list)


class FanProfileUpdate(BaseModel):
    """Payload para atualização de um perfil existente."""

    name: Optional[str] = None
    description: Optional[str] = None
    sensor_source: Optional[str] = None
    curve: Optional[List[CurvePoint]] = None
