"""
Task API Routes - Task management endpoints
"""

from fastapi import APIRouter, Depends, status, Query, Request
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.schemas import (
    TaskRequest, TaskResponse, TaskStatus, TaskPriority
)
from middleware.auth import get_current_user
from middleware.admin import require_admin
from models.schemas import User
from dependencies.database import get_db
from dependencies.container import get_container
from exceptions import TaskQueueError, NotFoundError, DatabaseError, ValidationError
from middleware.rate_limit import rate_limit, RATE_LIMITS

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
container = get_container()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
@rate_limit(RATE_LIMITS["task"])
async def create_task(
    request: Request,
    task_request: TaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new task
    
    Returns task_id immediately (202 Accepted) for async processing
    """
    try:
        task_queue = container.get("task_queue")
        task_id = task_queue.create_task(
            task_type=task_request.task_type,
            task_data=task_request.task_data,
            user_id=current_user.user_id,
            db=db,
            priority=task_request.priority or TaskPriority.MEDIUM,
            timeout=task_request.timeout
        )
        
        # Get the created task
        task = task_queue.get_task(task_id, db)
        if not task:
            raise TaskQueueError(
                "Failed to create task",
                details={"task_id": task_id}
            )
        
        return TaskResponse(**task)
    except (TaskQueueError, NotFoundError, DatabaseError, ValidationError):
        raise
    except Exception as e:
        raise TaskQueueError(
            f"Failed to create task: {str(e)}",
            details={"original_error": str(e)}
        )


@router.get("/{task_id}", response_model=TaskResponse)
@rate_limit(RATE_LIMITS["default"])
async def get_task(
    request: Request,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get task status and result
    
    Client should poll this endpoint to check task status
    """
    task_queue = container.get("task_queue")
    task = task_queue.get_task(task_id, db)
    
    if not task:
        raise NotFoundError("Task not found")
    
    # Check if user owns the task
    from middleware.authorization import check_user_authorization
    check_user_authorization(current_user, task["user_id"], "task")
    
    return TaskResponse(**task)


@router.get("", response_model=List[TaskResponse])
async def get_user_tasks(
    status: Optional[TaskStatus] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all tasks for the current user
    
    Args:
        status: Filter by task status (optional)
        limit: Maximum number of tasks to return
    """
    task_queue = container.get("task_queue")
    tasks = task_queue.get_user_tasks(
        user_id=current_user.user_id,
        db=db,
        status=status,
        limit=limit
    )
    
    return [TaskResponse(**task) for task in tasks]


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a task (only if pending or processing)
    """
    task_queue = container.get("task_queue")
    success = task_queue.cancel_task(task_id, current_user.user_id, db)
    
    if not success:
        raise TaskQueueError(
            "Task cannot be cancelled or not found",
            details={"task_id": task_id, "user_id": current_user.user_id}
        )
    
    return None


@router.get("/stats/summary")
async def get_task_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get task statistics for current user
    
    Returns:
    - Task counts by status
    - Task type distribution
    - Success rate
    - Average processing time
    """
    try:
        analytics_service = container.get("analytics_service")
        stats = analytics_service.get_user_usage_stats(current_user.user_id, db, days=days)
        return stats
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to get task stats: {str(e)}",
            details={"user_id": current_user.user_id, "days": days, "original_error": str(e)}
        )


@router.get("/stats/performance")
async def get_task_performance(
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get task performance statistics
    
    Returns:
    - Average processing time
    - P95/P99 processing times
    - Task completion rates
    """
    try:
        analytics_service = container.get("analytics_service")
        stats = analytics_service.get_task_performance_stats(db, task_type=task_type, days=days)
        return stats
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to get performance stats: {str(e)}",
            details={"task_type": task_type, "days": days, "original_error": str(e)}
        )

