"""Private, explicitly saved consultation packets with revision-guarded writes."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from dependencies.database import get_db
from middleware.auth import get_current_user
from models.database import ConsultationDB, PilotProfileDB, SupportJourneyDB
from models.schemas import User
from services.auth_service import lock_session_account
from services.care_subjects import accessible_subjects

router = APIRouter(prefix="/api/consultations", tags=["private-consultations"])


class ConsultationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0, strict=True)
    request_key: UUID
    contact_key: Optional[str] = Field(default=None, min_length=1, max_length=100)
    subject_id: Optional[UUID] = None
    appointment_at: Optional[datetime] = None
    questions: list[str] = Field(min_length=3, max_length=3)
    days: int = Field(ge=3, le=30, strict=True)
    include_parent: StrictBool = False
    include_notes: StrictBool = False
    include_details: StrictBool = False
    text: str = Field(min_length=1, max_length=8000)
    confirmed: StrictBool

    @field_validator("questions")
    @classmethod
    def bounded_questions(cls, value):
        if any(len(question) > 250 for question in value):
            raise ValueError("Keep each question within 250 characters")
        return value

    @field_validator("days")
    @classmethod
    def allowed_period(cls, value):
        if value not in (3, 7, 14, 30):
            raise ValueError("Choose an available time range")
        return value

    @field_validator("appointment_at")
    @classmethod
    def zoned_time(cls, value):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("Include the appointment time zone")
            return value.astimezone(timezone.utc)
        return value


def owned_packet(db, consultation_id, user_id):
    row = db.query(ConsultationDB).populate_existing().filter(ConsultationDB.consultation_id == str(consultation_id),
        ConsultationDB.user_id == user_id).first()
    if row is None:
        raise HTTPException(404, "Consultation not found")
    return row


def packet_view(row, detail=True):
    base = {"consultation_id": row.consultation_id, "revision": row.revision, "cleared": row.cleared,
        "updated_at": row.updated_at.isoformat() + "Z", "last_write_key": row.last_write_key}
    if row.cleared:
        return base
    return {**base, "content": row.content if detail else {key: row.content.get(key)
        for key in ("contact_key", "contact_name", "subject_id", "subject_name", "appointment_at")}}


@router.get("")
def list_consultations(limit: int = Query(20, ge=1, le=50), before_id: Optional[str] = Query(None, max_length=36),
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Creation order is stable across edits; the cursor is resolved only within this account.
    query = db.query(ConsultationDB).filter(ConsultationDB.user_id == user.user_id, ConsultationDB.cleared.is_(False))
    if before_id:
        cursor = owned_packet(db, before_id, user.user_id)
        query = query.filter(or_(ConsultationDB.created_at < cursor.created_at,
            and_(ConsultationDB.created_at == cursor.created_at, ConsultationDB.consultation_id < cursor.consultation_id)))
    rows = query.order_by(ConsultationDB.created_at.desc(), ConsultationDB.consultation_id.desc()).limit(limit + 1).all()
    return {"items": [packet_view(row, False) for row in rows[:limit]],
        "next_before_id": rows[limit - 1].consultation_id if len(rows) > limit else None}


@router.get("/{consultation_id}")
def get_consultation(consultation_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return packet_view(owned_packet(db, consultation_id, user.user_id))


@router.post("/{consultation_id}")
def save_consultation(consultation_id: UUID, body: ConsultationWrite,
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.confirmed or not body.text.strip() or (body.include_notes and not body.include_details):
        raise HTTPException(422, "Review the private consultation material before saving")
    lock_session_account(db, user.user_id)
    row = db.query(ConsultationDB).populate_existing().filter(ConsultationDB.consultation_id == str(consultation_id)).first()
    if row and row.user_id != user.user_id:
        raise HTTPException(404, "Consultation not found")
    content = body.model_dump(mode="json", exclude={"revision", "request_key", "confirmed"})
    fingerprint = sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    if row and row.last_write_key == str(body.request_key):
        if row.fingerprint != fingerprint or row.cleared:
            raise HTTPException(409, "This save is already finalized with different content")
        return packet_view(row)
    if (row.revision if row else 0) != body.revision or (row and row.cleared):
        raise HTTPException(409, "Consultation changed; reload before saving")
    previous = row.content if row else {}
    if body.subject_id:
        subject = next((item for item in accessible_subjects(db, user.user_id) if item["subject_id"] == str(body.subject_id)), None)
        if not subject and previous.get("subject_id") != str(body.subject_id):
            raise HTTPException(404, "Care subject is unavailable")
        content["subject_name"] = previous.get("subject_name", "") if previous.get("subject_id") == str(body.subject_id) else subject["nickname"]
    else:
        content["subject_name"] = ""
    if body.contact_key and previous.get("contact_key") == body.contact_key:
        content["contact_name"] = previous.get("contact_name", "")
    elif body.contact_key:
        profile_row = db.get(PilotProfileDB, "local")
        profile = profile_row.profile if profile_row else {}
        contact = profile if body.contact_key == "organization" else next((item for item in profile.get("resources", []) if item.get("resource_key") == body.contact_key), None)
        journey = db.get(SupportJourneyDB, (user.user_id, body.contact_key))
        name = (contact or {}).get("name") or (journey.contact_name if journey and not journey.cleared else "")
        if not name:
            raise HTTPException(404, "Contact is unavailable")
        content["contact_name"] = name
    else:
        content["contact_name"] = ""
    now = datetime.utcnow()
    if row:
        row.content = content; row.revision += 1; row.updated_at = now
        row.last_write_key = str(body.request_key); row.fingerprint = fingerprint
    else:
        row = ConsultationDB(consultation_id=str(consultation_id), user_id=user.user_id, content=content,
            revision=1, last_write_key=str(body.request_key), fingerprint=fingerprint, cleared=False)
        db.add(row)
    db.commit()
    return packet_view(row)


@router.delete("/{consultation_id}")
def clear_consultation(consultation_id: UUID, revision: int = Query(..., ge=1),
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lock_session_account(db, user.user_id)
    row = owned_packet(db, consultation_id, user.user_id)
    if row.cleared:
        return packet_view(row)
    if row.revision != revision:
        raise HTTPException(409, "Consultation changed; reload before deleting")
    row.content = {}; row.fingerprint = ""; row.cleared = True; row.revision += 1; row.updated_at = datetime.utcnow()
    db.commit()
    return packet_view(row)
