"""Endpoints REST de controle de ventoinhas – /api/v1/fans/..."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import FanControllerDep
from app.models.fan import SPEED_MODES, FanModeRequest, FanReading, FanSpeedRequest

router = APIRouter()

_VALID_MODES = frozenset({*SPEED_MODES.keys(), "auto"})


@router.get(
    "/",
    response_model=list[FanReading],
    summary="Lista ventoinhas",
    description="Retorna todas as ventoinhas detectadas, RPM atual, modo ativo e se são controláveis.",
)
async def list_fans(controller: FanControllerDep) -> list[FanReading]:
    return controller.list_fans()


@router.post(
    "/{fan_id}/speed",
    summary="Define velocidade por percentual",
    description=(
        "Define a velocidade de uma ventoinha específica (0–100 %). "
        "No Linux, escreve no sysfs PWM. No Windows, salva em memória."
    ),
)
async def set_fan_speed(
    fan_id: str,
    body: FanSpeedRequest,
    controller: FanControllerDep,
) -> dict:
    if not controller.set_speed(fan_id, body.percent):
        raise HTTPException(status_code=400, detail="Falha ao definir velocidade da ventoinha.")
    return {"fan_id": fan_id, "percent": body.percent, "status": "ok"}


@router.post(
    "/{fan_id}/mode",
    summary="Define modo de velocidade",
    description=(
        "Define o modo de velocidade de uma ventoinha.\n\n"
        "- **quiet** → 30 % – Silencioso\n"
        "- **balanced** → 60 % – Balanceado\n"
        "- **turbo** → 100 % – Performance máxima\n"
        "- **auto** → Restaura controle automático da BIOS"
    ),
)
async def set_fan_mode(
    fan_id: str,
    body: FanModeRequest,
    controller: FanControllerDep,
) -> dict:
    if body.mode not in _VALID_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Modo inválido '{body.mode}'. Aceitos: {', '.join(sorted(_VALID_MODES))}.",
        )
    if not controller.set_mode(fan_id, body.mode):
        raise HTTPException(status_code=400, detail="Falha ao definir modo da ventoinha.")
    return {"fan_id": fan_id, "mode": body.mode, "status": "ok"}


@router.post(
    "/{fan_id}/auto",
    summary="Restaura controle automático de uma ventoinha",
)
async def restore_fan_auto(fan_id: str, controller: FanControllerDep) -> dict:
    if not controller.restore_auto(fan_id):
        raise HTTPException(status_code=400, detail="Falha ao restaurar controle automático.")
    return {"fan_id": fan_id, "status": "auto"}


@router.post(
    "/auto",
    summary="Restaura controle automático de todas as ventoinhas",
)
async def restore_all_auto(controller: FanControllerDep) -> dict:
    controller.restore_all_auto()
    return {"status": "todas as ventoinhas em modo automático"}
