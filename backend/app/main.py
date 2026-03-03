"""Ponto de entrada da aplicação backend."""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import hardware, fans, profiles, health
from app.core.config import settings
from app.core.logger import setup_logger
from app.services.hardware_monitor import HardwareMonitor
from app.services.fan_controller import FanController
from app.services.profile_manager import ProfileManager
from app.websocket.manager import WebSocketManager

setup_logger()
logger = logging.getLogger(__name__)

# Shared service instances (injected via app.state)
hardware_monitor: HardwareMonitor = HardwareMonitor()
fan_controller: FanController = FanController()
profile_manager: ProfileManager = ProfileManager()
ws_manager: WebSocketManager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida de inicialização e desligamento da aplicação."""
    logger.info("Iniciando HardwareMonitor backend v%s", settings.APP_VERSION)

    # Armazena serviços compartilhados no estado da aplicação
    app.state.hardware_monitor = hardware_monitor
    app.state.fan_controller = fan_controller
    app.state.profile_manager = profile_manager
    app.state.ws_manager = ws_manager

    # Inicia a tarefa de coleta em background
    poll_task = asyncio.create_task(
        hardware_monitor.start_polling(
            interval=settings.POLL_INTERVAL_SECONDS,
            ws_manager=ws_manager,
        )
    )

    yield

    logger.info("Encerrando HardwareMonitor backend")
    poll_task.cancel()
    try:
        await poll_task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="API de monitoramento de temperatura de hardware e controle de ventoinhas",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS – permite o renderer Electron e o servidor de dev Vite
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rotas REST
    app.include_router(health.router)
    app.include_router(hardware.router, prefix="/api/hardware", tags=["hardware"])
    app.include_router(fans.router, prefix="/api/fans", tags=["fans"])
    app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])

    # Endpoint WebSocket
    from app.websocket import ws_router
    app.include_router(ws_router)

    # Serve o app React compilado em produção
    try:
        app.mount("/", StaticFiles(directory=settings.STATIC_DIR, html=True), name="static")
    except RuntimeError:
        logger.warning("Diretório de estáticos '%s' não encontrado – rodando apenas como API.", settings.STATIC_DIR)

    return app


app = create_app()


def main() -> None:
    """Run the server – entry point for PyInstaller."""

    def _handle_exit(sig, frame):  # noqa: ANN001
        logger.info("Received signal %s, exiting.", sig)
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_exit)
    signal.signal(signal.SIGTERM, _handle_exit)

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
