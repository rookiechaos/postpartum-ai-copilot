"""
Milestone Routes - User milestones API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from dependencies.container import get_container
from services.logging_service import logger
from exceptions import DatabaseError

router = APIRouter(prefix="/api/milestones", tags=["milestones"])
container = get_container()


@router.get("/check")
async def check_milestones(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check for newly achieved milestones"""
    try:
        milestone_service = container.get("milestone_service")
        milestones = milestone_service.check_milestones(
            user_id=current_user.user_id,
            db=db
        )
        return {"milestones": milestones}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to check milestones: {str(e)}")


@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user statistics for milestone display"""
    try:
        milestone_service = container.get("milestone_service")
        stats = milestone_service.get_user_stats(
            user_id=current_user.user_id,
            db=db
        )
        return {"stats": stats}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get user stats: {str(e)}")

