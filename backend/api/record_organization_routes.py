"""Explicit, atomic attribution of selected old private baby records."""

from hashlib import sha256
import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dependencies.database import get_db
from middleware.auth import get_current_user
from middleware.rate_limit import rate_limit, RATE_LIMITS
from models.database import TrackingEntryDB, RecordOrganizationDB, CareSubjectDB
from models.schemas import User
from services.auth_service import lock_session_account
from services.care_subjects import CARE_TYPES, validate_attribution

router = APIRouter(prefix="/api/record-organization", tags=["private-records"])


class RecordVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int = Field(ge=1, strict=True)
    record_key: UUID
    revision: int = Field(ge=1, strict=True)


class OrganizationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_key: UUID
    subject_id: UUID
    subject_revision: int = Field(ge=1, strict=True)
    records: list[RecordVersion] = Field(min_length=1, max_length=50)
    confirmed: StrictBool

    @model_validator(mode="after")
    def unique_records(self):
        if len({row.id for row in self.records}) != len(self.records) or len({row.record_key for row in self.records}) != len(self.records):
            raise ValueError("Select each record once")
        if not self.confirmed:
            raise ValueError("Review attribution before saving")
        return self


class UndoWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: StrictBool


def receipt(row):
    return {"request_key": row.request_key, "subject_id": row.subject_id,
            "count": len(row.records), "undone": row.undone,
            "created_at": row.created_at.isoformat() + "Z"}


@router.get("/unassigned")
def unassigned_records(limit: int = Query(50, ge=1, le=50), before_id: int | None = Query(None, ge=1),
                       kind: Literal["all", "feeding", "diaper", "sleep", "pumping"] = "all",
                       from_day: date | None = None, to_day: date | None = None,
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(TrackingEntryDB).filter(TrackingEntryDB.user_id == user.user_id,
        TrackingEntryDB.entry_type.in_(CARE_TYPES), TrackingEntryDB.subject_id.is_(None),
        TrackingEntryDB.family_shared.is_(False))
    if kind != "all":
        query = query.filter(TrackingEntryDB.entry_type == kind)
    if from_day and to_day and from_day > to_day:
        raise HTTPException(422, "Choose a valid date range")
    if (from_day and from_day.year < 2) or (to_day and to_day.year >= 9999):
        raise HTTPException(422, "Date range is outside the supported calendar")
    jst = timezone(timedelta(hours=9))
    if from_day:
        start = datetime.combine(from_day, time.min, tzinfo=jst).astimezone(timezone.utc).replace(tzinfo=None)
        query = query.filter(TrackingEntryDB.timestamp >= start)
    if to_day:
        end = datetime.combine(to_day + timedelta(days=1), time.min, tzinfo=jst).astimezone(timezone.utc).replace(tzinfo=None)
        query = query.filter(TrackingEntryDB.timestamp < end)
    total = query.count()
    if before_id is not None:
        query = query.filter(TrackingEntryDB.id < before_id)
    rows = query.order_by(TrackingEntryDB.id.desc()).limit(limit + 1).all()
    # Only the facts needed to choose attribution. Adult records and notes never enter this list.
    fields = ("id", "record_key", "revision", "entry_type", "feeding_type", "diaper_type",
              "amount_ml", "duration_minutes", "sleep_duration_minutes", "pumped_amount_ml")
    return {"total": total, "records": [{**{field: getattr(row, field) for field in fields},
            "timestamp": row.timestamp.isoformat() + "Z" if row.timestamp else None} for row in rows[:limit]],
            "next_before_id": rows[limit - 1].id if len(rows) > limit else None}


@router.get("/receipts")
def recent_receipts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(RecordOrganizationDB).filter(RecordOrganizationDB.user_id == user.user_id).order_by(
        RecordOrganizationDB.created_at.desc()).limit(10).all()
    return [receipt(row) for row in rows]


@router.get("/{request_key}")
def read_receipt(request_key: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(RecordOrganizationDB, (user.user_id, str(request_key)))
    if row is None:
        raise HTTPException(404, "Attribution operation not found")
    return receipt(row)


@router.post("")
@rate_limit(RATE_LIMITS["tracking"])
def organize_records(request: Request, body: OrganizationWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lock_session_account(db, user.user_id)
    fingerprint = sha256(json.dumps(body.model_dump(mode="json", exclude={"request_key"}), sort_keys=True).encode()).hexdigest()
    existing = db.get(RecordOrganizationDB, (user.user_id, str(body.request_key)))
    if existing:
        if existing.fingerprint != fingerprint:
            raise HTTPException(409, "This operation already has different content")
        return receipt(existing)
    validate_attribution(db, user.user_id, {"entry_type": "feeding", "subject_id": str(body.subject_id), "family_shared": False})
    subject = db.query(CareSubjectDB).populate_existing().filter(CareSubjectDB.subject_id == str(body.subject_id)).first()
    locked = db.query(CareSubjectDB).filter(CareSubjectDB.subject_id == str(body.subject_id),
        CareSubjectDB.revision == body.subject_revision).update({"revision": body.subject_revision}, synchronize_session=False)
    if subject is None or locked != 1:
        db.rollback()
        raise HTTPException(409, "Care subject changed; review again")
    versions = []
    for record in sorted(body.records, key=lambda value: value.id):
        changed = db.query(TrackingEntryDB).filter(TrackingEntryDB.id == record.id,
            TrackingEntryDB.user_id == user.user_id, TrackingEntryDB.record_key == str(record.record_key),
            TrackingEntryDB.revision == record.revision, TrackingEntryDB.subject_id.is_(None),
            TrackingEntryDB.family_shared.is_(False), TrackingEntryDB.entry_type.in_(CARE_TYPES),
        ).update({"subject_id": str(body.subject_id), "family_shared": False, "revision": record.revision + 1}, synchronize_session=False)
        if changed != 1:
            db.rollback()
            raise HTTPException(409, "A selected record changed; no attribution was saved")
        versions.append({"id": record.id, "record_key": str(record.record_key), "revision": record.revision + 1})
    row = RecordOrganizationDB(user_id=user.user_id, request_key=str(body.request_key), fingerprint=fingerprint,
        subject_id=str(body.subject_id), records=versions, undone=False)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Attribution changed; check the saved operations") from None
    return receipt(row)


@router.post("/{request_key}/undo")
def undo_organization(request_key: UUID, body: UndoWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.confirmed:
        raise HTTPException(422, "Confirm before undoing attribution")
    lock_session_account(db, user.user_id)
    row = db.query(RecordOrganizationDB).populate_existing().filter(RecordOrganizationDB.user_id == user.user_id,
        RecordOrganizationDB.request_key == str(request_key)).first()
    if row is None:
        raise HTTPException(404, "Attribution operation not found")
    if row.undone:
        return receipt(row)
    for record in sorted(row.records, key=lambda value: value["id"]):
        changed = db.query(TrackingEntryDB).filter(TrackingEntryDB.id == record["id"],
            TrackingEntryDB.user_id == user.user_id, TrackingEntryDB.record_key == record["record_key"],
            TrackingEntryDB.revision == record["revision"], TrackingEntryDB.subject_id == row.subject_id,
            TrackingEntryDB.family_shared.is_(False), TrackingEntryDB.entry_type.in_(CARE_TYPES),
        ).update({"subject_id": None, "revision": record["revision"] + 1}, synchronize_session=False)
        if changed != 1:
            db.rollback()
            raise HTTPException(409, "A record was edited, shared or removed; no records were reverted")
    row.undone = True
    db.commit()
    return receipt(row)
