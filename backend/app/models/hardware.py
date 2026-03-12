"""Modelos Pydantic para dados de sensores de hardware."""

from __future__ import annotations

from typing import List, Optional
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
    temperature_note: Optional[str] = Field(
        None,
        description=(
            "Motivo pelo qual a temperatura não está disponível. "
            "'run_as_admin' = o backend precisa de privilégios de administrador "
            "para acessar os sensores de temperatura via LibreHardwareMonitor."
        ),
    )


class MemorySlot(BaseModel):
    """Informações de um slot físico de memória RAM (via dmidecode)."""

    device_locator: str = Field("", description="Localização do slot (ex: DIMM A1)")
    size_gb: float = Field(0.0, description="Capacidade do módulo em GB")
    speed_mhz: Optional[int] = Field(None, description="Velocidade em MHz")
    manufacturer: Optional[str] = Field(None, description="Fabricante do módulo")
    part_number: Optional[str] = Field(None, description="Número de série / part number")
    form_factor: Optional[str] = Field(None, description="Formato (ex: SODIMM, DIMM)")
    memory_type: Optional[str] = Field(None, description="Tipo (DDR4, DDR5, LPDDR5...)") 


class MemoryStats(BaseModel):
    """Estatísticas de memória do sistema."""

    total_gb: float
    used_gb: float
    available_gb: float
    percent: float
    hardware_total_gb: Optional[float] = Field(
        None, description="Total físico real via dmidecode (soma dos slots)"
    )
    slots: List[MemorySlot] = Field(
        default_factory=list, description="Detalhes de cada slot físico"
    )


class DiskStats(BaseModel):
    """Uso de disco para uma única partição/volume lógico."""

    device: str
    mountpoint: str
    total_gb: float
    used_gb: float
    percent: float
    # Informações do disco físico subjacente (melhor esforço)
    model: Optional[str] = Field(None, description="Modelo do disco físico (ex: Samsung SSD 860 EVO)")
    media_type: Optional[str] = Field(None, description="Tipo de mídia: NVMe | SSD | HDD | Unknown")
    physical_size_gb: Optional[float] = Field(None, description="Capacidade real do disco físico em GB")


class GpuStats(BaseModel):
    """Estatísticas de GPU (quando disponível)."""

    name: str
    load_percent: float
    memory_used_mb: float
    memory_total_mb: float
    temperature: Optional[float] = None
    vendor: Optional[str] = Field(None, description="NVIDIA | AMD | Intel | Unknown")
    driver_version: Optional[str] = Field(None, description="Versão do driver")
    vram_gb: Optional[float] = Field(None, description="VRAM total em GB")


class HardwareSnapshot(BaseModel):
    """Snapshot completo de hardware transmitido via WebSocket."""

    timestamp: float = Field(..., description="Unix timestamp da leitura")
    cpu: CpuStats
    memory: MemoryStats
    disks: List[DiskStats] = Field(default_factory=list)
    gpus: List[GpuStats] = Field(default_factory=list)
    temperatures: List[TemperatureComponent] = Field(default_factory=list)
