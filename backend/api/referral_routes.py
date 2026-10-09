"""
Referral Routes - User referral system API
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user, get_optional_user
from models.schemas import User
from dependencies.container import get_container
from services.logging_service import logger
from exceptions import DatabaseError, ValidationError

router = APIRouter(prefix="/api/referrals", tags=["referrals"])
container = get_container()


class ReferralTrackRequest(BaseModel):
    """Referral tracking request"""
    referred_user_id: str = Field(..., description="User ID of referred user")
    referral_code: Optional[str] = Field(None, description="Referral code used")


@router.get("/code")
async def get_referral_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get or generate referral code for current user"""
    try:
        referral_service = container.get("referral_service")
        code = referral_service.generate_referral_code(
            user_id=current_user.user_id,
            db=db
        )
        return {"referral_code": code, "user_id": current_user.user_id}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get referral code: {str(e)}")


@router.post("/track")
async def track_referral(
    request: ReferralTrackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track a referral"""
    try:
        if request.referred_user_id == current_user.user_id:
            raise ValidationError("Cannot refer yourself")
        
        referral_service = container.get("referral_service")
        referral = referral_service.track_referral(
            referrer_user_id=current_user.user_id,
            referred_user_id=request.referred_user_id,
            referral_code=request.referral_code,
            db=db
        )
        return {"referral": referral, "message": "Referral tracked successfully"}
    except (ValidationError, DatabaseError):
        raise
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to track referral: {str(e)}")


@router.get("/stats")
async def get_referral_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get referral statistics for current user"""
    try:
        referral_service = container.get("referral_service")
        stats = referral_service.get_referral_stats(
            user_id=current_user.user_id,
            days=days,
            db=db
        )
        return {"stats": stats}
    except Exception as e:
        logger.log_error(e, user_id=current_user.user_id)
        raise DatabaseError(f"Failed to get referral stats: {str(e)}")


@router.get("/validate/{referral_code}")
async def validate_referral_code(
    referral_code: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Validate a referral code"""
    try:
        referral_service = container.get("referral_service")
        validation = referral_service.validate_referral_code(
            referral_code=referral_code,
            db=db
        )
        
        if validation:
            return {"valid": True, "referral_code": referral_code}
        else:
            return {"valid": False, "message": "Invalid referral code"}
    except Exception as e:
        logger.log_error(e)
        return {"valid": False, "message": "Error validating code"}

