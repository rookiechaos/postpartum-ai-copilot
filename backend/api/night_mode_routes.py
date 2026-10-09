"""
Night Mode Routes - Relaxation, breathing exercises, safety tips
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from dependencies.container import get_container
from services.logging_service import logger
from exceptions import DatabaseError
from utils.user_preferences import get_user_language_preference

router = APIRouter(prefix="/api/night-mode", tags=["night-mode"])
container = get_container()


@router.post("/relaxation")
async def get_relaxation_guide(
    guide_type: Optional[str] = Query(None, description="Specific guide type"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get relaxation guide
    
    Args:
        guide_type: Specific guide type (optional)
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        Relaxation guide with steps and timestamp
    """
    try:
        relaxation_service = container.get("relaxation_service")
        language = await get_user_language_preference(
            user_id=current_user.user_id if current_user else None,
            db=db,
            default="en"
        )
        
        guide = relaxation_service.get_relaxation_guide(
            language=language,
            guide_type=guide_type
        )
        return guide
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id if current_user else None)
        raise DatabaseError(f"Failed to get relaxation guide: {str(e)}")


@router.post("/breathing")
async def get_breathing_exercise(
    exercise_type: Optional[str] = Query(None, description="Specific exercise type"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get breathing exercise
    
    Args:
        exercise_type: Specific exercise type (optional)
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        Breathing exercise with steps and timestamp
    """
    try:
        relaxation_service = container.get("relaxation_service")
        language = await get_user_language_preference(
            user_id=current_user.user_id if current_user else None,
            db=db,
            default="en"
        )
        
        exercise = relaxation_service.get_breathing_exercise(
            language=language,
            exercise_type=exercise_type
        )
        return exercise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id if current_user else None)
        raise DatabaseError(f"Failed to get breathing exercise: {str(e)}")


@router.get("/safety-tips")
async def get_safety_tips(
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get safety tips for postpartum mothers
    
    Args:
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        Safety tips with emergency message and timestamp
    """
    try:
        relaxation_service = container.get("relaxation_service")
        language = await get_user_language_preference(
            user_id=current_user.user_id if current_user else None,
            db=db,
            default="en"
        )
        
        tips = relaxation_service.get_safety_tips(language=language)
        return tips
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id if current_user else None)
        raise DatabaseError(f"Failed to get safety tips: {str(e)}")


@router.get("/quick-calm")
async def get_quick_calm_tips(
    count: int = Query(3, ge=1, le=10, description="Number of tips"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get quick calm tips
    
    Args:
        count: Number of tips to return (1-10)
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        List of quick calm tips with timestamp
    """
    try:
        relaxation_service = container.get("relaxation_service")
        language = await get_user_language_preference(
            user_id=current_user.user_id if current_user else None,
            db=db,
            default="en"
        )
        
        tips = relaxation_service.get_quick_calm_tips(language=language, count=count)
        return tips
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id if current_user else None)
        raise DatabaseError(f"Failed to get quick calm tips: {str(e)}")

