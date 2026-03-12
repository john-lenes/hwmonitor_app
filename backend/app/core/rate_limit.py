"""Middleware de rate limiting por IP – janela deslizante em memória.

Sem dependências externas (sem Redis, sem slowapi).
Aplica limites apenas em requisições mutantes (POST/PUT/PATCH/DELETE) em /api/*.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window per-IP rate limiter para endpoints de escrita.

    Args:
        max_requests: Máximo de requisições permitidas na janela.
        window_seconds: Tamanho da janela em segundos.
        exempt_paths: Prefixos de path isentos do rate limiting.
    """

    _MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    def __init__(
        self,
        app: object,
        max_requests: int = 60,
        window_seconds: int = 60,
        exempt_paths: tuple[str, ...] = ("/api/health", "/api/v1/health"),
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._max = max_requests
        self._window = window_seconds
        self._exempt = exempt_paths
        # Mapa: IP → deque de timestamps das requisições recentes
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable[..., Response]) -> Response:
        # Isentar métodos de leitura e paths específicos
        if request.method not in self._MUTATING_METHODS:
            return await call_next(request)
        if any(request.url.path.startswith(p) for p in self._exempt):
            return await call_next(request)
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        ip = self._client_ip(request)
        now = time.monotonic()
        bucket = self._buckets[ip]

        # Remove entradas fora da janela
        cutoff = now - self._window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= self._max:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(self._window)},
                content={
                    "success": False,
                    "error": "RateLimitExceeded",
                    "detail": (
                        f"Máximo de {self._max} requisições por "
                        f"{self._window}s excedido. Tente novamente mais tarde."
                    ),
                    "path": str(request.url.path),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status_code": 429,
                },
            )

        bucket.append(now)
        return await call_next(request)
