"""
Family Routes - API endpoints for family sharing
"""

from fastapi import APIRouter, Depends, status, Query
from pydantic import BaseModel, Field, StrictBool
from typing import Optional, List
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from models.database import FamilyDB, FamilyMemberDB
from dependencies.container import get_container
from middleware.authorization import check_user_authorization
from exceptions import DatabaseError, NotFoundError, ValidationError, ConflictError
from services.family_service import FAMILY_SHARED_DAYS

router = APIRouter()
container = get_container()


class FamilyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class FamilyInvite(BaseModel):
    invitee_user_id: str = Field(min_length=1, max_length=100)
    role: str = Field(default="member", pattern="^(admin|member|viewer)$")


class SharingPreferences(BaseModel):
    revision: int = Field(ge=1, strict=True)
    share_tracking: Optional[StrictBool] = None
    share_baby: Optional[StrictBool] = None
    share_parent: StrictBool = False
    share_notes: StrictBool = False
    display_label: str = Field(default="", max_length=40)


class FamilyResponse(BaseModel):
    family_id: str
    name: str
    created_by: str
    created_at: str
    updated_at: str


@router.get("/invitations")
def get_invitations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(FamilyMemberDB, FamilyDB).join(FamilyDB,
        FamilyMemberDB.family_id == FamilyDB.family_id).filter(
        FamilyMemberDB.user_id == current_user.user_id, FamilyMemberDB.status == "pending").all()
    return [{"family_id": family.family_id, "name": family.name} for member, family in rows]


@router.post("/{family_id}/decline")
def decline_invitation(family_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(FamilyMemberDB).filter(FamilyMemberDB.family_id == family_id,
        FamilyMemberDB.user_id == current_user.user_id, FamilyMemberDB.status == "pending").first()
    if row is None:
        raise NotFoundError("Invitation not found")
    changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.id == row.id,
        FamilyMemberDB.status == "pending", FamilyMemberDB.revision == row.revision,
    ).update({"status": "inactive", "permissions": {},
        "revision": row.revision + 1}, synchronize_session=False)
    if changed != 1:
        db.rollback()
        raise NotFoundError("Invitation is no longer available")
    db.commit()
    return {"declined": True}


@router.post("/{family_id}/leave")
def leave_family(family_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = db.query(FamilyDB).filter(FamilyDB.family_id == family_id).first()
    if family is None:
        raise NotFoundError("Family not found")
    if family.created_by == current_user.user_id:
        raise ValidationError("The creator must revoke other memberships instead of leaving")
    changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.family_id == family_id,
        FamilyMemberDB.user_id == current_user.user_id, FamilyMemberDB.status == "active",
    ).update({"status": "inactive", "permissions": {},
        "revision": FamilyMemberDB.revision + 1}, synchronize_session=False)
    if changed != 1:
        db.rollback()
        raise NotFoundError("Membership not found")
    db.commit()
    return {"left": True}


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
    days: int = Query(FAMILY_SHARED_DAYS, ge=1, le=FAMILY_SHARED_DAYS),
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


@router.post("/{family_id}/sharing")
async def set_sharing_preferences(
    family_id: str,
    preferences: SharingPreferences,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set only the authenticated member's own sharing preference."""
    return container.get("family_service").share_tracking_data(
        family_id, current_user.user_id, preferences.share_tracking, db,
        share_baby=preferences.share_baby, share_parent=preferences.share_parent,
        share_notes=preferences.share_notes, display_label=preferences.display_label,
        expected_revision=preferences.revision,
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
    except (ValidationError, NotFoundError, ConflictError):
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
        family_service = container.get("family_service")
        
        summary = await family_service.generate_family_summary(
            family_id=family_id,
            user_id=current_user.user_id,
            period=period,
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

