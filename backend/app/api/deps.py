"""Helpers de injeção de dependência (FastAPI Depends).

Centraliza o acesso aos serviços compartilhados guardados em `app.state`,
evitando acesso direto a `request.app.state` espalhado pelos routers.

Uso:
    from app.api.deps import MonitorDep, FanControllerDep

    @router.get("/snapshot")
    async def get_snapshot(monitor: MonitorDep) -> HardwareSnapshot:
        ...
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.services.fan_controller import FanController
from app.services.hardware_monitor import HardwareMonitor
from app.services.profile_manager import ProfileManager
from app.websocket.manager import WebSocketManager


# ──────────────────────────────────────────────────────────────────────────────
# Funções privadas de resolução (chamadas pelo Depends)
# ──────────────────────────────────────────────────────────────────────────────


def _get_hardware_monitor(request: Request) -> HardwareMonitor:
    return request.app.state.hardware_monitor  # type: ignore[no-any-return]


def _get_fan_controller(request: Request) -> FanController:
    return request.app.state.fan_controller  # type: ignore[no-any-return]


def _get_profile_manager(request: Request) -> ProfileManager:
    return request.app.state.profile_manager  # type: ignore[no-any-return]


def _get_ws_manager(request: Request) -> WebSocketManager:
    return request.app.state.ws_manager  # type: ignore[no-any-return]


# ──────────────────────────────────────────────────────────────────────────────
# Type aliases anotados – use diretamente como parâmetros de rota
# ──────────────────────────────────────────────────────────────────────────────

MonitorDep = Annotated[HardwareMonitor, Depends(_get_hardware_monitor)]
FanControllerDep = Annotated[FanController, Depends(_get_fan_controller)]
ProfileManagerDep = Annotated[ProfileManager, Depends(_get_profile_manager)]
WsManagerDep = Annotated[WebSocketManager, Depends(_get_ws_manager)]
