"""
Monitoring API Routes - System monitoring and metrics endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from services.health_check_service import get_health_check_service
from middleware.performance import performance_metrics
from middleware.admin import require_admin
from models.schemas import User
from services.logging_service import logger
from dependencies.database import get_db
from services.directory_review import resource_digest
from models.database import AccountRequestDB, AccountWorkflowDB, TaskDB, DirectoryWorkspaceDB, PilotProfileDB, DirectoryReviewTaskDB

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/actions")
def operator_actions(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """A bounded action summary. No questions, health text, emails or request references."""
    now = datetime.utcnow()
    pending = db.query(AccountRequestDB).filter(AccountRequestDB.status.in_(("received", "verifying")))
    overdue = pending.join(AccountWorkflowDB, AccountWorkflowDB.reference == AccountRequestDB.reference).filter(
        AccountWorkflowDB.details["expected_reply_at"].as_string() < now.isoformat() + "Z").count()
    ai = db.query(TaskDB).filter(TaskDB.task_type.in_(("ai_chat", "tracking_analysis", "personalized_chat")))
    waiting = ai.filter(TaskDB.status.in_(("pending", "retrying")))
    oldest = waiting.with_entities(func.min(TaskDB.created_at)).scalar()
    workspace = db.get(DirectoryWorkspaceDB, "local")
    published = db.get(PilotProfileDB, "local")
    profile = workspace.profile if workspace else published.profile if published else {}
    tasks = {row.contact_key: row for row in db.query(DirectoryReviewTaskDB).all()}
    today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    review_cutoff = (datetime.now(timezone(timedelta(hours=9))).date() - timedelta(days=30)).isoformat()
    contacts = []
    for contact in profile.get("resources", []):
        task = tasks.get(contact.get("resource_key"))
        details = task.details if task else {}
        due = details.get("next_review_on") or contact.get("review_due_on")
        stale = task is not None and task.resource_digest != resource_digest(contact)
        postponed = task is not None and not stale and details.get("decision") != "pending" and due and due > today
        if postponed:
            continue
        checked = contact.get("checked_on")
        if stale or details.get("decision") == "pending" or not checked or checked <= review_cutoff or not due or due <= today:
            contacts.append({"contact_key": contact.get("resource_key"), "name": contact.get("name", ""),
                "assignee": details.get("assignee") or contact.get("maintainer", ""), "due_on": due})
    contacts.sort(key=lambda contact: contact["due_on"] or "")
    return {"checked_at": now.isoformat() + "Z", "requests": {
        "received": pending.filter(AccountRequestDB.status == "received").count(),
        "verifying": pending.filter(AccountRequestDB.status == "verifying").count(), "overdue": overdue},
        "ai": {"waiting": waiting.count(), "waiting_long": waiting.filter(TaskDB.created_at < now - timedelta(minutes=15)).count(),
            "oldest_at": oldest.isoformat() + "Z" if oldest else None,
            "failed_last_day": ai.filter(TaskDB.status == "failed", TaskDB.updated_at >= now - timedelta(days=1)).count()},
        "directory": {"due_count": len(contacts), "contacts": contacts[:10]}}


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

