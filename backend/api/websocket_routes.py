"""
WebSocket Routes - Real-time communication endpoints
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import connection_manager
from dependencies.container import get_container
from dependencies.database import SessionLocal
from services.logging_service import logger
import json

router = APIRouter()
container = get_container()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates
    
    Clients should connect with user authentication token in query params:
    ws://localhost:8000/ws?token=<jwt_token>
    """
    # Get user_id from query params or headers
    user_id = None
    try:
        # Try to get token from query params
        token = websocket.query_params.get("token")
        if token:
            auth_service = container.get("auth_service")
            with SessionLocal() as db:
                token_data = auth_service.verify_token(token, token_type="access", db=db)
                user = auth_service.get_user_by_id(token_data.user_id, db) if token_data else None
                if user and user.is_active:
                    user_id = user.user_id
    except Exception as e:
        logger.log_error(e, context={"action": "websocket_auth"})
    
    if not user_id:
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    # Connect the WebSocket
    await connection_manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "subscribe_task":
                    task_id = message.get("task_id")
                    if task_id:
                        db = SessionLocal()
                        try:
                            task_queue = container.get("task_queue")
                            task = task_queue.get_task(task_id, db)
                            if not task or task.get("user_id") != user_id:
                                await connection_manager.send_personal_message({
                                    "type": "error",
                                    "message": "Unauthorized task subscription",
                                    "task_id": task_id,
                                }, websocket)
                                continue
                            connection_manager.subscribe_to_task(websocket, task_id)
                            await connection_manager.send_personal_message({
                                "type": "subscription",
                                "status": "subscribed",
                                "task_id": task_id,
                            }, websocket)
                        finally:
                            db.close()
                
                elif message_type == "unsubscribe_task":
                    # Unsubscribe from task updates
                    task_id = message.get("task_id")
                    if task_id:
                        connection_manager.unsubscribe_from_task(websocket, task_id)
                        await connection_manager.send_personal_message({
                            "type": "subscription",
                            "status": "unsubscribed",
                            "task_id": task_id
                        }, websocket)
                
                elif message_type == "ping":
                    # Heartbeat
                    await connection_manager.send_personal_message({
                        "type": "pong"
                    }, websocket)
                
                else:
                    await connection_manager.send_personal_message({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    }, websocket)
                    
            except json.JSONDecodeError:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, websocket)
                
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.log_error(e, context={"action": "websocket_error", "user_id": user_id})
        connection_manager.disconnect(websocket)
