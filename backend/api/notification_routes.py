"""
Notification Routes - API endpoints for notifications
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from dependencies.container import get_container
from exceptions import ConflictError, DatabaseError, ValidationError

router = APIRouter()
container = get_container()


class NotificationCreate(BaseModel):
    notification_type: str = Field(..., description="Type: feeding, sleep, mood_check, medical_appointment, custom")
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    scheduled_time: datetime
    is_recurring: bool = Field(default=False)
    recurrence_pattern: Optional[str] = Field(default=None, description="daily, weekly, or custom")
    action_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("scheduled_time")
    @classmethod
    def utc_schedule(cls, value):
        # Legacy timestamps without a zone are UTC; explicit offsets are normalized.
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


class NotificationResponse(BaseModel):
    id: int
    user_id: str
    notification_type: str
    title: str
    message: str
    scheduled_time: str
    is_recurring: bool
    recurrence_pattern: Optional[str]
    is_enabled: bool
    is_sent: bool
    sent_at: Optional[str]
    action_url: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str


@router.post("/", response_model=NotificationResponse)
async def create_notification(
    notification: NotificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new notification/reminder"""
    notification_service = container.get("notification_service")
    
    try:
        created = notification_service.create_notification(
            user_id=current_user.user_id,
            notification_type=notification.notification_type,
            title=notification.title,
            message=notification.message,
            scheduled_time=notification.scheduled_time,
            db=db,
            is_recurring=notification.is_recurring,
            recurrence_pattern=notification.recurrence_pattern,
            action_url=notification.action_url,
            metadata=notification.metadata
        )
        return NotificationResponse(**created)
    except (ValidationError, DatabaseError):
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to create notification: {str(e)}",
            details={"user_id": current_user.user_id, "notification_type": notification.notification_type, "original_error": str(e)}
        )


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    include_sent: bool = False,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's notifications"""
    notification_service = container.get("notification_service")
    notifications = notification_service.get_user_notifications(
        user_id=current_user.user_id,
        db=db,
        include_sent=include_sent,
        limit=limit
    )
    return [NotificationResponse(**n) for n in notifications]


@router.get("/due")
async def due_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Read the account's due IDs without changing delivery state or exposing care text."""
    rows = container.get("notification_service").get_pending_notifications(db, user_id=current_user.user_id, limit=25)
    return [{"id": row["id"]} for row in rows]


@router.post("/{notification_id}/acknowledge")
async def acknowledge_notification(notification_id: int, current_user: User = Depends(get_current_user),
                                   db: Session = Depends(get_db)):
    """The browser reports acceptance; ownership and due/enabled state are checked server-side."""
    accepted = container.get("notification_service").mark_notification_sent(
        notification_id, db, user_id=current_user.user_id)
    if not accepted:
        raise HTTPException(409, "Reminder is no longer available for delivery")
    return {"acknowledged": True}


@router.post("/smart/feeding", response_model=NotificationResponse)
async def create_smart_feeding_reminder(
    based_on_history: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a smart feeding reminder based on user's history"""
    notification_service = container.get("notification_service")
    notification = notification_service.create_smart_feeding_reminder(
        user_id=current_user.user_id,
        db=db,
        based_on_history=based_on_history
    )
    
    if not notification:
        raise DatabaseError(
            "Failed to create feeding reminder",
            details={"user_id": current_user.user_id, "based_on_history": based_on_history}
        )
    
    return NotificationResponse(**notification)


@router.post("/smart/mood-check", response_model=NotificationResponse)
async def create_mood_checkin_reminder(
    time_of_day: str = "evening",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a mood check-in reminder"""
    notification_service = container.get("notification_service")
    notification = notification_service.create_mood_checkin_reminder(
        user_id=current_user.user_id,
        db=db,
        time_of_day=time_of_day
    )
    
    if not notification:
        raise DatabaseError(
            "Failed to create mood check-in reminder",
            details={"user_id": current_user.user_id, "time_of_day": time_of_day}
        )
    
    return NotificationResponse(**notification)


@router.delete("/{notification_id}")
async def disable_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable a notification"""
    notification_service = container.get("notification_service")
    
    success = notification_service.disable_notification(
        notification_id=notification_id,
        user_id=current_user.user_id,
        db=db
    )
    
    if not success:
        raise ConflictError("Reminder changed; refresh the schedule before stopping it")
    
    return {"message": "Notification disabled"}

