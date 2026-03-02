"""Modelos Pydantic para dados de sensores de hardware."""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TemperatureSensor(BaseModel):
    """Leitura individual de um sensor de temperatura."""

    label: str = Field(..., description="Rótulo / nome do sensor")
    current: float = Field(..., description="Temperatura atual em °C")
    high: Optional[float] = Field(None, description="Limiar de alerta em °C")
    critical: Optional[float] = Field(None, description="Limiar crítico em °C")


class TemperatureComponent(BaseModel):
    """Grupo de sensores de um componente de hardware."""

    component: str = Field(..., description="Nome do componente (ex: 'CPU', 'GPU')")
    sensors: List[TemperatureSensor] = Field(default_factory=list)


class CpuStats(BaseModel):
    """Estatísticas de utilização da CPU."""

    usage_percent: float = Field(..., description="Uso geral da CPU em %")
    per_core: List[float] = Field(default_factory=list, description="Uso por núcleo em %")
    frequency_mhz: Optional[float] = None
    temperature: Optional[float] = Field(None, description="Temperatura do pacote em °C")


class MemoryStats(BaseModel):
    """Estatísticas de memória do sistema."""

    total_gb: float
    used_gb: float
    available_gb: float
    percent: float


class DiskStats(BaseModel):
    """Uso de disco para uma única partição."""

    device: str
    mountpoint: str
    total_gb: float
    used_gb: float
    percent: float


class GpuStats(BaseModel):
    """Estatísticas de GPU (quando disponível)."""

    name: str
    load_percent: float
    memory_used_mb: float
    memory_total_mb: float
    temperature: Optional[float] = None


class HardwareSnapshot(BaseModel):
    """Snapshot completo de hardware transmitido via WebSocket."""

    timestamp: float = Field(..., description="Unix timestamp da leitura")
    cpu: CpuStats
    memory: MemoryStats
    disks: List[DiskStats] = Field(default_factory=list)
    gpus: List[GpuStats] = Field(default_factory=list)
    temperatures: List[TemperatureComponent] = Field(default_factory=list)
