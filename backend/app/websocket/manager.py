"""Gerenciador de conexões WebSocket."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Gerencia conexões WebSocket ativas e envia mensagens em broadcast."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
        logger.debug("Cliente WS conectado. Total: %d", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            try:
                self._connections.remove(websocket)
            except ValueError:
                pass
        logger.debug("Cliente WS desconectado. Total: %d", len(self._connections))

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Transmite um payload dict para todos os clientes conectados como JSON."""
        if not self._connections:
            return

        payload = json.dumps(data)
        dead: list[WebSocket] = []

        async with self._lock:
            connections_snapshot = list(self._connections)

        for ws in connections_snapshot:
            try:
                await ws.send_text(payload)
            except Exception:  # noqa: BLE001
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    try:
                        self._connections.remove(ws)
                    except ValueError:
                        pass
