"""
websocket_service.py
────────────────────
WebSocket connection manager for live prediction broadcasts.

Usage from route handlers:
    from backend.services.websocket_service import ws_manager

    await ws_manager.broadcast({"type": "weather_update", "city_id": 42, ...})
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """Manages a pool of active WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.debug(f"WS connected: {websocket.client}. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.debug(f"WS disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Send a JSON message to all connected clients."""
        message = json.dumps(data)
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.disconnect(d)

    async def send_to(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        """Send a JSON message to a specific client."""
        try:
            await websocket.send_text(json.dumps(data))
        except Exception:
            self.disconnect(websocket)


# ─── Global singleton ─────────────────────────────────────────────────────────
ws_manager = ConnectionManager()
