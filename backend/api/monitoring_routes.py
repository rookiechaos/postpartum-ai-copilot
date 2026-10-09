"""
Monitoring API Routes - System monitoring and metrics endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from services.health_check_service import get_health_check_service
from middleware.performance import performance_metrics
from middleware.auth import get_current_user
from models.schemas import User
from services.logging_service import logger
from dependencies.database import get_db

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/health")
async def get_health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check endpoint
    
    Returns detailed health status of all system components:
    - Database connectivity
    - AI provider status
    - Task queue status
    - System resources
    """
    try:
        health_service = get_health_check_service()
        health_status = health_service.get_comprehensive_health(db)
        return health_status
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/metrics")
async def get_metrics(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get performance metrics
    
    Requires authentication.
    Returns API performance statistics including:
    - Total requests
    - Average response time
    - P95/P99 response times
    - Status code distribution
    - Slow queries
    """
    try:
        stats = performance_metrics.get_stats()
        return {
            "metrics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/tasks")
async def get_task_queue_stats(
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get task queue statistics
    
    Returns:
    - Pending tasks count
    - Recent task statistics
    - Task processing rates
    """
    try:
        health_service = get_health_check_service()
        task_status = health_service.check_task_queue(db)
        return task_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task stats: {str(e)}")


@router.get("/system")
async def get_system_resources(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get system resource usage
    
    Returns:
    - CPU usage
    - Memory usage
    - Disk usage
    """
    try:
        health_service = get_health_check_service()
        system_status = health_service.check_system_resources()
        return system_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system resources: {str(e)}")

