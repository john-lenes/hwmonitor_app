"""Router WebSocket – expõe o endpoint /ws."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
ws_router = APIRouter()


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Stream de telemetria de hardware em tempo real."""
    manager = websocket.app.state.ws_manager
    await manager.connect(websocket)
    try:
        # Mantém a conexão viva; o cliente pode enviar frames de ping
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
