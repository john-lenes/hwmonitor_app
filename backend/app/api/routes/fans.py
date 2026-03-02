"""Endpoints REST de controle de ventoinhas."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.models.fan import FanReading, FanSpeedRequest

router = APIRouter()


@router.get("/", response_model=list[FanReading])
async def list_fans(request: Request) -> list[FanReading]:
    """Retorna todas as ventoinhas detectadas e seu RPM atual."""
    controller = request.app.state.fan_controller
    return controller.list_fans()


@router.post("/{fan_id}/speed")
async def set_fan_speed(fan_id: str, body: FanSpeedRequest, request: Request) -> dict:
    """Define a velocidade de uma ventoinha específica (percentual 0–100)."""
    controller = request.app.state.fan_controller
    success = controller.set_speed(fan_id, body.percent)
    if not success:
        raise HTTPException(status_code=400, detail="Falha ao definir velocidade da ventoinha")
    return {"fan_id": fan_id, "percent": body.percent, "status": "ok"}


@router.post("/{fan_id}/auto")
async def restore_fan_auto(fan_id: str, request: Request) -> dict:
    """Restaura o controle automático (BIOS) de uma ventoinha específica."""
    controller = request.app.state.fan_controller
    success = controller.restore_auto(fan_id)
    if not success:
        raise HTTPException(status_code=400, detail="Falha ao restaurar controle automático")
    return {"fan_id": fan_id, "status": "auto"}


@router.post("/auto")
async def restore_all_auto(request: Request) -> dict:
    """Restaura o controle automático de todas as ventoinhas."""
    controller = request.app.state.fan_controller
    controller.restore_all_auto()
    return {"status": "todas as ventoinhas em modo automático"}
