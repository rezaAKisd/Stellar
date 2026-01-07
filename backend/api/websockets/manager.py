"""WebSocket Connection Manager for real-time updates"""
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time progress updates.

    Tracks active connections per user and provides methods for
    broadcasting messages to specific users or all connections.
    """

    def __init__(self):
        # Active connections: {user: Set[WebSocket]}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, user: str):
        """
        Accept a new WebSocket connection and register it for a user.

        Args:
            websocket: The WebSocket connection
            user: Username to associate with this connection
        """
        await websocket.accept()

        if user not in self.active_connections:
            self.active_connections[user] = set()

        self.active_connections[user].add(websocket)
        logger.info(f"WebSocket connected for user {user}. Total connections: {len(self.active_connections[user])}")

    def disconnect(self, websocket: WebSocket, user: str):
        """
        Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
            user: Username associated with the connection
        """
        if user in self.active_connections:
            self.active_connections[user].discard(websocket)

            # Clean up empty user entries
            if not self.active_connections[user]:
                del self.active_connections[user]

            logger.info(f"WebSocket disconnected for user {user}")

    async def send_personal_message(self, message: dict, user: str):
        """
        Send a message to all connections for a specific user.

        Args:
            message: Dictionary message to send (will be JSON serialized)
            user: Username to send the message to
        """
        if user not in self.active_connections:
            logger.debug(f"No active connections for user {user}")
            return

        # Send to all connections for this user
        disconnected = set()
        for connection in self.active_connections[user]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {user}: {str(e)}")
                disconnected.add(connection)

        # Remove any disconnected connections
        for connection in disconnected:
            self.disconnect(connection, user)

    async def broadcast(self, message: dict):
        """
        Broadcast a message to all connected users.

        Args:
            message: Dictionary message to send (will be JSON serialized)
        """
        for user in list(self.active_connections.keys()):
            await self.send_personal_message(message, user)

    def get_connection_count(self, user: str = None) -> int:
        """
        Get the number of active connections.

        Args:
            user: If provided, get count for specific user. Otherwise, total count.

        Returns:
            Number of active connections
        """
        if user:
            return len(self.active_connections.get(user, set()))
        else:
            return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()
