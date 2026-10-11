"""
WebSocket Manager - Real-time communication for task updates
WebSocket manager - real-time communication for task updates
"""

from typing import Callable, Dict, Set
from fastapi import WebSocket
from datetime import datetime
from services.logging_service import logger


class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        # user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # task_id -> Set[WebSocket] (for task-specific subscriptions)
        self.task_subscriptions: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> user_id (for reverse lookup)
        self.connection_users: Dict[WebSocket, str] = {}
        self.session_validators: Dict[WebSocket, Callable[[], bool]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, validate_session: Callable[[], bool]):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id
        self.session_validators[websocket] = validate_session
        
        logger.log_info(f"WebSocket connected: user_id={user_id}", context={"user_id": user_id})
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        return websocket in self.connection_users
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.session_validators.pop(websocket, None)
        user_id = self.connection_users.get(websocket)
        if user_id:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove from task subscriptions
            for task_id, connections in list(self.task_subscriptions.items()):
                connections.discard(websocket)
                if not connections:
                    del self.task_subscriptions[task_id]
            
            del self.connection_users[websocket]
            logger.log_info(f"WebSocket disconnected: user_id={user_id}", context={"user_id": user_id})

    async def ensure_authenticated(self, websocket: WebSocket) -> bool:
        """Recheck current token, factor and account state before using a socket."""
        if websocket not in self.connection_users:
            return False
        validate = self.session_validators.get(websocket)
        try:
            valid = validate is not None and validate()
        except Exception as e:
            logger.log_error(e, context={"action": "websocket_session_check"})
            valid = False
        if not valid:
            self.disconnect(websocket)
            try:
                await websocket.close(code=1008, reason="Authentication required")
            except Exception:
                pass  # The peer may already have closed the connection.
        return bool(valid)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific WebSocket connection"""
        if not await self.ensure_authenticated(websocket):
            return
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.log_error(e, context={"action": "websocket_send"})
            self.disconnect(websocket)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections of a user"""
        if user_id not in self.active_connections:
            return
        
        for websocket in list(self.active_connections[user_id]):
            await self.send_personal_message(message, websocket)
    
    async def broadcast_task_update(self, task_id: str, task_data: dict):
        """Broadcast task update to all subscribers"""
        if task_id not in self.task_subscriptions:
            return
        
        message = {
            "type": "task_update",
            "task_id": task_id,
            "data": task_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for websocket in list(self.task_subscriptions[task_id]):
            await self.send_personal_message(message, websocket)
    
    def subscribe_to_task(self, websocket: WebSocket, task_id: str):
        """Subscribe a connection to task updates"""
        if websocket not in self.connection_users:
            return
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        self.task_subscriptions[task_id].add(websocket)
    
    def unsubscribe_from_task(self, websocket: WebSocket, task_id: str):
        """Unsubscribe a connection from task updates"""
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(websocket)
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]
    
    def get_user_connections_count(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        return len(self.active_connections.get(user_id, set()))
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())


# Global connection manager instance
connection_manager = ConnectionManager()
