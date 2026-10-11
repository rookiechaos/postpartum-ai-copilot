"""
Monitoring API Routes - System monitoring and metrics endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime
from sqlalchemy.orm import Session
from services.health_check_service import get_health_check_service
from middleware.performance import performance_metrics
from middleware.admin import require_admin
from models.schemas import User
from services.logging_service import logger
from dependencies.database import get_db

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/health")
async def get_health_check(db: Session = Depends(get_db)):
    """Public database readiness probe; never include diagnostic details."""
    try:
        health_service = get_health_check_service()
        healthy = health_service.check_database(db).get("status") == "healthy"
    except Exception as e:
        logger.log_error(e, context={"action": "public_health_check"})
        healthy = False
    return JSONResponse(status_code=200 if healthy else 503, content={
        "status": "healthy" if healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
    })


@router.get("/health/details")
async def get_health_details(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Component diagnostics are available only to provisioned administrators."""
    try:
        return get_health_check_service().get_comprehensive_health(db)
    except Exception as e:
        logger.log_error(e, context={"action": "health_details"})
        raise HTTPException(status_code=503, detail="Health diagnostics unavailable")


@router.get("/metrics")
async def get_metrics(
    current_user: User = Depends(require_admin)
):
    """
    Get performance metrics
    
    Requires administrator access.
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
        logger.log_error(e, context={"action": "monitoring_metrics"})
        raise HTTPException(status_code=503, detail="Metrics unavailable")


@router.get("/tasks")
async def get_task_queue_stats(
    current_user: User = Depends(require_admin),
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
        logger.log_error(e, context={"action": "monitoring_tasks"})
        raise HTTPException(status_code=503, detail="Task statistics unavailable")


@router.get("/system")
async def get_system_resources(
    current_user: User = Depends(require_admin)
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
        logger.log_error(e, context={"action": "monitoring_system"})
        raise HTTPException(status_code=503, detail="System statistics unavailable")

