"""Serviço de monitoramento de hardware – multiplataforma (Linux e Windows)."""

from __future__ import annotations

import asyncio
import logging
import platform
import time
from typing import TYPE_CHECKING, Optional

import psutil

from app.models.hardware import (
    CpuStats,
    DiskStats,
    GpuStats,
    HardwareSnapshot,
    MemoryStats,
    TemperatureComponent,
    TemperatureSensor,
)

if TYPE_CHECKING:
    from app.websocket.manager import WebSocketManager

logger = logging.getLogger(__name__)
_OS = platform.system()  # "Linux" | "Windows" | "Darwin"


def _read_temps_linux() -> list[TemperatureComponent]:
    """Lê temperaturas via psutil (requer lm-sensors no Linux)."""
    components: list[TemperatureComponent] = []
    try:
        raw = psutil.sensors_temperatures()
        if not raw:
            return components
        for key, entries in raw.items():
            sensors = [
                TemperatureSensor(
                    label=e.label or f"{key}_{i}",
                    current=e.current,
                    high=e.high,
                    critical=e.critical,
                )
                for i, e in enumerate(entries)
            ]
            components.append(TemperatureComponent(component=key, sensors=sensors))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Erro ao ler temperaturas: %s", exc)
    return components


def _read_temps_windows() -> list[TemperatureComponent]:
    """Lê temperaturas via WMI / LibreHardwareMonitor no Windows."""
    components: list[TemperatureComponent] = []
    try:
        import wmi  # type: ignore[import]

        w = wmi.WMI(namespace=r"root\LibreHardwareMonitor")
        sensors = w.Sensor()
        grouped: dict[str, list[TemperatureSensor]] = {}
        for s in sensors:
            if s.SensorType != "Temperature":
                continue
            parent = getattr(s, "Parent", "Unknown")
            grouped.setdefault(parent, []).append(
                TemperatureSensor(label=s.Name, current=float(s.Value))
            )
        for parent, sensor_list in grouped.items():
            components.append(TemperatureComponent(component=parent, sensors=sensor_list))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Erro ao ler temperaturas via WMI: %s", exc)
    return components


def _read_gpus() -> list[GpuStats]:
    """Lê estatísticas de GPU via GPUtil (NVIDIA) – melhor esforço."""
    gpus: list[GpuStats] = []
    try:
        import GPUtil  # type: ignore[import]

        for g in GPUtil.getGPUs():
            gpus.append(
                GpuStats(
                    name=g.name,
                    load_percent=g.load * 100,
                    memory_used_mb=g.memoryUsed,
                    memory_total_mb=g.memoryTotal,
                    temperature=g.temperature,
                )
            )
    except Exception:  # noqa: BLE001
        pass
    return gpus


class HardwareMonitor:
    """Coleta e armazena em cache dados de telemetria de hardware."""

    def __init__(self) -> None:
        self._latest_snapshot: Optional[HardwareSnapshot] = None
        self._running = False

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def get_snapshot(self) -> Optional[HardwareSnapshot]:
        """Retorna o snapshot coletado mais recentemente."""
        return self._latest_snapshot

    def collect(self) -> HardwareSnapshot:
        """Coleta um novo snapshot de hardware de forma síncrona."""
        snapshot = HardwareSnapshot(
            timestamp=time.time(),
            cpu=self._cpu_stats(),
            memory=self._memory_stats(),
            disks=self._disk_stats(),
            gpus=_read_gpus(),
            temperatures=self._temperatures(),
        )
        self._latest_snapshot = snapshot
        return snapshot

    async def start_polling(
        self,
        interval: float,
        ws_manager: "WebSocketManager",
    ) -> None:
        """Tarefa em background – coleta telemetria e envia via WebSocket."""
        self._running = True
        logger.info("Coleta de hardware iniciada (intervalo=%.1fs)", interval)
        while self._running:
            try:
                snapshot = self.collect()
                await ws_manager.broadcast(snapshot.model_dump())
            except Exception as exc:  # noqa: BLE001
                logger.warning("Erro na coleta de hardware: %s", exc)
            await asyncio.sleep(interval)

    # ------------------------------------------------------------------
    # Métodos privados auxiliares
    # ------------------------------------------------------------------

    def _cpu_stats(self) -> CpuStats:
        per_core = psutil.cpu_percent(percpu=True)
        overall = sum(per_core) / len(per_core) if per_core else 0.0
        freq = psutil.cpu_freq()
        temp = self._cpu_package_temp()
        return CpuStats(
            usage_percent=round(overall, 1),
            per_core=[round(c, 1) for c in per_core],
            frequency_mhz=round(freq.current, 1) if freq else None,
            temperature=temp,
        )

    def _cpu_package_temp(self) -> Optional[float]:
        """Extrai a temperatura do pacote CPU a partir dos dados de sensor."""
        temps = _read_temps_linux() if _OS == "Linux" else _read_temps_windows()
        for component in temps:
            key = component.component.lower()
            if any(k in key for k in ("coretemp", "k10temp", "cpu", "acpitz")):
                for sensor in component.sensors:
                    if "package" in sensor.label.lower() or sensor.label == "":
                        return sensor.current
                if component.sensors:
                    return component.sensors[0].current
        return None

    def _memory_stats(self) -> MemoryStats:
        mem = psutil.virtual_memory()
        gb = 1024 ** 3
        return MemoryStats(
            total_gb=round(mem.total / gb, 2),
            used_gb=round(mem.used / gb, 2),
            available_gb=round(mem.available / gb, 2),
            percent=mem.percent,
        )

    def _disk_stats(self) -> list[DiskStats]:
        disks: list[DiskStats] = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                gb = 1024 ** 3
                disks.append(
                    DiskStats(
                        device=part.device,
                        mountpoint=part.mountpoint,
                        total_gb=round(usage.total / gb, 2),
                        used_gb=round(usage.used / gb, 2),
                        percent=usage.percent,
                    )
                )
            except PermissionError:
                continue
        return disks

    def _temperatures(self) -> list[TemperatureComponent]:
        if _OS == "Linux":
            return _read_temps_linux()
        elif _OS == "Windows":
            return _read_temps_windows()
        return []
