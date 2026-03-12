"""Health-check endpoint – usado pelo Docker HEALTHCHECK e load balancers."""

from __future__ import annotations

import platform
import time
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

_START_TIME = time.time()


class HealthResponse(BaseModel):
    success: bool = True
    status: str
    uptime_seconds: float
    version: str
    timestamp: str
    os: str


@router.get(
    "",
    response_model=HealthResponse,
    summary="Verifica o estado de saúde do serviço",
    description=(
        "Retorna status, uptime, versão e OS da API. "
        "Usado pelo Docker HEALTHCHECK e por load balancers."
    ),
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        uptime_seconds=round(time.time() - _START_TIME, 1),
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        os=platform.system(),
    )
