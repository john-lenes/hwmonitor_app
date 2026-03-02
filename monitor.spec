# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for HardwareMonitor backend."""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "backend" / "app" / "main.py")],
    pathex=[str(ROOT / "backend")],
    binaries=[],
    datas=[
        (str(ROOT / "frontend" / "dist"), "frontend/dist"),
        (str(ROOT / "backend" / "data"), "data"),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "psutil",
        "cpuinfo",
        "GPUtil",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="hardware-monitor-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(ROOT / "frontend" / "public" / "icon.ico") if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="hardware-monitor-backend",
)
