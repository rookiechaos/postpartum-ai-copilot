"""Opt-in, account-bound drafts. No browser health-data storage or external processing."""

from datetime import datetime, timedelta
import json
from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StrictBool, field_validator
from sqlalchemy import DateTime, JSON, insert, literal, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dependencies.database import get_db
from middleware.auth import get_current_user
from models.database import DraftPreferenceDB, UserDraftDB
from models.schemas import User

router = APIRouter(prefix="/api/drafts", tags=["private-drafts"])
DraftKind = Literal["record", "quick", "chat", "sheet"]


class DraftSettings(BaseModel):
    enabled: StrictBool
    revision: int = Field(ge=0)


class DraftWrite(BaseModel):
    content: Dict[str, Any]
    revision: int = Field(ge=0)
    preference_revision: int = Field(ge=1)

    @field_validator("content")
    @classmethod
    def bounded_content(cls, value):
        if len(json.dumps(value, ensure_ascii=False)) > 32000:
            raise ValueError("Draft is too long")
        return value


def preference(db, user_id):
    row = db.get(DraftPreferenceDB, user_id)
    return {"enabled": bool(row and row.enabled), "revision": row.revision if row else 0}


@router.get("/settings")
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return preference(db, user.user_id)


@router.post("/settings")
def save_settings(body: DraftSettings, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.get(DraftPreferenceDB, user.user_id)
    if existing is None:
        if body.revision != 0:
            raise HTTPException(409, "Draft preference changed")
        db.add(DraftPreferenceDB(user_id=user.user_id, enabled=body.enabled, revision=1))
    else:
        changed = db.query(DraftPreferenceDB).filter(
            DraftPreferenceDB.user_id == user.user_id, DraftPreferenceDB.revision == body.revision,
        ).update({"enabled": body.enabled, "revision": body.revision + 1}, synchronize_session=False)
        if changed != 1:
            db.rollback()
            raise HTTPException(409, "Draft preference changed")
    # Disabling, and re-enabling after a disabled state, cannot revive old drafts.
    if not body.enabled or existing is None or not existing.enabled:
        db.query(UserDraftDB).filter(UserDraftDB.user_id == user.user_id).delete(synchronize_session=False)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Draft preference changed") from None
    return preference(db, user.user_id)


@router.get("/{kind}")
def get_draft(kind: DraftKind, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = preference(db, user.user_id)
    row = db.get(UserDraftDB, (user.user_id, kind)) if settings["enabled"] else None
    if row and row.updated_at < datetime.utcnow() - timedelta(days=7):
        changed = db.query(UserDraftDB).filter(UserDraftDB.user_id == user.user_id,
            UserDraftDB.kind == kind, UserDraftDB.revision == row.revision,
            UserDraftDB.updated_at < datetime.utcnow() - timedelta(days=7),
        ).update({"content": {}, "cleared": True, "revision": row.revision + 1,
            "updated_at": datetime.utcnow()}, synchronize_session=False)
        db.commit()
        row = db.query(UserDraftDB).filter(UserDraftDB.user_id == user.user_id,
            UserDraftDB.kind == kind).populate_existing().first()
    return {**settings, "draft_revision": row.revision if row else 0,
        "draft": {"content": row.content, "revision": row.revision,
        "updated_at": row.updated_at.isoformat() + "Z"} if row and not row.cleared else None}


@router.post("/{kind}")
def save_draft(kind: DraftKind, body: DraftWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    locked = db.query(DraftPreferenceDB).filter(DraftPreferenceDB.user_id == user.user_id,
        DraftPreferenceDB.enabled.is_(True), DraftPreferenceDB.revision == body.preference_revision,
    ).with_for_update().first()
    if locked is None:
        db.rollback()
        raise HTTPException(409, "Draft recovery preference changed")
    allowed = select(DraftPreferenceDB.user_id).where(
        DraftPreferenceDB.user_id == user.user_id, DraftPreferenceDB.enabled.is_(True),
        DraftPreferenceDB.revision == body.preference_revision,
    ).exists()
    now = datetime.utcnow()
    if body.revision == 0:
        # The preference predicate is checked in the write itself, including on SQLite.
        try:
            changed = db.execute(insert(UserDraftDB).from_select(
                ["user_id", "kind", "content", "revision", "updated_at", "cleared"],
                select(literal(user.user_id), literal(kind), literal(body.content, type_=JSON),
                    literal(1), literal(now, type_=DateTime), literal(False)).where(allowed),
            ))
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Draft changed on another screen") from None
        count = changed.rowcount
    else:
        count = db.query(UserDraftDB).filter(UserDraftDB.user_id == user.user_id,
            UserDraftDB.kind == kind, UserDraftDB.revision == body.revision, allowed,
        ).update({"content": body.content, "cleared": False,
            "revision": body.revision + 1, "updated_at": now}, synchronize_session=False)
    if count != 1:
        db.rollback()
        raise HTTPException(409, "Draft or recovery preference changed")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Draft changed on another screen") from None
    return {"revision": body.revision + 1, "updated_at": now.isoformat() + "Z"}


@router.delete("/{kind}")
def delete_draft(kind: DraftKind, revision: int, preference_revision: int,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(UserDraftDB, (user.user_id, kind))
    if row is not None:
        locked = db.query(DraftPreferenceDB).filter(DraftPreferenceDB.user_id == user.user_id,
            DraftPreferenceDB.enabled.is_(True), DraftPreferenceDB.revision == preference_revision,
        ).with_for_update().first()
        if locked is None:
            db.rollback()
            raise HTTPException(409, "Draft recovery preference changed")
        allowed = select(DraftPreferenceDB.user_id).where(DraftPreferenceDB.user_id == user.user_id,
            DraftPreferenceDB.enabled.is_(True), DraftPreferenceDB.revision == preference_revision).exists()
        count = db.query(UserDraftDB).filter(UserDraftDB.user_id == user.user_id,
            UserDraftDB.kind == kind, UserDraftDB.revision == revision, allowed,
        ).update({"content": {}, "cleared": True, "revision": revision + 1,
            "updated_at": datetime.utcnow()}, synchronize_session=False)
        if count != 1:
            db.rollback()
            raise HTTPException(409, "Draft changed on another screen")
        db.commit()
    return {"deleted": True, "revision": revision + 1 if row is not None else 0}
