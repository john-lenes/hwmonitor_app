"""Serviço de monitoramento de hardware – multiplataforma (Linux e Windows).

Correções:
- RAM: dmidecode detecta slots físicos reais (corrige leitura parcial dentro de
  containers Docker onde psutil reporta apenas a RAM do VM, ex: 7.7 GB em vez de 16 GB).
- GPU: detecção multi-vendor (NVIDIA via GPUtil, AMD via sysfs DRM, Intel via sysfs, lspci).
- Windows temps/fans: LibreHardwareMonitorLib.dll via PowerShell background reader
  (substitui WMI removido no LHM 0.9.x).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import re
import subprocess
import tempfile
import time
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import psutil

from app.models.hardware import (
    CpuStats,
    DiskStats,
    GpuStats,
    HardwareSnapshot,
    MemorySlot,
    MemoryStats,
    TemperatureComponent,
    TemperatureSensor,
)

if TYPE_CHECKING:
    from app.websocket.manager import WebSocketManager

logger = logging.getLogger(__name__)
_OS = platform.system()  # "Linux" | "Windows" | "Darwin"


# ──────────────────────────────────────────────────────────────────────────────
# Windows – LibreHardwareMonitor DLL reader (substitui WMI no LHM 0.9.x)
# ──────────────────────────────────────────────────────────────────────────────

_LHM_DLL_SEARCH_PATHS: list[Path] = [
    # WinGet installation
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
    # Manual / Chocolatey installs
    Path("C:/Program Files/LibreHardwareMonitor"),
    Path("C:/Program Files (x86)/LibreHardwareMonitor"),
    Path("C:/Tools/LibreHardwareMonitor"),
    # Uso portátil – Desktop / Downloads / raiz do perfil
    Path(os.environ.get("USERPROFILE", "")) / "Desktop",
    Path(os.environ.get("USERPROFILE", "")) / "Downloads",
    Path(os.environ.get("USERPROFILE", "")) / "LibreHardwareMonitor",
    # Raízes comuns de instalação portátil
    Path("C:/LibreHardwareMonitor"),
    Path("C:/lhm"),
    Path("C:/Tools"),
]


def _find_lhm_dll() -> Optional[Path]:
    """Localiza LibreHardwareMonitorLib.dll no sistema."""
    for base in _LHM_DLL_SEARCH_PATHS:
        if not base.exists():
            continue
        # Busca recursiva limitada a 3 níveis
        for dll in base.rglob("LibreHardwareMonitorLib.dll"):
            return dll
    return None


_LHM_PS_SCRIPT = Path(__file__).parent / "lhm_reader.ps1"
_lhm_proc: Optional[subprocess.Popen] = None  # type: ignore[type-arg]
_lhm_json_file: Optional[Path] = None


def _start_lhm_reader() -> Optional[Path]:
    """Inicia o leitor PowerShell LHM em background; retorna o caminho do JSON."""
    global _lhm_proc, _lhm_json_file

    # Já iniciado e ainda rodando
    if _lhm_proc is not None and _lhm_proc.poll() is None:
        return _lhm_json_file

    dll = _find_lhm_dll()
    if dll is None:
        logger.debug("LHM DLL não encontrada; leitura de sensores via PowerShell desativada.")
        return None

    if not _LHM_PS_SCRIPT.exists():
        logger.warning("lhm_reader.ps1 não encontrado em %s", _LHM_PS_SCRIPT)
        return None

    tmp = Path(tempfile.gettempdir()) / "hwmonitor_lhm_sensors.json"
    _lhm_json_file = tmp

    try:
        _lhm_proc = subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-File", str(_LHM_PS_SCRIPT),
                "-DllPath", str(dll),
                "-OutputFile", str(tmp),
                "-IntervalMs", "2000",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if _OS == "Windows" else 0,
        )
        logger.info("LHM PowerShell reader iniciado (PID %d) usando %s", _lhm_proc.pid, dll)
        return tmp
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao iniciar LHM reader: %s", exc)
        return None


def _stop_lhm_reader() -> None:
    """Encerra o processo reader do LHM se estiver rodando."""
    global _lhm_proc
    if _lhm_proc is not None:
        try:
            _lhm_proc.terminate()
            _lhm_proc.wait(timeout=3)
        except Exception:  # noqa: BLE001
            pass
        _lhm_proc = None


# Caminho bem-conhecido: usado como fallback quando _lhm_json_file ainda não foi definido
# (ex: primeiro ciclo antes do HardwareMonitor.__init__ ou chamadas isoladas em testes).
_LHM_KNOWN_JSON_PATH = Path(tempfile.gettempdir()) / "hwmonitor_lhm_sensors.json"


def _read_lhm_json() -> Optional[dict]:  # type: ignore[type-arg]
    """Lê o JSON mais recente exportado pelo leitor PowerShell LHM.

    Usa _lhm_json_file quando definido; cai para o caminho bem-conhecido
    (_LHM_KNOWN_JSON_PATH) para tolerar leituras antes de HardwareMonitor
    ser instanciado ou quando um reader já estava em execução.
    """
    path = _lhm_json_file if _lhm_json_file is not None else _LHM_KNOWN_JSON_PATH
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if "error" in data:
            logger.debug("LHM reader reportou erro: %s", data["error"])
            return None
        return data
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao ler JSON do LHM: %s", exc)
        return None


def _read_temps_windows_lhm() -> list[TemperatureComponent]:
    """Lê temperaturas via LibreHardwareMonitorLib.dll (PowerShell reader)."""
    data = _read_lhm_json()
    if data is None:
        return []
    sensors: list[dict] = data.get("sensors", [])
    grouped: dict[str, list[TemperatureSensor]] = {}
    for s in sensors:
        if s.get("type") != "Temperature":
            continue
        key = s.get("hardware", "Unknown")
        grouped.setdefault(key, []).append(
            TemperatureSensor(
                label=s.get("name", ""),
                current=float(s["value"]),
            )
        )
    return [
        TemperatureComponent(component=k, sensors=v)
        for k, v in grouped.items()
    ]


def _discover_windows_fans_lhm() -> list:
    """Detecta ventoinhas via LibreHardwareMonitorLib.dll (PowerShell reader)."""
    from app.models.fan import FanReading  # evita importação circular no topo

    data = _read_lhm_json()
    if data is None:
        return []
    fans = []
    for s in data.get("sensors", []):
        if s.get("type") != "Fan":
            continue
        fan_id = re.sub(r"[^a-zA-Z0-9_]", "_", s.get("identifier", s["name"]))
        fans.append(
            FanReading(
                id=fan_id,
                label=f"{s.get('hardware','')} / {s.get('name','')}",
                rpm=int(s["value"]),
                controllable=False,
            )
        )
    return fans


def _read_gpus_from_lhm() -> list[GpuStats]:
    """Cria lista de GpuStats com métricas reais lidas via LibreHardwareMonitorLib.dll."""
    data = _read_lhm_json()
    if not data:
        return []

    by_hw: dict[str, dict] = {}
    for s in data.get("sensors", []):
        hw_type = s.get("hardwareType", "").lower()
        if "gpu" not in hw_type:
            continue
        hw = s.get("hardware", "")
        name = s.get("name", "").lower()
        stype = s.get("type", "")
        try:
            value = float(s.get("value", 0))
        except (ValueError, TypeError):
            value = 0.0

        g = by_hw.setdefault(hw, {})
        if stype == "Temperature" and name == "gpu core":
            g.setdefault("temperature", round(value, 1))
        elif stype == "Load" and name == "gpu core":
            g.setdefault("load_percent", round(value, 1))
        elif stype == "SmallData" and name == "gpu memory total":
            g.setdefault("memory_total_mb", round(value, 1))
        elif stype == "SmallData" and name == "gpu memory used":
            g.setdefault("memory_used_mb", round(value, 1))

    gpus: list[GpuStats] = []
    for hw_name, m in by_hw.items():
        vram_mb = m.get("memory_total_mb", 0.0)
        gpus.append(GpuStats(
            name=hw_name,
            load_percent=m.get("load_percent", 0.0),
            memory_used_mb=m.get("memory_used_mb", 0.0),
            memory_total_mb=vram_mb,
            temperature=m.get("temperature"),
            vendor=_detect_gpu_vendor(hw_name),
            vram_gb=round(vram_mb / 1024, 2) if vram_mb > 0 else None,
        ))
    return gpus


def _read_memory_slots_windows() -> tuple[float, list[MemorySlot]]:
    """Lê slots de memória física via PowerShell Get-CimInstance Win32_PhysicalMemory."""
    _FORM_FACTOR: dict[int, str] = {9: "DIMM", 12: "SODIMM", 13: "SODIMM", 15: "DIMM"}
    _MEM_TYPE: dict[int, str] = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 34: "DDR5"}
    slots: list[MemorySlot] = []
    hardware_total_gb = 0.0
    try:
        ps_cmd = (
            "Get-CimInstance Win32_PhysicalMemory | "
            "Select-Object DeviceLocator,Capacity,Speed,Manufacturer,PartNumber,MemoryType,FormFactor | "
            "ConvertTo-Json -Compress"
        )
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", ps_cmd],
            text=True, stderr=subprocess.DEVNULL, timeout=15,
        )
        items = json.loads(output.strip())
        if isinstance(items, dict):
            items = [items]
        for item in items:
            cap = int(item.get("Capacity") or 0)
            if cap <= 0:
                continue
            size_gb = round(cap / (1024 ** 3), 2)
            hardware_total_gb += size_gb
            speed = item.get("Speed")
            mfg = (item.get("Manufacturer") or "").strip() or None
            pn = (item.get("PartNumber") or "").strip() or None
            locator = (item.get("DeviceLocator") or "").strip()
            form_raw = int(item.get("FormFactor") or 0)
            type_raw = int(item.get("MemoryType") or 0)
            slots.append(MemorySlot(
                device_locator=locator,
                size_gb=size_gb,
                speed_mhz=int(speed) if speed else None,
                manufacturer=mfg,
                part_number=pn,
                form_factor=_FORM_FACTOR.get(form_raw),
                memory_type=_MEM_TYPE.get(type_raw),
            ))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Erro ao ler slots de RAM no Windows: %s", exc)
    return round(hardware_total_gb, 2), slots


# ──────────────────────────────────────────────────────────────────────────────
# Mapeamento partição → disco físico
# ──────────────────────────────────────────────────────────────────────────────


def _read_physical_disk_map_windows() -> dict[str, tuple]:
    """
    Retorna mapeamento mountpoint (ex: 'C:\\') → (model, media_type, size_gb)
    via PowerShell CIM.  Chamado uma vez e cacheado em HardwareMonitor.
    """
    ps_script = (
        "$result=@();"
        "foreach($ld in (Get-CimInstance Win32_LogicalDisk|"
        "Where-Object{$_.DeviceID-match'^[A-Z]:$'})){"
        "try{"
        "$pt=Get-CimAssociatedInstance $ld -ResultClassName Win32_DiskPartition"
        " -ErrorAction SilentlyContinue|Select-Object -First 1;"
        "if($pt){"
        "$dk=Get-CimAssociatedInstance $pt -ResultClassName Win32_DiskDrive"
        " -ErrorAction SilentlyContinue|Select-Object -First 1;"
        "if($dk){"
        "$sGB=if($dk.Size){[math]::Round([long]$dk.Size/1073741824,2)}else{0};"
        "$mt=if($dk.Model-match'NVMe|NVME'  -or $dk.InterfaceType-eq'NVMe'){'NVMe'}"
        "elseif($dk.Model-match'SSD|Solid' -or $dk.MediaType-match'SSD'){'SSD'}"
        "elseif($dk.MediaType-match'HDD|Rotating|Fixed' -or $dk.Model-match'WDC|Seagate|HGST|Hitachi'){'HDD'}else{'Unknown'};"
        "$result+=[PSCustomObject]@{Letter=\"$($ld.DeviceID)\\\\\";Model=$dk.Model;MediaType=$mt;SizeGB=$sGB}"
        "}}}catch{}}"
        "$result|ConvertTo-Json -Compress"
    )
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", ps_script],
            text=True, stderr=subprocess.DEVNULL, timeout=25,
        )
        text = output.strip()
        if not text or text == "null":
            return {}
        items = json.loads(text)
        if isinstance(items, dict):
            items = [items]
        result: dict[str, tuple] = {}
        for item in items:
            letter = (item.get("Letter") or "").strip()
            # Normaliza para exatamente uma barra invertida no final (C:\ )
            letter = letter.rstrip("\\") + "\\" if letter else ""
            model = (item.get("Model") or "").strip() or None
            media_type = (item.get("MediaType") or "Unknown").strip()
            size_gb: Optional[float] = float(item.get("SizeGB") or 0) or None
            if letter:
                result[letter] = (model, media_type, size_gb)
        logger.info("Mapa discos físicos Windows: %d volumes mapeados", len(result))
        return result
    except Exception as exc:  # noqa: BLE001
        logger.debug("Erro ao ler mapa de discos físicos no Windows: %s", exc)
        return {}


def _read_physical_disk_map_linux() -> dict[str, tuple]:
    """Retorna mapeamento mountpoint → (model, media_type, size_gb) via sysfs."""
    result: dict[str, tuple] = {}
    try:
        for part in psutil.disk_partitions(all=False):
            device = part.device
            m = re.match(r"(/dev/(?:nvme\d+n\d+|[a-z]+))", device)
            if not m:
                continue
            disk_name = m.group(1).replace("/dev/", "")
            sys_path = Path(f"/sys/block/{disk_name}")
            if not sys_path.exists():
                continue
            model_raw = _read_sysfs_str(sys_path / "device" / "model")
            model = model_raw.strip() if model_raw else None
            rotational = _read_sysfs_int(sys_path / "queue" / "rotational")
            size_sectors = _read_sysfs_int(sys_path / "size")
            if "nvme" in disk_name:
                media_type = "NVMe"
            elif rotational == 0:
                media_type = "SSD"
            elif rotational == 1:
                media_type = "HDD"
            else:
                media_type = "Unknown"
            size_gb: Optional[float] = (
                round(size_sectors * 512 / (1024 ** 3), 2) if size_sectors else None
            )
            result[part.mountpoint] = (model, media_type, size_gb)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Erro ao ler mapa de discos físicos no Linux: %s", exc)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Helpers genéricos
# ──────────────────────────────────────────────────────────────────────────────


def _read_sysfs_int(path: Path) -> Optional[int]:
    """Lê um inteiro de um arquivo sysfs; retorna None em caso de falha."""
    try:
        return int(path.read_text().strip())
    except Exception:  # noqa: BLE001
        return None


def _read_sysfs_str(path: Path) -> Optional[str]:
    """Lê uma string de um arquivo sysfs; retorna None em caso de falha."""
    try:
        val = path.read_text().strip()
        return val if val else None
    except Exception:  # noqa: BLE001
        return None


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


# Cache para leitura de temperatura via PowerShell (evita overhead de ~1 s do PS a cada poll)
_ps_temp_cache: tuple[float, Optional[float]] = (0.0, None)  # (timestamp, °C)
_PS_TEMP_TTL = 10.0  # segundos entre chamadas reais ao PS


def _read_cpu_temp_windows_ps() -> Optional[float]:
    """
    Fallback de temperatura do pacote CPU no Windows via PowerShell puro
    (não requer pacote Python 'wmi' nem DLL do LHM em disco).

    Prioridade:
      1. LHM WMI namespace (root\\LibreHardwareMonitor) – se LHM estiver rodando como admin.
      2. ACPI Thermal Zone (MSAcpi_ThermalZoneTemperature) – sempre disponível no Windows.

    O resultado é cacheado por _PS_TEMP_TTL segundos para não iniciar um processo
    PowerShell a cada ciclo de coleta (2 s).
    """
    global _ps_temp_cache
    now = time.time()
    if now - _ps_temp_cache[0] < _PS_TEMP_TTL:
        return _ps_temp_cache[1]

    result: Optional[float] = None

    # ── Tentativa 1: LHM WMI namespace ─────────────────────────────────────
    try:
        ps_cmd = (
            "try {"
            " $s = Get-WmiObject -Namespace 'root\\LibreHardwareMonitor'"
            " -Class Sensor -ErrorAction Stop"
            " | Where-Object { $_.SensorType -eq 'Temperature'"
            "   -and $_.Name -like '*Package*' }"
            " | Select-Object -First 1;"
            " if ($s) { [math]::Round([float]$s.Value, 1) } else { 'null' }"
            "} catch { 'null' }"
        )
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            text=True, stderr=subprocess.DEVNULL, timeout=6,
        ).strip()
        if out and out != "null":
            val = float(out)
            if 0.0 < val < 200.0:
                result = round(val, 1)
    except Exception:  # noqa: BLE001
        pass

    # ── Tentativa 2: ACPI Thermal Zone (décimos de Kelvin → Celsius) ────────
    if result is None:
        try:
            ps_cmd = (
                "$t = (Get-WmiObject -Namespace root\\WMI"
                " -Class MSAcpi_ThermalZoneTemperature"
                " -ErrorAction SilentlyContinue"
                " | Sort-Object CurrentTemperature -Descending"
                " | Select-Object -First 1 -ExpandProperty CurrentTemperature);"
                " if ($t) { [math]::Round(($t - 2732) / 10.0, 1) } else { 'null' }"
            )
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                text=True, stderr=subprocess.DEVNULL, timeout=6,
            ).strip()
            if out and out != "null":
                val = float(out)
                if 0.0 < val < 200.0:
                    result = round(val, 1)
        except Exception:  # noqa: BLE001
            pass

    _ps_temp_cache = (now, result)
    return result


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


# ─────────────────────────────────────────────────────────────────────────────
# Detecção de GPU – multi-método (NVIDIA → AMD → Intel → lspci)
# ─────────────────────────────────────────────────────────────────────────────


def _detect_gpu_vendor(vendor_str: str) -> str:
    v = vendor_str.upper()
    if "NVIDIA" in v:
        return "NVIDIA"
    if "AMD" in v or "ADVANCED MICRO" in v or "ATI" in v:
        return "AMD"
    if "INTEL" in v:
        return "Intel"
    return "Unknown"


def _read_gpus_nvidia() -> list[GpuStats]:
    """Lê estatísticas de GPU via GPUtil (apenas NVIDIA)."""
    gpus: list[GpuStats] = []
    try:
        import GPUtil  # type: ignore[import]
        for g in GPUtil.getGPUs():
            vram_gb = round(g.memoryTotal / 1024, 2) if g.memoryTotal else None
            gpus.append(GpuStats(
                name=g.name,
                load_percent=round(g.load * 100, 1),
                memory_used_mb=g.memoryUsed,
                memory_total_mb=g.memoryTotal,
                temperature=g.temperature,
                vendor="NVIDIA",
                driver_version=getattr(g, "driver", None),
                vram_gb=vram_gb,
            ))
    except Exception:  # noqa: BLE001
        pass
    return gpus


def _read_gpus_amd() -> list[GpuStats]:
    """Lê estatísticas de GPU AMD via sysfs DRM (/sys/class/drm)."""
    gpus: list[GpuStats] = []
    drm_base = Path("/sys/class/drm")
    if not drm_base.exists():
        return gpus
    for card_dir in sorted(drm_base.iterdir()):
        if not re.fullmatch(r"card\d+", card_dir.name):
            continue
        vendor_id = _read_sysfs_str(card_dir / "device" / "vendor") or ""
        if vendor_id != "0x1002":  # AMD vendor ID
            continue
        vram_total = _read_sysfs_int(card_dir / "device" / "mem_info_vram_total")
        vram_used = _read_sysfs_int(card_dir / "device" / "mem_info_vram_used")
        gpu_busy = _read_sysfs_int(card_dir / "device" / "gpu_busy_percent")
        temp: Optional[float] = None
        hwmon_dir = card_dir / "device" / "hwmon"
        if hwmon_dir.exists():
            for h in sorted(hwmon_dir.iterdir()):
                raw = _read_sysfs_int(h / "temp1_input")
                if raw is not None:
                    temp = round(raw / 1000.0, 1)
                    break
        product_name = _read_sysfs_str(card_dir / "device" / "product_name") or "AMD GPU"
        vram_total_mb = (vram_total or 0) / (1024 * 1024)
        vram_used_mb = (vram_used or 0) / (1024 * 1024)
        gpus.append(GpuStats(
            name=product_name,
            load_percent=float(gpu_busy) if gpu_busy is not None else 0.0,
            memory_used_mb=round(vram_used_mb, 1),
            memory_total_mb=round(vram_total_mb, 1),
            temperature=temp,
            vendor="AMD",
            vram_gb=round(vram_total_mb / 1024, 2) if vram_total_mb > 0 else None,
        ))
    return gpus


def _read_gpus_intel() -> list[GpuStats]:
    """Lê informações básicas de GPU Intel via sysfs DRM."""
    gpus: list[GpuStats] = []
    drm_base = Path("/sys/class/drm")
    if not drm_base.exists():
        return gpus
    for card_dir in sorted(drm_base.iterdir()):
        if not re.fullmatch(r"card\d+", card_dir.name):
            continue
        vendor_id = _read_sysfs_str(card_dir / "device" / "vendor") or ""
        if vendor_id != "0x8086":  # Intel vendor ID
            continue
        product_name = _read_sysfs_str(card_dir / "device" / "product_name") or "Intel Graphics"
        gpus.append(GpuStats(
            name=product_name,
            load_percent=0.0,
            memory_used_mb=0.0,
            memory_total_mb=0.0,
            vendor="Intel",
        ))
    return gpus


def _read_gpus_lspci() -> list[GpuStats]:
    """Fallback: detecta GPUs via lspci."""
    gpus: list[GpuStats] = []
    try:
        output = subprocess.check_output(
            ["lspci", "-mmv"], text=True, stderr=subprocess.DEVNULL, timeout=5
        )
        current: dict[str, str] = {}
        for line in output.splitlines() + [""]:
            if not line.strip():
                if current:
                    gpu_class = current.get("Class", "").lower()
                    if any(k in gpu_class for k in ("vga", "3d", "display", "render")):
                        vendor = current.get("Vendor", "Unknown")
                        device = current.get("Device", "Unknown")
                        gpus.append(GpuStats(
                            name=f"{vendor} {device}".strip(),
                            load_percent=0.0,
                            memory_used_mb=0.0,
                            memory_total_mb=0.0,
                            vendor=_detect_gpu_vendor(vendor),
                        ))
                    current = {}
            elif ":" in line:
                k, _, v = line.partition(":")
                current[k.strip()] = v.strip()
    except Exception as exc:  # noqa: BLE001
        logger.debug("lspci indisponível: %s", exc)
    return gpus


def _read_gpus() -> list[GpuStats]:
    """Detecta GPUs usando método adequado por vendor: NVIDIA → AMD → Intel → lspci."""
    if _OS == "Windows":
        # Tenta LHM primeiro – métricas completas (temp, carga, VRAM)
        gpus = _read_gpus_from_lhm()
        if gpus:
            return gpus
        # Fallback: GPUtil (NVIDIA via nvidia-smi)
        gpus = _read_gpus_nvidia()
        if not gpus:
            # Fallback final: WMI (info básica, sem métricas em tempo real)
            try:
                import wmi  # type: ignore[import]
                w = wmi.WMI()
                for g in w.Win32_VideoController():
                    name = g.Caption or "GPU"
                    vram_bytes = int(g.AdapterRAM or 0)
                    vram_mb = vram_bytes / (1024 * 1024)
                    gpus.append(GpuStats(
                        name=name,
                        load_percent=0.0,
                        memory_used_mb=0.0,
                        memory_total_mb=vram_mb,
                        vendor=_detect_gpu_vendor(name),
                        driver_version=g.DriverVersion,
                        vram_gb=round(vram_mb / 1024, 2) if vram_mb > 0 else None,
                    ))
            except Exception:  # noqa: BLE001
                pass
        return gpus

    # Linux: NVIDIA → AMD → Intel → lspci
    gpus = _read_gpus_nvidia()
    gpus += _read_gpus_amd()
    gpus += _read_gpus_intel()
    if not gpus:
        logger.debug("GPUtil/sysfs não encontraram GPU; tentando lspci…")
        gpus = _read_gpus_lspci()
    return gpus


# ─────────────────────────────────────────────────────────────────────────────
# Detecção de RAM via dmidecode (slots físicos reais)
# ─────────────────────────────────────────────────────────────────────────────


def _read_memory_slots_linux() -> tuple[float, list[MemorySlot]]:
    """
    Lê informações de cada slot de memória RAM via dmidecode (Type 17).

    Isso corrige o problema de o psutil reportar apenas a RAM visível ao
    container (ex: 7.7 GB do Docker VM) em vez do total físico (ex: 16 GB).

    Retorna: (hardware_total_gb, [MemorySlot, ...])
    """
    slots: list[MemorySlot] = []
    hardware_total_gb = 0.0

    try:
        output = subprocess.check_output(
            ["dmidecode", "-t", "memory"],
            text=True, stderr=subprocess.DEVNULL, timeout=10,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("dmidecode indisponível: %s", exc)
        return hardware_total_gb, slots

    current: dict[str, str] = {}

    def _flush() -> None:
        nonlocal hardware_total_gb
        size_str = current.get("Size", "No Module Installed")
        if "No Module" in size_str or size_str in ("", "Unknown"):
            return
        size_gb = 0.0
        try:
            if "MB" in size_str:
                size_gb = int(size_str.split()[0]) / 1024
            elif "GB" in size_str:
                size_gb = float(size_str.split()[0])
        except (ValueError, IndexError):
            return
        if size_gb <= 0:
            return
        hardware_total_gb += size_gb
        speed_mhz: Optional[int] = None
        m = re.search(r"(\d+)", current.get("Speed", ""))
        if m:
            speed_mhz = int(m.group(1))

        def _clean(val: Optional[str]) -> Optional[str]:
            return val if val and val not in ("Unknown", "Not Specified") else None

        slots.append(MemorySlot(
            device_locator=current.get("Locator", current.get("Device Locator", "")),
            size_gb=round(size_gb, 2),
            speed_mhz=speed_mhz,
            manufacturer=_clean(current.get("Manufacturer")),
            part_number=_clean(current.get("Part Number", "").strip()) or None,
            form_factor=_clean(current.get("Form Factor")),
            memory_type=_clean(current.get("Type") or current.get("Memory Type")),
        ))

    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Memory Device"):
            _flush()
            current = {}
        elif ":" in stripped:
            k, _, v = stripped.partition(":")
            current[k.strip()] = v.strip()
    _flush()  # último bloco

    logger.info("dmidecode: %d slot(s), total físico=%.1f GB", len(slots), hardware_total_gb)
    return round(hardware_total_gb, 2), slots


class HardwareMonitor:
    """Coleta e armazena em cache dados de telemetria de hardware."""

    def __init__(self) -> None:
        self._latest_snapshot: Optional[HardwareSnapshot] = None
        self._running = False
        # Cache dos slots de RAM (dmidecode é caro; lemos apenas uma vez)
        self._mem_slots_cache: Optional[tuple[float, list[MemorySlot]]] = None
        # Cache do mapeamento de partições → disco físico (lemos apenas uma vez)
        self._physical_disks_cache: Optional[dict] = None
        # Buffer circular de histórico de snapshots (configurável por HISTORY_MAX_POINTS)
        from app.core.config import settings as _s
        self._history: deque[HardwareSnapshot] = deque(maxlen=_s.HISTORY_MAX_POINTS)
        # Inicia o leitor LHM em background no Windows
        if _OS == "Windows":
            _start_lhm_reader()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def get_snapshot(self) -> Optional[HardwareSnapshot]:
        """Retorna o snapshot coletado mais recentemente."""
        return self._latest_snapshot

    def get_history(self, limit: int = 60) -> list[HardwareSnapshot]:
        """Retorna os últimos `limit` snapshots do buffer circular de histórico.

        Args:
            limit: Número máximo de entradas a retornar.
                   Limitado ao tamanho atual do buffer.
        """
        items = list(self._history)
        return items[-limit:] if limit < len(items) else items

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
        self._history.append(snapshot)
        return snapshot

    async def start_polling(
        self,
        interval: float,
        ws_manager: "WebSocketManager",
    ) -> None:
        """Tarefa em background – coleta telemetria e envia via WebSocket."""
        self._running = True
        logger.info("Coleta de hardware iniciada (intervalo=%.1fs)", interval)
        try:
            while self._running:
                try:
                    snapshot = self.collect()
                    await ws_manager.broadcast(snapshot.model_dump())
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Erro na coleta de hardware: %s", exc)
                await asyncio.sleep(interval)
        finally:
            if _OS == "Windows":
                _stop_lhm_reader()

    # ------------------------------------------------------------------
    # Métodos privados auxiliares
    # ------------------------------------------------------------------

    def _cpu_stats(self) -> CpuStats:
        per_core = psutil.cpu_percent(percpu=True)
        overall = sum(per_core) / len(per_core) if per_core else 0.0
        freq = psutil.cpu_freq()
        temp = self._cpu_package_temp()

        temperature_note: Optional[str] = None
        if temp is None and _OS == "Windows":
            temperature_note = "run_as_admin"
            if not getattr(self, "_temp_warn_logged", False):
                logger.warning(
                    "Temperatura da CPU indisponível. O LibreHardwareMonitor "
                    "requer privilégios de administrador para acessar sensores "
                    "de temperatura via MSR. Reinicie o backend como administrador "
                    "ou execute o LHM como admin antes de iniciar o servidor."
                )
                self._temp_warn_logged = True  # type: ignore[attr-defined]

        return CpuStats(
            usage_percent=round(overall, 1),
            per_core=[round(c, 1) for c in per_core],
            frequency_mhz=round(freq.current, 1) if freq else None,
            temperature=temp,
            temperature_note=temperature_note,
        )

    def _cpu_package_temp(self) -> Optional[float]:
        """Extrai a temperatura do pacote CPU.

        Windows – prioridade:
          1. LHM JSON reader (processo PS em background com a DLL)
          2. LHM WMI namespace ou ACPI thermal zone (PowerShell, sem pacote wmi)
          3. pacote Python wmi (se instalado)
        Linux:
          psutil.sensors_temperatures()
        """
        if _OS == "Windows":
            # 1) LHM JSON reader (background PS process com DLL)
            lhm = _read_temps_windows_lhm()
            for component in lhm:
                for sensor in component.sensors:
                    if "package" in sensor.label.lower():
                        return sensor.current
            # 2) PowerShell puro: LHM WMI namespace → ACPI thermal zone (cacheado)
            ps_temp = _read_cpu_temp_windows_ps()
            if ps_temp is not None:
                return ps_temp
            # 3) Fallback: pacote Python wmi (LHM versões antigas com namespace WMI)
            temps = _read_temps_windows()
        else:
            temps = _read_temps_linux()
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
        """
        Coleta estatísticas de memória.

        Usa psutil para uso em tempo real (percentual, usado, disponível) e
        dmidecode para o total físico real (hardware_total_gb + slots).
        Corrige a leitura parcial dentro de containers Docker onde psutil
        reporta apenas a RAM alocada ao VM Linux (ex: 7.7 GB em vez de 16 GB).
        """
        mem = psutil.virtual_memory()
        gb = 1024 ** 3

        hardware_total_gb: Optional[float] = None
        slots: list[MemorySlot] = []

        if _OS == "Linux":
            if self._mem_slots_cache is None:
                self._mem_slots_cache = _read_memory_slots_linux()
            if self._mem_slots_cache[0] > 0:
                hardware_total_gb, slots = self._mem_slots_cache
        elif _OS == "Windows":
            if self._mem_slots_cache is None:
                self._mem_slots_cache = _read_memory_slots_windows()
            if self._mem_slots_cache[0] > 0:
                hardware_total_gb, slots = self._mem_slots_cache

        return MemoryStats(
            total_gb=round(mem.total / gb, 2),
            used_gb=round(mem.used / gb, 2),
            available_gb=round(mem.available / gb, 2),
            percent=mem.percent,
            hardware_total_gb=hardware_total_gb,
            slots=slots,
        )

    def _disk_stats(self) -> list[DiskStats]:
        # Popula o cache do mapa físico na primeira chamada (operação lenta)
        if self._physical_disks_cache is None:
            if _OS == "Windows":
                self._physical_disks_cache = _read_physical_disk_map_windows()
            elif _OS == "Linux":
                self._physical_disks_cache = _read_physical_disk_map_linux()
            else:
                self._physical_disks_cache = {}
        phys_map = self._physical_disks_cache

        disks: list[DiskStats] = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                gb = 1024 ** 3
                phys = phys_map.get(part.mountpoint)
                disks.append(
                    DiskStats(
                        device=part.device,
                        mountpoint=part.mountpoint,
                        total_gb=round(usage.total / gb, 2),
                        used_gb=round(usage.used / gb, 2),
                        percent=usage.percent,
                        model=phys[0] if phys else None,
                        media_type=phys[1] if phys else None,
                        physical_size_gb=phys[2] if phys else None,
                    )
                )
            except PermissionError:
                continue
        return disks

    def _temperatures(self) -> list[TemperatureComponent]:
        if _OS == "Linux":
            return _read_temps_linux()
        elif _OS == "Windows":
            # Tenta LHM direto (DLL via PowerShell reader) primeiro;
            # cai para WMI se o reader ainda não tiver dados.
            lhm = _read_temps_windows_lhm()
            return lhm if lhm else _read_temps_windows()
        return []
