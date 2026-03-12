"""Exceções customizadas e handlers globais de erro da aplicação."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Exceções de domínio
# ──────────────────────────────────────────────────────────────────────────────


class AppError(Exception):
    """Erro base da aplicação – mapeado automaticamente pelo handler global."""

    status_code: int = 500

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    """Recurso não encontrado (404)."""

    status_code = 404


class ConflictError(AppError):
    """Conflito de estado (ex: recurso já existe) (409)."""

    status_code = 409


class ServiceUnavailableError(AppError):
    """Serviço ou dependência temporariamente indisponível (503)."""

    status_code = 503


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _error_body(
    request: Request,
    status_code: int,
    error: str,
    detail: Any,
) -> dict[str, Any]:
    """Monta o payload de erro padronizado."""
    return {
        "success": False,
        "error": error,
        "detail": detail,
        "path": str(request.url.path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status_code": status_code,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Registro de handlers
# ──────────────────────────────────────────────────────────────────────────────


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos os handlers globais de exceção na instância FastAPI."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "AppError %s: %s | path=%s",
            exc.status_code,
            exc.detail,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(request, exc.status_code, type(exc).__name__, exc.detail),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        logger.warning(
            "HTTPException %s: %s | path=%s",
            exc.status_code,
            exc.detail,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(request, exc.status_code, "HTTPException", exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.warning(
            "ValidationError | path=%s | errors=%s",
            request.url.path,
            exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                request,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "ValidationError",
                exc.errors(),
            ),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Exceção não tratada | path=%s", request.url.path)
        return JSONResponse(
            status_code=500,
            content=_error_body(
                request,
                500,
                "InternalServerError",
                "Erro interno do servidor.",
            ),
        )
