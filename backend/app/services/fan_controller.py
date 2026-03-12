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
            try:
                label = label_file.read_text().strip() if label_file.exists() else f"{chip_name}/fan{i}"
            except OSError:
                label = f"{chip_name}/fan{i}"

            # Lê RPM mínimo e máximo do sysfs quando disponíveis
            min_rpm: Optional[int] = None
            max_rpm: Optional[int] = None
            try:
                min_file = hwmon_dir / f"fan{i}_min"
                if min_file.exists():
                    min_rpm = int(min_file.read_text().strip())
            except (ValueError, OSError):
                pass
            try:
                max_file = hwmon_dir / f"fan{i}_max"
                if max_file.exists():
                    max_rpm = int(max_file.read_text().strip())
            except (ValueError, OSError):
                pass

            # Calcula percentual quando max_rpm conhecido
            percent: Optional[float] = None
            if max_rpm and max_rpm > 0:
                percent = round(min(rpm / max_rpm * 100, 100.0), 1)

            pwm_file = hwmon_dir / f"pwm{i}"
            controllable = pwm_file.exists() and os.access(pwm_file, os.W_OK)

            # Se tiver arquivo PWM, tenta estimar percent por ele
            if percent is None and pwm_file.exists():
                try:
                    pwm_val = int(pwm_file.read_text().strip())
                    percent = round(pwm_val / 255 * 100, 1)
                except (ValueError, OSError):
                    pass

            fans.append(
                FanReading(
                    id=f"{hwmon_dir.name}_fan{i}",
                    label=label,
                    rpm=rpm,
                    min_rpm=min_rpm,
                    max_rpm=max_rpm,
                    percent=percent,
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
    """Lê velocidades de ventoinha via LibreHardwareMonitorLib.dll (PowerShell reader).

    Fallback para WMI do LibreHardwareMonitor se o reader não estiver disponível.
    """
    # Tenta via LHM DLL reader (não requer WMI)
    try:
        from app.services.hardware_monitor import _discover_windows_fans_lhm
        fans = _discover_windows_fans_lhm()
        if fans:
            return fans
    except Exception as exc:  # noqa: BLE001
        logger.debug("LHM DLL reader indisponível: %s", exc)

    # Fallback: WMI (LibreHardwareMonitor < 0.9.x)
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
                    controllable=False,
                )
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Erro ao ler ventoinhas via WMI: %s", exc)
    return fans


# ---------------------------------------------------------------------------
# Serviço FanController
# ---------------------------------------------------------------------------

# RPM padrão assumido como máximo enquanto o histórico ainda está curto.
# CPU fans em notebooks geralmente variam até ~5 000 RPM; GPU fans até ~6 500.
_DEFAULT_MAX_RPM = 5000


class FanController:
    """Gerencia a descoberta e o controle de velocidade de ventoinhas em múltiplas plataformas.

    Mantém estado em memória para:
    - ``_rpm_max``    – RPM máximo observado por ventoinha (atualizado a cada leitura).
    - ``_speed_modes``– Modo de velocidade ativo por ventoinha (quiet/balanced/turbo/auto).
    """

    def __init__(self) -> None:
        # Dicionário id → RPM máximo observado desde a inicialização
        self._rpm_max: dict[str, int] = {}
        # Dicionário id → modo atual ("quiet" | "balanced" | "turbo" | "auto")
        self._speed_modes: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Descoberta e leitura
    # ------------------------------------------------------------------

    def list_fans(self) -> list[FanReading]:
        """Retorna todas as ventoinhas detectadas com RPM atual, máximo e modo ativo."""
        if _OS == "Linux":
            fans = _discover_linux_fans()
        elif _OS == "Windows":
            fans = _discover_windows_fans()
        else:
            fans = []

        for fan in fans:
            # Atualiza o RPM máximo histórico
            if fan.rpm > 0:
                prev = self._rpm_max.get(fan.id, 0)
                self._rpm_max[fan.id] = max(prev, fan.rpm)

            # Preenche max_rpm com o máximo observado ou valor registrado pelo driver
            if fan.max_rpm is None or fan.max_rpm < fan.rpm:
                tracked = self._rpm_max.get(fan.id)
                if tracked:
                    fan.max_rpm = tracked

            # Injeta o modo de velocidade em memória (padrão = "auto")
            fan.speed_mode = self._speed_modes.get(fan.id, "auto")

            # Recalcula percent com base no max_rpm disponível (mais preciso)
            if fan.max_rpm and fan.max_rpm > 0 and fan.percent is None:
                fan.percent = round(min(fan.rpm / fan.max_rpm * 100, 100.0), 1)

        return fans

    # ------------------------------------------------------------------
    # Controle de velocidade – percentual livre
    # ------------------------------------------------------------------

    def set_speed(self, fan_id: str, percent: float) -> bool:
        """Define a ventoinha para um percentual específico de velocidade (0–100).

        Retorna True em caso de sucesso.  No Windows, fans detectadas via LHM
        não são controláveis diretamente sem drivers específicos do fabricante.
        """
        if _OS == "Linux":
            return _set_linux_fan_speed(fan_id, percent)
        logger.warning(
            "Controle de velocidade de ventoinhas não implementado para o SO: %s – "
            "modo salvo apenas em memória.",
            _OS,
        )
        return False

    # ------------------------------------------------------------------
    # Controle por modo (3 níveis estilo Nitro Sense)
    # ------------------------------------------------------------------

    def set_mode(self, fan_id: str, mode: str) -> bool:
        """Define o modo de velocidade para a ventoinha indicada.

        Modos aceitos: ``quiet`` (30 %), ``balanced`` (60 %), ``turbo`` (100 %),
        ``auto`` (restaura controle BIOS e remove modo salvo).

        No Linux, translada o modo para um valor PWM imediatamente.
        No Windows, salva o modo em memória (controle efetivo depende de drivers
        do fabricante como Nitro Sense / OMEN Command Center etc.).
        """
        from app.models.fan import SPEED_MODES  # evita importação circular no topo

        if mode == "auto":
            self._speed_modes.pop(fan_id, None)
            return self.restore_auto(fan_id)

        if mode not in SPEED_MODES:
            logger.warning("Modo de ventoinha desconhecido: %s", mode)
            return False

        self._speed_modes[fan_id] = mode
        percent = SPEED_MODES[mode]

        if _OS == "Linux":
            return self.set_speed(fan_id, percent)

        # Windows: modo registrado; controle físico requer drivers fabricante
        logger.info(
            "Modo '%s' (%d%%) salvo para ventoinha %s (Windows – sem controle físico direto).",
            mode,
            percent,
            fan_id,
        )
        return True

    # ------------------------------------------------------------------
    # Restauração automática
    # ------------------------------------------------------------------

    def restore_auto(self, fan_id: str) -> bool:
        """Restaura o controle automático da ventoinha para um ID específico."""
        self._speed_modes.pop(fan_id, None)
        if _OS == "Linux":
            return _restore_linux_auto(fan_id)
        return True  # no Windows, apenas remove o modo salvo

    def restore_all_auto(self) -> None:
        """Restaura o controle automático para todas as ventoinhas controláveis."""
        for fan in self.list_fans():
            self.restore_auto(fan.id)
