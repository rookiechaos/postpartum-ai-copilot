"""
Tracking Routes - API endpoints for tracking data management
"""

from fastapi import APIRouter, Depends, Query, Request
from typing import List, Dict, Any
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session

from dependencies.database import get_db
from middleware.auth import get_current_user
from middleware.authorization import check_user_authorization
from middleware.rate_limit import rate_limit, RATE_LIMITS
from models.schemas import User, TrackingEntry, TrackingEntryCreate, TrackingEntryUpdate, TrackingSummary, EmotionalCheckIn
from models.database import TrackingEntryDB, TrackingWriteDB
from services.task_queue import TaskPriority
from services.ai_data_scope import profile_for_ai, records_for_ai
from services.care_subjects import accessible_subjects
from exceptions import (
    PostpartumException,
    DatabaseError,
    AIServiceError,
    TaskQueueError,
)
from config.settings import get_settings
from dependencies.container import get_container
from fastapi import HTTPException

router = APIRouter(tags=["tracking"])

container = get_container()
settings = get_settings()


@router.get("/api/tracking/operations/{request_key}")
@rate_limit(RATE_LIMITS["tracking"])
def read_tracking_operation(request: Request, request_key: UUID,
                            current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    receipt = db.get(TrackingWriteDB, (current_user.user_id, str(request_key)))
    if receipt is None:
        return {"state": "not_found", "record": None}
    row = db.query(TrackingEntryDB).filter(TrackingEntryDB.record_key == receipt.record_key,
        TrackingEntryDB.user_id == current_user.user_id).first()
    if row is None:
        return {"state": "deleted", "record": None}
    return {"state": "saved", "record": container.get("tracking_service")._owned_entries([row], db, current_user.user_id)[0]}


@router.get("/api/tracking/entries/{entry_id}", response_model=TrackingEntry)
@rate_limit(RATE_LIMITS["tracking"])
def read_tracking_entry(request: Request, entry_id: int, record_key: UUID,
                        current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(TrackingEntryDB).filter(TrackingEntryDB.id == entry_id,
        TrackingEntryDB.record_key == str(record_key), TrackingEntryDB.user_id == current_user.user_id).first()
    if row is None:
        raise HTTPException(404, "Tracking entry not found")
    return container.get("tracking_service")._owned_entries([row], db, current_user.user_id)[0]


@router.post("/api/tracking/duplicate-check")
@rate_limit(RATE_LIMITS["tracking"])
def check_family_duplicates(request: Request, entry: TrackingEntryCreate,
                            current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from datetime import timezone
    subject = next((item for item in accessible_subjects(db, current_user.user_id)
        if item["subject_id"] == str(entry.subject_id)), None)
    if not subject or not subject["family_id"] or entry.entry_type.value not in ("feeding", "diaper", "sleep", "pumping"):
        return {"matches": []}
    if entry.timestamp is None:
        raise HTTPException(422, "Choose an event time before checking")
    timestamp = entry.timestamp.replace(tzinfo=timezone.utc) if entry.timestamp.tzinfo is None else entry.timestamp
    records = container.get("family_service").get_shared_tracking_data(subject["family_id"], current_user.user_id, days=7, db=db)
    matches = []
    for record in records:
        if record["recorded_by"] == current_user.user_id or record["entry_type"] != entry.entry_type.value:
            continue
        date = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
        date = date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date
        if abs((date - timestamp).total_seconds()) > 300:
            continue
        if any(getattr(entry, key) is not None and record.get(key) != getattr(entry, key).value for key in ("feeding_type", "diaper_type")):
            continue
        matches.append({key: record.get(key) for key in ("record_key", "timestamp", "entry_type", "recorder_label", "feeding_type", "diaper_type", "amount_ml", "duration_minutes", "sleep_duration_minutes")})
    return {"matches": matches[:3]}


@router.post("/api/tracking/entries/{entry_id}/update", response_model=TrackingEntry)
@rate_limit(RATE_LIMITS["tracking"])
async def update_tracking_entry(
    request: Request,
    entry_id: int,
    entry: TrackingEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if entry.user_id and entry.user_id != current_user.user_id:
        check_user_authorization(current_user, entry.user_id, "tracking entry")
    return await container.get("tracking_service").update_entry(entry_id, current_user.user_id, entry, db)


@router.delete("/api/tracking/entries/{entry_id}")
@rate_limit(RATE_LIMITS["tracking"])
async def delete_tracking_entry(
    request: Request,
    entry_id: int,
    record_key: UUID,
    revision: int = Query(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await container.get("tracking_service").delete_entry(entry_id, current_user.user_id, str(record_key), revision, db)


@router.post("/api/tracking", response_model=Dict[str, Any])
@rate_limit(RATE_LIMITS["tracking"])
async def add_tracking_entry(
    request: Request,
    entry: TrackingEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Save a private care record without external AI processing.

    Requires authentication. user_id is always taken from the JWT token.
    Request validation is local; AI analysis is a separate user action.
    """
    if entry.user_id and entry.user_id != current_user.user_id:
        check_user_authorization(current_user, entry.user_id, "tracking entry")

    user_id = current_user.user_id
    entry_data = entry.model_copy(update={"user_id": user_id})
    tracking_service = container.get("tracking_service")

    try:
        result = await tracking_service.add_entry(entry_data, db)
        return result
    except PostpartumException:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to add tracking entry: {str(e)}")


@router.get("/api/tracking/{user_id}", response_model=List[TrackingEntry])
@rate_limit(RATE_LIMITS["tracking"])
async def get_tracking_entries(
    request: Request,
    user_id: str,
    days: int = Query(7, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get tracking entries for a user"""
    check_user_authorization(current_user, user_id, "tracking entries")
    tracking_service = container.get("tracking_service")

    try:
        entries = await tracking_service.get_entries(user_id, db, days=days)
        return entries
    except PostpartumException:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to get tracking entries: {str(e)}")


@router.get("/api/tracking/{user_id}/recent", response_model=List[TrackingEntry])
async def get_latest_tracking(user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_user_authorization(current_user, user_id, "tracking entries")
    return await container.get("tracking_service").get_latest_entries(user_id, db)


@router.get("/api/tracking/{user_id}/summary", response_model=TrackingSummary)
@rate_limit(RATE_LIMITS["default"])
async def get_tracking_summary(
    request: Request,
    user_id: str,
    days: int = Query(7, ge=1, le=90),
    include_parent: bool = False,
    include_notes: bool = False,
    include_profile: bool = False,
    language: str = Query("ja", pattern="^(ja|en)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-generated summary and patterns from tracking data

    Now uses async task queue for processing.
    Returns task_id, client should poll /api/tasks/{task_id}
    """
    check_user_authorization(current_user, user_id, "user's tracking data")
    tracking_service = container.get("tracking_service")
    ai_service = container.get("ai_service")
    task_queue = container.get("task_queue")

    async_mode = settings.async_mode

    if not async_mode:
        try:
            entries = await tracking_service.get_entries(user_id, db, days=days)
            entries = records_for_ai(entries, include_parent, include_notes)
            context = profile_for_ai(await tracking_service.get_user_context(user_id, db), include_profile)

            summary = await ai_service.analyze_tracking(
                entries=entries,
                context=context,
                language=language
            )
            if summary.get("error"):
                raise AIServiceError("AI analysis unavailable")

            return TrackingSummary(
                patterns=summary.get("patterns", []),
                insights=summary.get("insights", []),
                recommendations=summary.get("recommendations", []),
                normalcy_checks=summary.get("normalcy_checks", []),
                timestamp=datetime.now().isoformat()
            )
        except PostpartumException:
            raise
        except Exception as e:
            raise AIServiceError(f"Failed to analyze tracking data: {str(e)}")

    try:
        task_data = {
            "user_id": user_id,
            "days": days, "language": language, "include_parent": include_parent,
            "include_notes": include_notes, "include_profile": include_profile,
        }

        task_id = task_queue.create_task(
            task_type="tracking_analysis",
            task_data=task_data,
            user_id=user_id,
            db=db,
            priority=TaskPriority.LOW,
            timeout=600
        )

        raise HTTPException(
            status_code=202,
            detail={
                "message": "Task created, please poll /api/tasks/{task_id} for result",
                "task_id": task_id,
                "status": "pending"
            }
        )
    except HTTPException:
        raise
    except PostpartumException:
        raise
    except Exception as e:
        raise TaskQueueError(f"Failed to create tracking analysis task: {str(e)}")


@router.get("/api/tracking/{user_id}/daily-summary")
@rate_limit(RATE_LIMITS["default"])
async def get_daily_summary(
    request: Request,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Read local daily statistics; never perform external AI processing."""
    check_user_authorization(current_user, user_id, "tracking summary")
    tracking_service = container.get("tracking_service")
    try:
        summary = await tracking_service.generate_daily_summary(
            user_id=user_id,
            db=db,
        )
        return summary
    except PostpartumException:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to get daily summary: {str(e)}")


@router.get("/api/tracking/{user_id}/weekly-summary")
@rate_limit(RATE_LIMITS["default"])
async def get_weekly_summary(
    request: Request,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Read local weekly statistics; AI analysis is a separate opt-in request."""
    check_user_authorization(current_user, user_id, "tracking summary")
    tracking_service = container.get("tracking_service")
    try:
        summary = await tracking_service.generate_weekly_summary(
            user_id=user_id,
            db=db,
        )
        return summary
    except PostpartumException:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to get weekly summary: {str(e)}")


@router.post("/api/emotional-checkin")
@rate_limit(RATE_LIMITS["tracking"])
async def emotional_checkin(
    request: Request,
    checkin: EmotionalCheckIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Daily emotional check-in with risk detection.

    Requires authentication. user_id is always taken from the JWT token.
    """
    if checkin.user_id and checkin.user_id != current_user.user_id:
        check_user_authorization(current_user, checkin.user_id, "emotional check-in")

    user_id = current_user.user_id
    tracking_service = container.get("tracking_service")
    ai_service = container.get("ai_service")

    try:
        recent_moods = await tracking_service.get_mood_history(user_id, db, days=7) if checkin.include_history else []

        analysis = await ai_service.analyze_emotional_state(
            current_checkin={**checkin.model_dump(mode="json"), "user_id": user_id},
            mood_history=recent_moods
        )

        return {
            "assessment": analysis.get("assessment", ""),
            "risk_level": analysis.get("risk_level", "unknown"),
            "analysis_available": analysis.get("analysis_available", False),
            "error": analysis.get("error"),
            "suggestions": analysis.get("suggestions", []),
            "escalation_needed": analysis.get("escalation_needed"),
            "resources": analysis.get("resources", []),
            "timestamp": datetime.now().isoformat()
        }
    except PostpartumException:
        raise
    except Exception as e:
        raise AIServiceError(f"Failed to process emotional check-in: {str(e)}")
