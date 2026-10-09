"""
Family Routes - API endpoints for family sharing
"""

from fastapi import APIRouter, Depends, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from dependencies.container import get_container
from middleware.authorization import check_user_authorization
from exceptions import DatabaseError, NotFoundError, ValidationError, ConflictError

router = APIRouter()
container = get_container()


class FamilyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class FamilyInvite(BaseModel):
    invitee_user_id: str
    role: str = Field(default="member", pattern="^(owner|admin|member|viewer)$")


class FamilyResponse(BaseModel):
    family_id: str
    name: str
    created_by: str
    created_at: str
    updated_at: str


@router.post("/", response_model=FamilyResponse)
async def create_family(
    family: FamilyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new family group"""
    try:
        family_service = container.get("family_service")
        created = family_service.create_family(
            user_id=current_user.user_id,
            name=family.name,
            db=db
        )
        return FamilyResponse(**created)
    except (ValidationError, ConflictError):
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to create family: {str(e)}",
            details={"user_id": current_user.user_id, "family_name": family.name, "original_error": str(e)}
        )


@router.get("/", response_model=List[FamilyResponse])
async def get_user_families(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all families the user belongs to"""
    try:
        family_service = container.get("family_service")
        families = family_service.get_user_families(
            user_id=current_user.user_id,
            db=db
        )
        return [FamilyResponse(**f) for f in families]
    except Exception as e:
        raise DatabaseError(
            f"Failed to get families: {str(e)}",
            details={"user_id": current_user.user_id, "original_error": str(e)}
        )


@router.post("/{family_id}/invite")
async def invite_member(
    family_id: str,
    invite: FamilyInvite,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invite a user to join the family"""
    try:
        family_service = container.get("family_service")
        result = family_service.invite_member(
            family_id=family_id,
            inviter_user_id=current_user.user_id,
            invitee_user_id=invite.invitee_user_id,
            role=invite.role,
            db=db
        )
        return result
    except (ValidationError, NotFoundError, ConflictError):
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to invite member: {str(e)}",
            details={"family_id": family_id, "invitee_user_id": invite.invitee_user_id, "original_error": str(e)}
        )


@router.post("/{family_id}/accept")
async def accept_invitation(
    family_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept a family invitation"""
    try:
        family_service = container.get("family_service")
        success = family_service.accept_invitation(
            family_id=family_id,
            user_id=current_user.user_id,
            db=db
        )
        return {"status": "accepted", "family_id": family_id}
    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to accept invitation: {str(e)}",
            details={"family_id": family_id, "user_id": current_user.user_id, "original_error": str(e)}
        )


@router.get("/{family_id}/members")
async def get_family_members(
    family_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all members of a family"""
    try:
        family_service = container.get("family_service")
        members = family_service.get_family_members(
            family_id=family_id,
            user_id=current_user.user_id,
            db=db
        )
        return {"family_id": family_id, "members": members}
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to get family members: {str(e)}",
            details={"family_id": family_id, "user_id": current_user.user_id, "original_error": str(e)}
        )


@router.get("/{family_id}/shared-data")
async def get_shared_tracking_data(
    family_id: str,
    days: int = Query(7, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get shared tracking data from all family members"""
    try:
        family_service = container.get("family_service")
        data = family_service.get_shared_tracking_data(
            family_id=family_id,
            user_id=current_user.user_id,
            days=days,
            db=db
        )
        return {"family_id": family_id, "data": data, "days": days}
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to get shared tracking data: {str(e)}",
            details={"family_id": family_id, "user_id": current_user.user_id, "days": days, "original_error": str(e)}
        )


@router.delete("/{family_id}/members/{member_user_id}")
async def remove_member(
    family_id: str,
    member_user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a member from the family"""
    try:
        family_service = container.get("family_service")
        success = family_service.remove_member(
            family_id=family_id,
            member_user_id=member_user_id,
            remover_user_id=current_user.user_id,
            db=db
        )
        return {"status": "removed", "member_user_id": member_user_id}
    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to remove member: {str(e)}",
            details={"family_id": family_id, "member_user_id": member_user_id, "original_error": str(e)}
        )


@router.get("/{family_id}/summary")
async def get_family_summary(
    family_id: str,
    period: str = Query("daily", pattern="^(daily|weekly)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get family summary for partner viewing"""
    try:
        from services.tracking_service import TrackingService
        from services.ai_service import AIService
        
        family_service = container.get("family_service")
        tracking_service = container.get("tracking_service")
        ai_service = container.get("ai_service")
        
        summary = await family_service.generate_family_summary(
            family_id=family_id,
            user_id=current_user.user_id,
            period=period,
            tracking_service=tracking_service,
            ai_service=ai_service,
            db=db
        )
        return summary
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to get family summary: {str(e)}",
            details={"family_id": family_id, "period": period, "original_error": str(e)}
        )


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(high|medium|low)$")


@router.post("/{family_id}/tasks")
async def create_family_task(
    family_id: str,
    task: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a family task for coordination"""
    try:
        family_service = container.get("family_service")
        created_task = family_service.create_family_task(
            family_id=family_id,
            creator_user_id=current_user.user_id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            db=db
        )
        return created_task
    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to create family task: {str(e)}",
            details={"family_id": family_id, "original_error": str(e)}
        )

