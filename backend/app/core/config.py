"""Configurações da aplicação via variáveis de ambiente."""

import os
import sys
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_bundled() -> bool:
    """Retorna True quando executando dentro de um bundle PyInstaller."""
    return getattr(sys, "frozen", False)


BASE_DIR = Path(sys._MEIPASS) if _is_bundled() else Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Aplicação
    APP_NAME: str = "HardwareMonitor"
    APP_VERSION: str = "1.0.0"

    # Servidor
    # Em container Docker usa 0.0.0.0; localmente usa 127.0.0.1
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    LOG_LEVEL: str = "INFO"

    # CORS – em produção restringir à origem do frontend real
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",   # servidor de dev Vite
        "http://localhost:3000",
        "http://localhost",        # frontend via Nginx no Docker
        "http://127.0.0.1:5173",
        "app://.",                 # origem do Electron em produção
    ]

    # Coleta de dados
    POLL_INTERVAL_SECONDS: float = 2.0

    # Caminhos
    STATIC_DIR: str = str(BASE_DIR / "frontend" / "dist")
    DATA_DIR: str = str(BASE_DIR / "data")

    # Controle de ventoinhas
    FAN_CONTROL_ENABLED: bool = True

    # Histórico de snapshots em memória (ring buffer)
    HISTORY_MAX_POINTS: int = 120

    # Rate limiting – requisições de escrita (POST/PUT/PATCH/DELETE) por IP
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60


settings = Settings()

# Garante que o diretório de dados exista
os.makedirs(settings.DATA_DIR, exist_ok=True)
