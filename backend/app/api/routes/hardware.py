"""Endpoints REST de monitoramento de hardware."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.models.hardware import HardwareSnapshot

router = APIRouter()


@router.get("/snapshot", response_model=HardwareSnapshot)
async def get_snapshot(request: Request) -> HardwareSnapshot:
    """Retorna o snapshot mais recente de hardware."""
    monitor = request.app.state.hardware_monitor
    snapshot = monitor.get_snapshot()
    if snapshot is None:
        snapshot = monitor.collect()
    return snapshot


@router.get("/temperatures")
async def get_temperatures(request: Request) -> dict:
    """Retorna apenas os sensores de temperatura."""
    monitor = request.app.state.hardware_monitor
    snapshot = monitor.get_snapshot() or monitor.collect()
    return {"temperatures": [t.model_dump() for t in snapshot.temperatures]}


@router.get("/cpu")
async def get_cpu(request: Request) -> dict:
    """Retorna uso e temperatura da CPU."""
    monitor = request.app.state.hardware_monitor
    snapshot = monitor.get_snapshot() or monitor.collect()
    return snapshot.cpu.model_dump()


@router.get("/memory")
async def get_memory(request: Request) -> dict:
    """Retorna uso de memória."""
    monitor = request.app.state.hardware_monitor
    snapshot = monitor.get_snapshot() or monitor.collect()
    return snapshot.memory.model_dump()


@router.get("/disks")
async def get_disks(request: Request) -> dict:
    """Retorna uso de disco por partição."""
    monitor = request.app.state.hardware_monitor
    snapshot = monitor.get_snapshot() or monitor.collect()
    return {"disks": [d.model_dump() for d in snapshot.disks]}


@router.get("/gpus")
async def get_gpus(request: Request) -> dict:
    """Retorna estatísticas de GPU (NVIDIA via GPUtil)."""
    monitor = request.app.state.hardware_monitor
    snapshot = monitor.get_snapshot() or monitor.collect()
    return {"gpus": [g.model_dump() for g in snapshot.gpus]}
