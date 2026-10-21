"""Small-pilot directory. Staff privileges never grant access to family records."""

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Literal
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from config.settings import get_settings
from dependencies.database import get_db
from middleware.auth import get_current_user
from middleware.rate_limit import RATE_LIMITS, rate_limit
from models.database import PilotProfileDB, DirectoryWorkspaceDB, DirectoryHistoryDB, DirectoryReviewTaskDB
from models.schemas import User
from services.directory_review import resource_digest

router = APIRouter(prefix="/api/pilot", tags=["local-pilot"])


class LocalResource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=500)
    hours: str = Field(default="", max_length=200)
    area: str = Field(default="", max_length=100)
    audience: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=40, pattern=r"^[0-9+() #.-]*$")
    booking_url: Optional[str] = Field(default=None, max_length=500)
    cost_note: str = Field(default="", max_length=300)
    checked_on: Optional[date] = None
    resource_key: UUID = Field(default_factory=uuid4)
    category: Literal["parenting", "postpartum", "feeding"] = "parenting"
    maintainer: str = Field(default="", max_length=100)
    review_due_on: Optional[date] = None
    service_status: Literal["active", "paused"] = "active"
    pause_notice: str = Field(default="", max_length=500)
    application_steps: str = Field(default="", max_length=800)
    visiting_note: str = Field(default="", max_length=500)
    preparation: str = Field(default="", max_length=500)
    fallback_contact: str = Field(default="", max_length=500)

    @field_validator("url", "booking_url")
    @classmethod
    def public_https_link(cls, value):
        if value is None:
            return value
        parts = urlsplit(value)
        _ = parts.port  # Reject malformed port numbers before publication.
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("Use an HTTPS source URL without credentials")
        return value

    @field_validator("checked_on")
    @classmethod
    def reviewed_in_past(cls, value):
        if value and value > datetime.now(timezone(timedelta(hours=9))).date():
            raise ValueError("The checked date cannot be in the future")
        return value


class PilotProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="", max_length=100)
    municipality: str = Field(default="", max_length=100)
    contact: str = Field(default="", max_length=200)
    hours: str = Field(default="", max_length=200)
    retention_notice: str = Field(default="", max_length=1000)
    phone: str = Field(default="", max_length=40, pattern=r"^[0-9+() #.-]*$")
    email: str = Field(default="", max_length=255, pattern=r"^(?:[^@\s]+@[^@\s]+\.[^@\s]+)?$")
    ai_data_notice: str = Field(default="", max_length=1500)
    account_support_notice: str = Field(default="", max_length=1000)
    resources: List[LocalResource] = Field(default_factory=list, max_length=10)


async def require_institution_staff(current_user: User = Depends(get_current_user)):
    configured = get_settings().institution_user_ids or ""
    allowed = {value.strip() for value in configured.split(",") if value.strip()}
    if not current_user.is_active or current_user.user_id not in allowed:
        raise HTTPException(status_code=403, detail="Institution access has not been granted")
    return current_user


def read_profile(db: Session):
    record = db.get(PilotProfileDB, "local")
    settings = get_settings()
    services = []
    if settings.nsfw_detection_enabled and settings.ai_provider.lower() == "openai" and settings.openai_api_key:
        services.append({"purpose": "input_check", "provider": "OpenAI"})
    if settings.rag_enabled:
        services.append({"purpose": "reference_search", "provider": "OpenAI"})
    return {
        "profile": record.profile if record else PilotProfile().model_dump(mode="json"),
        "updated_at": record.updated_at.isoformat() + "Z" if record else None,
        "ai_provider": settings.ai_provider,
        # Configuration only; this is not a live availability check or a credential.
        "ai_services": services,
    }


@router.get("")
def public_directory(db: Session = Depends(get_db)):
    """Public, operator-maintained contact information; works without AI or login."""
    return read_profile(db)


class DirectoryWrite(BaseModel):
    profile: PilotProfile
    revision: int = Field(ge=1)


class DirectoryRestore(BaseModel):
    history_id: UUID
    revision: int = Field(ge=1)


class DraftResource(LocalResource):
    name: str = Field(default="", max_length=100)
    url: str = Field(default="", max_length=500)

    @field_validator("url", "booking_url")
    @classmethod
    def public_https_link(cls, value):
        return value if value in (None, "") else LocalResource.public_https_link(value)


class DraftProfile(PilotProfile):
    resources: List[DraftResource] = Field(default_factory=list, max_length=10)


class DirectoryDraftWrite(DirectoryWrite):
    profile: DraftProfile


class DirectoryReviewWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0, strict=True)
    workspace_revision: int = Field(ge=1, strict=True)
    decision: Literal["pending", "deferred", "checked", "edited"]
    reason: str = Field(default="", max_length=500)
    assignee: str = Field(default="", max_length=100)
    next_review_on: Optional[date] = None
    confirmed: StrictBool = False
    profile: Optional[DraftProfile] = None


def review_tasks(db, profile):
    resources = {str(item["resource_key"]): item for item in profile.get("resources", [])}
    return [{"contact_key": row.contact_key, "revision": row.revision, **row.details,
        "stale": row.contact_key not in resources or resource_digest(resources[row.contact_key]) != row.resource_digest,
        "updated_at": row.updated_at.isoformat() + "Z"}
        for row in db.query(DirectoryReviewTaskDB).all()]


def workspace(db, user_id):
    row = db.get(DirectoryWorkspaceDB, "local")
    if row is None:
        published = db.get(PilotProfileDB, "local")
        profile = PilotProfile.model_validate(published.profile if published else {}).model_dump(mode="json")
        row = DirectoryWorkspaceDB(id="local", profile=profile, revision=1, updated_by=user_id)
        db.add(row)
        if published:
            db.add(DirectoryHistoryDB(profile=profile, revision=0, published_by=published.updated_by,
                published_at=published.updated_at))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        row = db.get(DirectoryWorkspaceDB, "local")
    return row


def staff_state(db, user_id):
    row = workspace(db, user_id)
    history = db.query(DirectoryHistoryDB).order_by(DirectoryHistoryDB.revision.desc()).limit(21).all()
    summaries = []
    for index, item in enumerate(history[:20]):
        previous = history[index + 1].profile if index + 1 < len(history) else {}
        fields = [key for key in item.profile if key != "resources" and item.profile[key] != previous.get(key)]
        old = {resource.get("resource_key", str(i)): resource for i, resource in enumerate(previous.get("resources", []))}
        new = {resource.get("resource_key", str(i)): resource for i, resource in enumerate(item.profile.get("resources", []))}
        changes = {"added": [new[key].get("name", "") for key in new.keys() - old.keys()],
            "removed": [old[key].get("name", "") for key in old.keys() - new.keys()],
            "updated": [new[key].get("name", "") for key in new.keys() & old.keys() if new[key] != old[key]]}
        summaries.append({"id": item.id, "name": item.profile.get("name", ""), "fields": fields,
            "changes": changes, "published_at": item.published_at.isoformat() + "Z"})
    return {**read_profile(db), "workspace": {"profile": row.profile, "revision": row.revision,
        "updated_at": row.updated_at.isoformat() + "Z"},
        "history": summaries, "review_tasks": review_tasks(db, row.profile)}


def replace_draft(db, profile, revision, user_id):
    workspace(db, user_id)
    changed = db.query(DirectoryWorkspaceDB).filter(DirectoryWorkspaceDB.id == "local",
        DirectoryWorkspaceDB.revision == revision,
    ).update({"profile": profile, "revision": revision + 1, "updated_by": user_id,
        "updated_at": datetime.utcnow()}, synchronize_session=False)
    if changed != 1:
        db.rollback()
        raise HTTPException(409, "The institution draft changed on another screen")


@router.get("/organization")
def staff_directory(current_user: User = Depends(require_institution_staff), db: Session = Depends(get_db)):
    return staff_state(db, current_user.user_id)


@router.post("/organization/draft")
@rate_limit(RATE_LIMITS["default"])
def save_directory_draft(request: Request, body: DirectoryDraftWrite,
    current_user: User = Depends(require_institution_staff), db: Session = Depends(get_db)):
    replace_draft(db, body.profile.model_dump(mode="json"), body.revision, current_user.user_id)
    db.commit()
    return staff_state(db, current_user.user_id)


@router.post("/organization/review-tasks/{contact_key}")
@rate_limit(RATE_LIMITS["default"])
def save_review_task(request: Request, contact_key: UUID, body: DirectoryReviewWrite,
                     current_user: User = Depends(require_institution_staff), db: Session = Depends(get_db)):
    row = workspace(db, current_user.user_id)
    locked = db.query(DirectoryWorkspaceDB).filter(DirectoryWorkspaceDB.id == "local",
        DirectoryWorkspaceDB.revision == body.workspace_revision).update(
        {"revision": DirectoryWorkspaceDB.revision}, synchronize_session=False)
    if locked != 1:
        db.rollback()
        raise HTTPException(409, "The institution draft changed; review again")
    today = datetime.now(timezone(timedelta(hours=9))).date()
    if body.decision != "pending" and (body.next_review_on is None or body.next_review_on <= today):
        raise HTTPException(422, "Choose a next review date after today")
    if body.decision == "deferred" and not body.reason.strip():
        raise HTTPException(422, "Record why this review was deferred")
    if body.decision in ("checked", "edited") and (not body.confirmed or body.profile is None):
        raise HTTPException(422, "Confirm the reviewed draft before recording completion")
    profile = body.profile.model_dump(mode="json") if body.profile else row.profile
    resource = next((item for item in profile.get("resources", []) if str(item["resource_key"]) == str(contact_key)), None)
    if resource is None:
        raise HTTPException(404, "Contact is no longer in the working draft")
    if body.profile is not None:
        replace_draft(db, profile, body.workspace_revision, current_user.user_id)
    details = {"decision": body.decision, "reason": body.reason.strip(), "assignee": body.assignee.strip(),
        "next_review_on": body.next_review_on.isoformat() if body.next_review_on else None}
    values = {"details": details, "resource_digest": resource_digest(resource), "revision": body.revision + 1,
        "updated_by": current_user.user_id, "updated_at": datetime.utcnow()}
    try:
        if body.revision == 0:
            db.add(DirectoryReviewTaskDB(contact_key=str(contact_key), **values))
        else:
            changed = db.query(DirectoryReviewTaskDB).filter(DirectoryReviewTaskDB.contact_key == str(contact_key),
                DirectoryReviewTaskDB.revision == body.revision).update(values, synchronize_session=False)
            if changed != 1:
                db.rollback()
                raise HTTPException(409, "The internal review task changed; reload before saving")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "The internal review task changed; reload before saving") from None
    return staff_state(db, current_user.user_id)


@router.post("/organization/restore")
@rate_limit(RATE_LIMITS["default"])
def restore_directory(request: Request, body: DirectoryRestore,
    current_user: User = Depends(require_institution_staff), db: Session = Depends(get_db)):
    snapshot = db.get(DirectoryHistoryDB, str(body.history_id))
    if snapshot is None:
        raise HTTPException(404, "Published version not found")
    profile = PilotProfile.model_validate(snapshot.profile).model_dump(mode="json")
    replace_draft(db, profile, body.revision, current_user.user_id)
    db.commit()
    return staff_state(db, current_user.user_id)


@router.post("/organization")
@rate_limit(RATE_LIMITS["default"])
def save_directory(
    request: Request,
    body: DirectoryWrite,
    current_user: User = Depends(require_institution_staff),
    db: Session = Depends(get_db),
):
    if not body.profile.name.strip() or any(not resource.name.strip() for resource in body.profile.resources):
        raise HTTPException(422, "Publication requires institution and contact names")
    profile = body.profile.model_dump(mode="json")
    replace_draft(db, profile, body.revision, current_user.user_id)
    record = db.get(PilotProfileDB, "local")
    if record is None:
        record = PilotProfileDB(id="local")
        db.add(record)
    record.profile = profile
    record.updated_by = current_user.user_id
    record.updated_at = datetime.utcnow()
    db.add(DirectoryHistoryDB(profile=profile, revision=body.revision + 1, published_by=current_user.user_id))
    db.commit()
    return staff_state(db, current_user.user_id)
