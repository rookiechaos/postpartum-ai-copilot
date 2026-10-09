"""
User Health Routes - User health scoring API
"""

from fastapi import APIRouter, Depends, Query
from typing import List
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from middleware.admin import require_admin
from models.schemas import User
from dependencies.container import get_container
from services.logging_service import logger
from exceptions import DatabaseError

router = APIRouter(prefix="/api/health", tags=["user-health"])
container = get_container()


@router.get("/score")
async def get_health_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user health score"""
    try:
        health_service = container.get("user_health_service")
        score = health_service.calculate_health_score(
            user_id=current_user.user_id,
            db=db
        )
        return {"health": score}
    except DatabaseError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to calculate health score: {str(e)}")


@router.get("/at-risk")
async def get_at_risk_users(
    days: int = Query(7, ge=1, le=30, description="Days of inactivity"),
    threshold: float = Query(40.0, ge=0, le=100, description="Health score threshold"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get list of at-risk users (admin only)"""
    try:
        health_service = container.get("user_health_service")
        at_risk = health_service.identify_at_risk_users(
            days=days,
            threshold=threshold,
            db=db
        )
        return {"at_risk_users": at_risk, "count": len(at_risk)}
    except Exception as e:
        logger.log_error(e)
        raise DatabaseError(f"Failed to get at-risk users: {str(e)}")


@router.get("/interventions")
async def get_interventions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get intervention suggestions for improving user health"""
    try:
        health_service = container.get("user_health_service")
        suggestions = health_service.get_intervention_suggestions(
            user_id=current_user.user_id,
            db=db
        )
        return {"suggestions": suggestions, "count": len(suggestions)}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get interventions: {str(e)}")

