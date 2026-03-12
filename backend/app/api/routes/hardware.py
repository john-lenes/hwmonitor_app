"""Endpoints REST de monitoramento de hardware – /api/v1/hardware/..."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import MonitorDep
from app.models.hardware import HardwareSnapshot

router = APIRouter()


@router.get(
    "/snapshot",
    response_model=HardwareSnapshot,
    summary="Snapshot completo de hardware",
    description="Retorna o snapshot mais recente de CPU, RAM, discos, GPUs e sensores.",
)
async def get_snapshot(monitor: MonitorDep) -> HardwareSnapshot:
    snapshot = monitor.get_snapshot()
    if snapshot is None:
        snapshot = monitor.collect()
    return snapshot


@router.get(
    "/history",
    response_model=list[HardwareSnapshot],
    summary="Histórico de snapshots",
    description=(
        "Retorna os últimos `limit` snapshots coletados em memória. "
        "Configurável via `HISTORY_MAX_POINTS` no ambiente. "
        "Útil para análises e gráficos sem depender do WebSocket."
    ),
)
async def get_history(
    monitor: MonitorDep,
    limit: Annotated[
        int,
        Query(ge=1, le=500, description="Número de entradas a retornar (1–500)"),
    ] = 60,
) -> list[HardwareSnapshot]:
    return monitor.get_history(limit=limit)


@router.get(
    "/temperatures",
    summary="Sensores de temperatura",
    description="Retorna apenas os grupos de sensores de temperatura do snapshot atual.",
)
async def get_temperatures(monitor: MonitorDep) -> dict:
    snapshot = monitor.get_snapshot() or monitor.collect()
    return {"temperatures": [t.model_dump() for t in snapshot.temperatures]}


@router.get(
    "/cpu",
    summary="Estatísticas da CPU",
    description="Retorna uso percentual, uso por núcleo, frequência e temperatura da CPU.",
)
async def get_cpu(monitor: MonitorDep) -> dict:
    snapshot = monitor.get_snapshot() or monitor.collect()
    return snapshot.cpu.model_dump()


@router.get(
    "/memory",
    summary="Estatísticas de memória",
    description="Retorna uso de RAM, total físico (via dmidecode/WMI) e detalhes por slot.",
)
async def get_memory(monitor: MonitorDep) -> dict:
    snapshot = monitor.get_snapshot() or monitor.collect()
    return snapshot.memory.model_dump()


@router.get(
    "/disks",
    summary="Uso de disco",
    description="Retorna uso de cada partição/volume detectado, incluindo modelo e tipo do disco físico.",
)
async def get_disks(monitor: MonitorDep) -> dict:
    snapshot = monitor.get_snapshot() or monitor.collect()
    return {"disks": [d.model_dump() for d in snapshot.disks]}


@router.get(
    "/gpus",
    summary="Estatísticas de GPU",
    description="Retorna carga, temperatura e uso de VRAM de todas as GPUs detectadas.",
)
async def get_gpus(monitor: MonitorDep) -> dict:
    snapshot = monitor.get_snapshot() or monitor.collect()
    return {"gpus": [g.model_dump() for g in snapshot.gpus]}
