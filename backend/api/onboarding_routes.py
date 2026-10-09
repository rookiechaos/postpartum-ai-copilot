"""
Onboarding Routes - API endpoints for onboarding progress
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from dependencies.container import get_container
from exceptions import DatabaseError, NotFoundError

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])
container = get_container()


class OnboardingProgressUpdate(BaseModel):
    """Onboarding progress update request"""
    current_step: int = Field(..., ge=0, description="Current step index")
    completed_steps: Optional[List[str]] = Field(None, description="List of completed step IDs")
    personalization_data: Optional[Dict[str, Any]] = Field(None, description="Personalization data")
    is_completed: bool = Field(False, description="Whether onboarding is completed")
    is_skipped: bool = Field(False, description="Whether onboarding was skipped")


class StepCompletedRequest(BaseModel):
    """Mark step as completed request"""
    step_id: str = Field(..., description="Step ID to mark as completed")


class PersonalizationDataRequest(BaseModel):
    """Save personalization data request"""
    personalization_data: Dict[str, Any] = Field(..., description="Personalization data")


@router.get("/progress")
async def get_onboarding_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get onboarding progress for current user
    
    Returns:
        Onboarding progress or None if not started
    """
    try:
        onboarding_service = container.get("onboarding_service")
        progress = onboarding_service.get_progress(current_user.user_id, db)
        
        if not progress:
            return {"progress": None, "message": "Onboarding not started"}
        
        return {"progress": progress}
    except Exception as e:
        raise DatabaseError(
            f"Failed to get onboarding progress: {str(e)}",
            details={"user_id": current_user.user_id, "original_error": str(e)}
        )


@router.post("/progress")
async def update_onboarding_progress(
    update: OnboardingProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update onboarding progress
    
    Args:
        update: Progress update data
    
    Returns:
        Updated onboarding progress
    """
    try:
        onboarding_service = container.get("onboarding_service")
        progress = onboarding_service.create_or_update_progress(
            user_id=current_user.user_id,
            current_step=update.current_step,
            completed_steps=update.completed_steps,
            personalization_data=update.personalization_data,
            is_completed=update.is_completed,
            is_skipped=update.is_skipped,
            db=db
        )
        
        return {"progress": progress, "message": "Progress updated successfully"}
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to update onboarding progress: {str(e)}",
            details={"user_id": current_user.user_id, "original_error": str(e)}
        )


@router.post("/step-completed")
async def mark_step_completed(
    request: StepCompletedRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a specific step as completed
    
    Args:
        request: Step completion data
    
    Returns:
        Updated onboarding progress
    """
    try:
        onboarding_service = container.get("onboarding_service")
        progress = onboarding_service.mark_step_completed(
            user_id=current_user.user_id,
            step_id=request.step_id,
            db=db
        )
        
        return {"progress": progress, "message": "Step marked as completed"}
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to mark step as completed: {str(e)}",
            details={"user_id": current_user.user_id, "step_id": request.step_id, "original_error": str(e)}
        )


@router.post("/personalization")
async def save_personalization_data(
    request: PersonalizationDataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save personalization data during onboarding
    
    Args:
        request: Personalization data
    
    Returns:
        Updated onboarding progress
    """
    try:
        onboarding_service = container.get("onboarding_service")
        progress = onboarding_service.save_personalization_data(
            user_id=current_user.user_id,
            personalization_data=request.personalization_data,
            db=db
        )
        
        return {"progress": progress, "message": "Personalization data saved"}
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to save personalization data: {str(e)}",
            details={"user_id": current_user.user_id, "original_error": str(e)}
        )

