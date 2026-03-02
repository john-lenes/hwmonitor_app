"""Serviço de controle de ventoinhas – multiplataforma (Linux / Windows)."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

from app.models.fan import FanReading

logger = logging.getLogger(__name__)
_OS = platform.system()


# ---------------------------------------------------------------------------
# Helpers Linux – interface sysfs hwmon
# ---------------------------------------------------------------------------

_HWMON_BASE = Path("/sys/class/hwmon")


def _discover_linux_fans() -> list[FanReading]:
    """Percorre sysfs do hwmon para encontrar sensores de ventoinha."""
    fans: list[FanReading] = []
    if not _HWMON_BASE.exists():
        return fans

    for hwmon_dir in sorted(_HWMON_BASE.iterdir()):
        name_file = hwmon_dir / "name"
        chip_name = name_file.read_text().strip() if name_file.exists() else hwmon_dir.name

        for i in range(1, 10):
            input_file = hwmon_dir / f"fan{i}_input"
            if not input_file.exists():
                continue

            try:
                rpm = int(input_file.read_text().strip())
            except (ValueError, OSError):
                continue

            label_file = hwmon_dir / f"fan{i}_label"
            label = (
                label_file.read_text().strip()
                if label_file.exists()
                else f"{chip_name}/fan{i}"
            )

            min_rpm: Optional[int] = None
            pwm_file = hwmon_dir / f"pwm{i}"
            controllable = pwm_file.exists() and os.access(pwm_file, os.W_OK)

            fans.append(
                FanReading(
                    id=f"{hwmon_dir.name}_fan{i}",
                    label=label,
                    rpm=rpm,
                    min_rpm=min_rpm,
                    controllable=controllable,
                )
            )
    return fans


def _set_linux_fan_speed(fan_id: str, percent: float) -> bool:
    """Define o valor PWM (0-255) da ventoinha via sysfs do hwmon.

    Requer permissão de escrita no arquivo pwm (normalmente necessita de root
    ou permissões do serviço fancontrol).
    """
    # Formato do fan_id: hwmon<N>_fan<M>
    try:
        parts = fan_id.split("_fan")
        hwmon_name, fan_index = parts[0], int(parts[1])
        pwm_path = _HWMON_BASE / hwmon_name / f"pwm{fan_index}"
        enable_path = _HWMON_BASE / hwmon_name / f"pwm{fan_index}_enable"

        # Muda para modo de controle manual (1 = manual)
        if enable_path.exists():
            enable_path.write_text("1")

        pwm_value = int(percent / 100 * 255)
        pwm_path.write_text(str(pwm_value))
        logger.info("Ventoinha %s definida para %s%% (PWM %s)", fan_id, percent, pwm_value)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Falha ao definir velocidade da ventoinha %s: %s", fan_id, exc)
        return False


def _restore_linux_auto(fan_id: str) -> bool:
    """Restaura o controle automático / BIOS para uma ventoinha hwmon no Linux."""
    try:
        parts = fan_id.split("_fan")
        hwmon_name, fan_index = parts[0], int(parts[1])
        enable_path = _HWMON_BASE / hwmon_name / f"pwm{fan_index}_enable"
        if enable_path.exists():
            enable_path.write_text("2")  # 2 = automático
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Falha ao restaurar controle automático da ventoinha %s: %s", fan_id, exc)
        return False


# ---------------------------------------------------------------------------
# Helpers Windows – WMI / LibreHardwareMonitor
# ---------------------------------------------------------------------------

def _discover_windows_fans() -> list[FanReading]:
    """Lê velocidades de ventoinha via WMI do LibreHardwareMonitor."""
    fans: list[FanReading] = []
    try:
        import wmi  # type: ignore[import]

        w = wmi.WMI(namespace=r"root\LibreHardwareMonitor")
        for s in w.Sensor():
            if s.SensorType != "Fan":
                continue
            fans.append(
                FanReading(
                    id=s.Identifier.replace("/", "_").lstrip("_"),
                    label=s.Name,
                    rpm=int(s.Value),
                    controllable=False,  # LHM somente leitura via WMI
                )
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Erro ao ler ventoinhas via WMI: %s", exc)
    return fans


# ---------------------------------------------------------------------------
# Serviço FanController
# ---------------------------------------------------------------------------


class FanController:
    """Gerencia a descoberta e o controle de velocidade de ventoinhas em múltiplas plataformas."""

    def list_fans(self) -> list[FanReading]:
        """Retorna todas as ventoinhas detectadas."""
        if _OS == "Linux":
            return _discover_linux_fans()
        elif _OS == "Windows":
            return _discover_windows_fans()
        return []

    def set_speed(self, fan_id: str, percent: float) -> bool:
        """Define a ventoinha para um percentual específico de velocidade.

        Retorna True em caso de sucesso.
        """
        if _OS == "Linux":
            return _set_linux_fan_speed(fan_id, percent)
        logger.warning("Controle de velocidade de ventoinhas não implementado para o SO: %s", _OS)
        return False

    def restore_auto(self, fan_id: str) -> bool:
        """Restaura o controle automático da ventoinha para um ID específico."""
        if _OS == "Linux":
            return _restore_linux_auto(fan_id)
        return False

    def restore_all_auto(self) -> None:
        """Restaura o controle automático para todas as ventoinhas contrólaveis."""
        for fan in self.list_fans():
            if fan.controllable:
                self.restore_auto(fan.id)
