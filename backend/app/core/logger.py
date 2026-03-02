"""Configuração centralizada de logging."""

import logging
import sys
from pathlib import Path


def setup_logger() -> None:
    """Configura o logger raiz com saída no console e, opcionalmente, em arquivo."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
    ]

    # Handler de arquivo – grava ao lado do executável ou na raiz do projeto
    try:
        log_path = Path("hardware_monitor.log")
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        handlers.append(file_handler)
    except OSError:
        pass  # Ignora escrever em arquivo se o caminho não for gravável

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )
