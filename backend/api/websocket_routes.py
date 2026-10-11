"""
WebSocket Routes - Authenticated real-time communication endpoints
"""

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import connection_manager
from dependencies.container import get_container
from dependencies.database import SessionLocal
from services.logging_service import logger

router = APIRouter()
container = get_container()
AUTH_RECHECK_INTERVAL_SECONDS = 30


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Authenticate on connection, incoming messages, pushes and idle intervals."""
    token = websocket.query_params.get("token")

    def authenticated_user_id():
        if not token:
            return None
        try:
            auth_service = container.get("auth_service")
            with SessionLocal() as db:
                claims = auth_service.verify_token(token, token_type="access", db=db)
                user = auth_service.get_user_by_id(claims.user_id, db) if claims else None
                if user and user.is_active:
                    return user.user_id
        except Exception as e:
            logger.log_error(e, context={"action": "websocket_auth"})
        return None

    user_id = authenticated_user_id()
    if not user_id:
        await websocket.close(code=1008, reason="Authentication required")
        return

    try:
        connected = await connection_manager.connect(
            websocket, user_id, validate_session=lambda: authenticated_user_id() == user_id,
        )
        if not connected:
            return

        while await connection_manager.ensure_authenticated(websocket):
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=AUTH_RECHECK_INTERVAL_SECONDS,
                )
            except asyncio.TimeoutError:
                continue  # Revalidate idle sockets, including token expiry.
            if not await connection_manager.ensure_authenticated(websocket):
                break
            try:
                message = json.loads(data)
                if not isinstance(message, dict):
                    raise ValueError("Message must be an object")
            except (json.JSONDecodeError, ValueError):
                await connection_manager.send_personal_message({
                    "type": "error", "message": "Invalid message format",
                }, websocket)
                continue

            message_type = message.get("type")
            task_id = message.get("task_id")
            if message_type == "subscribe_task" and isinstance(task_id, str) and task_id:
                with SessionLocal() as db:
                    task = container.get("task_queue").get_task(task_id, db)
                if not task or task.get("user_id") != user_id:
                    await connection_manager.send_personal_message({
                        "type": "error", "message": "Unauthorized task subscription",
                        "task_id": task_id,
                    }, websocket)
                    continue
                connection_manager.subscribe_to_task(websocket, task_id)
                await connection_manager.send_personal_message({
                    "type": "subscription", "status": "subscribed", "task_id": task_id,
                }, websocket)
            elif message_type == "unsubscribe_task" and isinstance(task_id, str) and task_id:
                connection_manager.unsubscribe_from_task(websocket, task_id)
                await connection_manager.send_personal_message({
                    "type": "subscription", "status": "unsubscribed", "task_id": task_id,
                }, websocket)
            elif message_type == "ping":
                await connection_manager.send_personal_message({"type": "pong"}, websocket)
            else:
                await connection_manager.send_personal_message({
                    "type": "error", "message": "Unknown message type",
                }, websocket)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.log_error(e, context={"action": "websocket_error", "user_id": user_id})
    finally:
        connection_manager.disconnect(websocket)
