"""
Recommendation Routes - Personalized recommendations API
"""

from fastapi import APIRouter, Depends, Query
from typing import List
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from dependencies.container import get_container
from services.logging_service import logger
from exceptions import DatabaseError

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])
container = get_container()


@router.get("/smart-reminders")
async def get_smart_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get smart reminders based on user behavior patterns"""
    try:
        recommendation_service = container.get("recommendation_service")
        reminders = recommendation_service.get_smart_reminders(
            user_id=current_user.user_id,
            db=db
        )
        return {"reminders": reminders}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get smart reminders: {str(e)}")


@router.get("/content")
async def get_content_recommendations(
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized content recommendations"""
    try:
        recommendation_service = container.get("recommendation_service")
        recommendations = recommendation_service.get_content_recommendations(
            user_id=current_user.user_id,
            db=db,
            limit=limit
        )
        return {"recommendations": recommendations}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get content recommendations: {str(e)}")


@router.get("/milestones")
async def get_milestones(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get milestone celebration suggestions"""
    try:
        recommendation_service = container.get("recommendation_service")
        milestones = recommendation_service.get_milestone_suggestions(
            user_id=current_user.user_id,
            db=db
        )
        return {"milestones": milestones}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get milestones: {str(e)}")

