"""
Task Queue Service - Background task processing
"""

import os
import uuid
import json
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import desc, case, update
from models.database import TaskDB
from exceptions import TaskQueueError
import threading

# Try to import asyncio for WebSocket notifications (optional)
try:
    import asyncio
    HAS_ASYNCIO = True
except ImportError:
    HAS_ASYNCIO = False


class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(str, Enum):
    """Task priority (stored as string; use rank() for ordering)"""
    HIGH = "high"      # Crisis mode, urgent requests
    MEDIUM = "medium"  # Regular chat requests
    LOW = "low"        # Background analysis, summaries

    @classmethod
    def rank(cls, priority: str) -> int:
        """Numeric rank for sorting (lower = higher priority)."""
        return {
            cls.HIGH.value: 0,
            cls.MEDIUM.value: 1,
            cls.LOW.value: 2,
        }.get(priority, 1)


class TaskQueue:
    """
    Task queue service with database persistence
    
    Features:
    - Task priority support (high/medium/low)
    - Task status management
    - Automatic retry mechanism
    - Task timeout handling
    - Database persistence
    """
    
    def __init__(self, max_retries: int = 3, default_timeout: int = 300):
        """
        Initialize task queue
        
        Args:
            max_retries: Maximum number of retries for failed tasks
            default_timeout: Default task timeout in seconds
        """
        self.max_retries = max_retries
        self.default_timeout = default_timeout
        self.lock = threading.Lock()
    
    def create_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        user_id: str,
        db: Session,
        priority: TaskPriority = TaskPriority.MEDIUM,
        timeout: Optional[int] = None
    ) -> str:
        """
        Create a new task and add to queue
        
        Args:
            task_type: Type of task (e.g., 'ai_chat', 'tracking_analysis')
            task_data: Task data dictionary
            user_id: User ID who created the task
            db: Database session
            priority: Task priority
            timeout: Task timeout in seconds (optional)
        
        Returns:
            Task ID
        """
        task_id = f"{task_type}_{uuid.uuid4().hex[:12]}"
        timeout = timeout or self.default_timeout
        
        try:
            task = TaskDB(
                task_id=task_id,
                task_type=task_type,
                task_data=json.dumps(task_data),
                user_id=user_id,
                status=TaskStatus.PENDING.value,
                priority=priority.value,
                timeout_seconds=timeout,
                created_at=datetime.utcnow()
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            
            # Notify WebSocket subscribers about new task (non-blocking)
            try:
                from services.websocket_manager import connection_manager
                task_dict = self._task_to_dict(task)
                # Use background thread for async notification
                def notify_ws():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            connection_manager.broadcast_task_update(task_id, task_dict)
                        )
                        loop.close()
                    except Exception:
                        pass  # Ignore WebSocket errors
                
                thread = threading.Thread(target=notify_ws, daemon=True)
                thread.start()
            except Exception:
                pass  # WebSocket notification is optional
            
            return task_id
        except Exception as e:
            db.rollback()
            raise TaskQueueError(f"Failed to create task: {str(e)}")
    
    def get_task(self, task_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        task = db.query(TaskDB).filter(TaskDB.task_id == task_id).first()
        if task:
            return self._task_to_dict(task)
        return None
    
    def get_pending_tasks(self, db: Session, limit: int = 100) -> List[Dict[str, Any]]:
        """Get pending tasks for worker processing"""
        priority_rank = case(
            (TaskDB.priority == TaskPriority.HIGH.value, 0),
            (TaskDB.priority == TaskPriority.MEDIUM.value, 1),
            (TaskDB.priority == TaskPriority.LOW.value, 2),
            else_=1,
        )
        query = db.query(TaskDB).filter(
            TaskDB.status == TaskStatus.PENDING.value
        ).order_by(
            priority_rank.asc(),
            TaskDB.created_at.asc()
        ).limit(limit)
        
        tasks = query.all()
        return [self._task_to_dict(task) for task in tasks]
    
    def get_user_tasks(
        self,
        user_id: str,
        db: Session,
        status: Optional[TaskStatus] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get tasks for a user"""
        query = db.query(TaskDB).filter(TaskDB.user_id == user_id)
        if status:
            query = query.filter(TaskDB.status == status.value)
        tasks = query.order_by(desc(TaskDB.created_at)).limit(limit).all()
        return [self._task_to_dict(task) for task in tasks]
    
    def claim_task(self, task_id: str, worker_id: str, db: Session) -> bool:
        """
        Atomically claim a pending task for processing.

        Uses a conditional UPDATE so only one worker can claim a task.
        """
        try:
            now = datetime.utcnow()
            rows_updated = db.execute(
                update(TaskDB)
                .where(
                    TaskDB.task_id == task_id,
                    TaskDB.status == TaskStatus.PENDING.value,
                )
                .values(
                    status=TaskStatus.PROCESSING.value,
                    worker_id=worker_id,
                    started_at=now,
                    updated_at=now,
                )
            ).rowcount
            db.commit()
            return rows_updated > 0
        except Exception:
            db.rollback()
            return False
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        db: Session,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Update task status
        
        Args:
            task_id: Task ID
            status: New status
            db: Database session
            result: Task result (if completed)
            error: Error message (if failed)
        
        Returns:
            True if updated successfully
        """
        try:
            task = db.query(TaskDB).filter(TaskDB.task_id == task_id).first()
            if not task:
                return False
            
            task.status = status.value
            task.updated_at = datetime.utcnow()
            
            if status == TaskStatus.COMPLETED:
                task.completed_at = datetime.utcnow()
                if result:
                    task.result = json.dumps(result)
            elif status == TaskStatus.FAILED:
                task.error = error
                task.retry_count = (task.retry_count or 0) + 1
                
                # Check if should retry
                if task.retry_count < self.max_retries:
                    task.status = TaskStatus.RETRYING.value
                    task.retry_count = task.retry_count
                    # Reset to pending for retry
                    task.status = TaskStatus.PENDING.value
                    task.worker_id = None
                    task.started_at = None
            
            db.commit()
            
            # Notify WebSocket subscribers about task update (non-blocking)
            try:
                from services.websocket_manager import connection_manager
                task_dict = self._task_to_dict(task)
                # Use background thread for async notification
                def notify_ws():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            connection_manager.broadcast_task_update(task_id, task_dict)
                        )
                        loop.close()
                    except Exception:
                        pass  # Ignore WebSocket errors
                
                thread = threading.Thread(target=notify_ws, daemon=True)
                thread.start()
            except Exception:
                pass  # WebSocket notification is optional
            
            return True
        except Exception as e:
            db.rollback()
            return False
    
    def cancel_task(self, task_id: str, user_id: str, db: Session) -> bool:
        """
        Cancel a task (only if pending or processing)
        
        Args:
            task_id: Task ID to cancel
            user_id: User ID (must match task owner)
            db: Database session
        
        Returns:
            True if cancelled successfully
        """
        try:
            task = db.query(TaskDB).filter(
                TaskDB.task_id == task_id,
                TaskDB.user_id == user_id
            ).first()
            
            if not task:
                return False
            
            # Only cancel if pending or processing
            if task.status in [TaskStatus.PENDING.value, TaskStatus.PROCESSING.value]:
                task.status = TaskStatus.CANCELLED.value
                task.updated_at = datetime.utcnow()
                db.commit()
                return True
            
            return False
        except Exception as e:
            db.rollback()
            return False
    
    def check_timeout_tasks(self, db: Session) -> List[str]:
        """
        Check for tasks that have timed out
        
        Args:
            db: Database session
        
        Returns:
            List of timed out task IDs
        """
        try:
            now = datetime.utcnow()
            timeout_tasks = db.query(TaskDB).filter(
                TaskDB.status == TaskStatus.PROCESSING.value,
                TaskDB.started_at.isnot(None)
            ).all()
            
            timed_out = []
            for task in timeout_tasks:
                if task.timeout_seconds and task.started_at:
                    elapsed = (now - task.started_at).total_seconds()
                    if elapsed > task.timeout_seconds:
                        # Mark as failed due to timeout
                        task.status = TaskStatus.FAILED.value
                        task.error = f"Task timed out after {task.timeout_seconds} seconds"
                        task.updated_at = now
                        timed_out.append(task.task_id)
            
            if timed_out:
                db.commit()
            
            return timed_out
        except Exception as e:
            db.rollback()
            return []
    
    def _task_to_dict(self, task: TaskDB) -> Dict[str, Any]:
        """Convert database task to dictionary"""
        result = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "task_data": json.loads(task.task_data) if task.task_data else {},
            "user_id": task.user_id,
            "status": task.status,
            "priority": task.priority,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "worker_id": task.worker_id,
            "retry_count": task.retry_count or 0,
            "timeout_seconds": task.timeout_seconds
        }
        
        if task.result:
            result["result"] = json.loads(task.result)
        
        if task.error:
            result["error"] = task.error
        
        return result

