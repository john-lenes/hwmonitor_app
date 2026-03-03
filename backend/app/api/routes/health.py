"""Health-check endpoint – usado pelo Docker HEALTHCHECK e load balancers."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

_START_TIME = time.time()


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    version: str


@router.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health_check(request: Request) -> HealthResponse:
    """Retorna o estado de saúde do serviço."""
    from app.core.config import settings

    return HealthResponse(
        status="ok",
        uptime_seconds=round(time.time() - _START_TIME, 1),
        version=settings.APP_VERSION,
    )
