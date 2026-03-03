"""Configuração centralizada de logging."""

import logging
import os
import sys
from pathlib import Path


def setup_logger() -> None:
    """Configura o logger raiz com saída no console e, opcionalmente, em arquivo.

    Em ambientes de container (LOG_FORMAT=json) usa formato compatível com
    agregadores de log como Loki, Datadog e CloudWatch.
    """
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
    ]

    # Handler de arquivo – grava ao lado do executável ou na raiz do projeto
    # Não cria arquivo de log em container (é melhor deixar o stdout para o runtime)
    running_in_container = os.path.exists("/.dockerenv")
    if not running_in_container:
        try:
            log_path = Path("hardware_monitor.log")
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter(fmt=log_format, datefmt=date_format)
            )
            handlers.append(file_handler)
        except OSError:
            pass  # Ignora escrever em arquivo se o caminho não for gravável

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )
