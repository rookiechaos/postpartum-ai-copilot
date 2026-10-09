"""
Achievement Routes - Achievements and goals API
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from dependencies.container import get_container
from services.logging_service import logger
from exceptions import DatabaseError, NotFoundError

router = APIRouter(prefix="/api/achievements", tags=["achievements"])
container = get_container()


class GoalCreate(BaseModel):
    """Goal creation model"""
    goal_type: str = Field(..., description="Type of goal")
    target_value: Optional[int] = Field(None, description="Target value")
    period: str = Field("daily", description="Period: daily, weekly, monthly")


@router.get("/check")
async def check_achievements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check and unlock new achievements"""
    try:
        achievement_service = container.get("achievement_service")
        newly_unlocked = achievement_service.check_and_unlock_achievements(
            user_id=current_user.user_id,
            db=db
        )
        return {"newly_unlocked": newly_unlocked, "count": len(newly_unlocked)}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to check achievements: {str(e)}")


@router.get("")
async def get_user_achievements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all achievements for current user"""
    try:
        achievement_service = container.get("achievement_service")
        achievements = achievement_service.get_user_achievements(
            user_id=current_user.user_id,
            db=db
        )
        return {"achievements": achievements, "total": len(achievements)}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get achievements: {str(e)}")


@router.post("/goals")
async def create_goal(
    goal: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a user goal"""
    try:
        achievement_service = container.get("achievement_service")
        created_goal = achievement_service.create_user_goal(
            user_id=current_user.user_id,
            goal_type=goal.goal_type,
            target_value=goal.target_value,
            period=goal.period,
            db=db
        )
        return {"goal": created_goal}
    except DatabaseError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to create goal: {str(e)}")


@router.get("/goals")
async def get_goals(
    active_only: bool = Query(True, description="Return only active goals"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user goals"""
    try:
        achievement_service = container.get("achievement_service")
        goals = achievement_service.get_user_goals(
            user_id=current_user.user_id,
            db=db,
            active_only=active_only
        )
        return {"goals": goals, "total": len(goals)}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get goals: {str(e)}")


@router.post("/goals/{goal_id}/progress")
async def update_goal_progress(
    goal_id: int,
    increment: int = Query(1, ge=1, description="Increment value"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update goal progress"""
    try:
        achievement_service = container.get("achievement_service")
        result = achievement_service.update_goal_progress(
            goal_id=goal_id,
            user_id=current_user.user_id,
            increment=increment,
            db=db
        )
        return {"goal": result}
    except NotFoundError:
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to update goal progress: {str(e)}")

