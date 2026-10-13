"""
Personalization Routes - API endpoints for user personalization
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from dependencies.database import get_db
from middleware.auth import get_current_user
from middleware.authorization import check_user_authorization
from models.schemas import User, PersonalizationRequest
from services.personalization_service import PersonalizationService
from services.tracking_service import TrackingService
from exceptions import (
    PostpartumException,
    DatabaseError
)
from dependencies.container import get_container

router = APIRouter(tags=["personalization"])

# Get service instances from container
container = get_container()


class UserContextUpdate(BaseModel):
    context: Dict[str, Any]
    user_id: Optional[str] = None  # Compatibility only; identity comes from JWT.


@router.get("/api/user/{user_id}/personalization")
async def get_personalization_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's personalization profile
    
    Returns comprehensive personalization data including:
    - Response style preferences
    - Tone preferences
    - Detail level preferences
    - Preferred topics
    - Interaction patterns
    - Baby stage
    - Customizations
    """
    check_user_authorization(current_user, user_id, "personalization profile")
    personalization_service = container.get("personalization_service")
    
    try:
        profile = await personalization_service.get_personalization_profile(user_id, db)
        return profile
    except PostpartumException:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to get personalization profile: {str(e)}")


@router.post("/api/user/personalization")
async def update_personalization(
    request: PersonalizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's personalization preferences
    
    Allows users to customize:
    - Response style (brief, detailed, balanced)
    - Tone preference (warm, professional, casual)
    - Detail level (minimal, moderate, comprehensive)
    - Preferred topics
    - Custom preferences
    """
    check_user_authorization(current_user, request.user_id, "personalization preferences")
    personalization_service = container.get("personalization_service")
    
    try:
        # Convert Pydantic model to dict, filtering None values
        preferences_dict = {
            k: v for k, v in request.preferences.dict().items()
            if v is not None
        }
        
        result = await personalization_service.update_personalization_preferences(
            request.user_id,
            preferences_dict,
            db
        )
        return result
    except PostpartumException:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to update personalization preferences: {str(e)}")


@router.post("/api/user/context")
async def update_user_context(
    request: UserContextUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update supplied user context fields; omitted fields are preserved.
    """
    if request.user_id is not None:
        check_user_authorization(current_user, request.user_id, "user context")
    tracking_service = container.get("tracking_service")
    
    try:
        result = await tracking_service.update_user_context(current_user.user_id, request.context, db)
        return result
    except PostpartumException:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to update user context: {str(e)}")


@router.get("/api/user/{user_id}/context")
async def get_user_context(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user context
    """
    check_user_authorization(current_user, user_id, "user context")
    tracking_service = container.get("tracking_service")
    
    try:
        context = await tracking_service.get_user_context(user_id, db)
        return context
    except PostpartumException:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to get user context: {str(e)}")

