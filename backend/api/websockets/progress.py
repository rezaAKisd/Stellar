"""WebSocket endpoint for real-time progress updates"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from fastapi.exceptions import WebSocketException

from core.security import verify_token
from api.websockets.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/progress")
async def websocket_progress(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token")
):
    """
    WebSocket endpoint for receiving real-time progress updates.

    Clients must provide a valid JWT token in the query parameters.
    Once connected, they will receive progress messages for their tasks.

    Message format:
    {
        "type": "download_progress" | "export_progress" | "task_complete" | "error",
        "project_id": "uuid",
        "progress": 0.0-1.0,  # Optional
        "status": "downloading" | "building" | "downloaded" | "exported",  # Optional
        "message": "Error message"  # Optional, only for error type
    }

    Args:
        websocket: The WebSocket connection
        token: JWT authentication token from query params
    """
    # Verify JWT token before accepting connection
    try:
        payload = verify_token(token)
        username = payload.get("sub")

        if not username:
            logger.warning("WebSocket connection rejected: invalid token payload")
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid authentication token"
            )

    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {str(e)}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication failed"
        )

    # Accept connection and register with manager
    await manager.connect(websocket, username)

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": f"Connected to progress updates for user: {username}"
        })

        # Keep connection alive and listen for messages
        # (In this implementation, we only send server->client messages)
        while True:
            try:
                # Receive messages from client (for heartbeat/ping)
                data = await websocket.receive_text()

                # Handle ping/pong for keeping connection alive
                if data == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user: {username}")
                break
            except Exception as e:
                logger.error(f"Error receiving WebSocket message: {str(e)}")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {username}")
    except Exception as e:
        logger.error(f"WebSocket error for user {username}: {str(e)}")
    finally:
        # Clean up connection
        manager.disconnect(websocket, username)


async def broadcast_progress(
    user: str,
    project_id: str,
    progress_type: str,
    progress: float = None,
    status: str = None,
    message: str = None,
    task_id: str = None,
    task_type: str = None
):
    """
    Helper function to broadcast progress updates to a user's WebSocket connections.

    Args:
        user: Username to send the update to
        project_id: ID of the project being updated
        progress_type: Type of progress ("download_progress", "export_progress", "task_complete", "error")
        progress: Progress value 0.0-1.0 (optional)
        status: Current status (optional)
        message: Error or info message (optional)
        task_id: ID of the specific task (optional)
        task_type: Type of task ("download", "build", "create_zip") (optional)
    """
    payload = {
        "type": progress_type,
        "project_id": project_id
    }

    if progress is not None:
        payload["progress"] = progress

    if status is not None:
        payload["status"] = status

    if task_id is not None:
        payload["task_id"] = task_id

    if task_type is not None:
        payload["task_type"] = task_type

    if message is not None:
        payload["message"] = message

    await manager.send_personal_message(payload, user)
    logger.debug(f"Broadcasted {progress_type} for project {project_id} to user {user}")
