from fastapi import WebSocket
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for multiple sessions"""

    def __init__(self):
        # Dictionary to store active connections: {session_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Connection established for session: {session_id}")
        logger.info(f"Total active connections: {len(self.active_connections)}")

    def disconnect(self, session_id: str):
        """Remove a WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Connection closed for session: {session_id}")
            logger.info(f"Total active connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, session_id: str):
        """Send a message to a specific session"""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected sessions"""
        for connection in self.active_connections.values():
            await connection.send_json(message)

    def get_connection(self, session_id: str) -> WebSocket:
        """Get a specific WebSocket connection"""
        return self.active_connections.get(session_id)

    def is_connected(self, session_id: str) -> bool:
        """Check if a session is connected"""
        return session_id in self.active_connections
