"""Explicit household handovers, single-use invitations and private help progress."""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dependencies.container import get_container
from dependencies.database import get_db
from middleware.auth import get_current_user
from middleware.rate_limit import RATE_LIMITS, rate_limit
from models.database import (FamilyDB, FamilyMemberDB, FamilyHandoverDB, FamilyInviteLinkDB,
                             SupportJourneyDB, PilotProfileDB)
from models.schemas import User

router = APIRouter(tags=["care-flows"])


def stamp(value):
    return value.isoformat() + "Z" if value else None


def member_of(db, family_id, user_id, *, write=False):
    member = db.query(FamilyMemberDB).filter(FamilyMemberDB.family_id == family_id,
        FamilyMemberDB.user_id == user_id, FamilyMemberDB.status == "active").first()
    if member is None:
        raise HTTPException(403, "Family access is unavailable")
    if write:
        # Also acquires a SQLite write lock, serializing revocation and this write.
        changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.id == member.id,
            FamilyMemberDB.status == "active", FamilyMemberDB.revision == member.revision,
        ).update({"revision": member.revision}, synchronize_session=False)
        if changed != 1:
            db.rollback()
            raise HTTPException(409, "Family access changed")
    return member


@router.get("/api/families/{family_id}/overview")
def family_overview(family_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    me = member_of(db, family_id, user.user_id)
    service = get_container().get("family_service")
    records = service.get_shared_tracking_data(family_id, user.user_id, days=7, db=db)
    categories = ("feeding", "diaper", "sleep", "pumping")
    people = db.query(FamilyMemberDB).filter(FamilyMemberDB.family_id == family_id,
        FamilyMemberDB.status == "active").order_by(FamilyMemberDB.id).all()
    labels = {person.user_id: (person.permissions or {}).get("display_label", "") for person in people}
    numbers = {person.user_id: index + 1 for index, person in enumerate(people)}
    # No parent records or free-text tracking notes enter the home overview.
    allowed = ("record_key", "timestamp", "entry_type", "recorded_by", "feeding_type", "diaper_type",
               "amount_ml", "duration_minutes", "sleep_duration_minutes", "pumped_amount_ml")
    latest = {}
    for kind in categories:
        entry = next((record for record in records if record["entry_type"] == kind), None)
        latest[kind] = ({**{key: entry[key] for key in allowed if key in entry},
            "recorder_label": labels.get(entry["recorded_by"], ""),
            "recorder_number": numbers.get(entry["recorded_by"])} if entry else None)
    cutoff = datetime.utcnow() - timedelta(days=7)
    notes = db.query(FamilyHandoverDB, FamilyMemberDB).join(FamilyMemberDB,
        (FamilyMemberDB.family_id == FamilyHandoverDB.family_id) &
        (FamilyMemberDB.user_id == FamilyHandoverDB.user_id)).filter(
        FamilyHandoverDB.family_id == family_id, FamilyHandoverDB.shared.is_(True),
        FamilyHandoverDB.updated_at >= cutoff, FamilyMemberDB.status == "active",
        FamilyHandoverDB.membership_revision == FamilyMemberDB.revision).all()
    own = db.get(FamilyHandoverDB, (family_id, user.user_id))
    own_visible = own is not None and own.updated_at >= cutoff
    current = own_visible and own.membership_revision == me.revision
    return {"family_id": family_id, "latest": latest, "checked_at": stamp(datetime.utcnow()),
        "membership_revision": me.revision,
        "own_handover": {"text": own.text if own_visible else "", "shared": own.shared if current else False,
            "revision": own.revision if own else 0, "updated_at": stamp(own.updated_at) if own_visible else None},
        "handovers": [{"text": note.text, "recorder_label": labels.get(note.user_id, ""),
            "recorder_number": numbers.get(note.user_id), "updated_at": stamp(note.updated_at)}
            for note, person in notes if note.text.strip()]}


class HandoverWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(default="", max_length=1000)
    shared: StrictBool = False
    revision: int = Field(ge=0, strict=True)
    membership_revision: int = Field(ge=1, strict=True)


@router.post("/api/families/{family_id}/handover")
def save_handover(family_id: str, body: HandoverWrite, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    me = member_of(db, family_id, user.user_id, write=True)
    if me.revision != body.membership_revision:
        db.rollback()
        raise HTTPException(409, "Sharing permissions changed; review before saving")
    values = {"text": body.text.strip(), "shared": body.shared and bool(body.text.strip()),
        "membership_revision": me.revision, "updated_at": datetime.utcnow(), "revision": body.revision + 1}
    try:
        if body.revision == 0:
            db.add(FamilyHandoverDB(family_id=family_id, user_id=user.user_id, **values))
        else:
            changed = db.query(FamilyHandoverDB).filter(FamilyHandoverDB.family_id == family_id,
                FamilyHandoverDB.user_id == user.user_id, FamilyHandoverDB.revision == body.revision,
            ).update(values, synchronize_session=False)
            if changed != 1:
                raise HTTPException(409, "Handover changed on another screen")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Handover changed on another screen") from None
    return {"saved": True, "revision": body.revision + 1}


def invite_manager(db, family_id, user_id):
    member = member_of(db, family_id, user_id, write=True)
    if member.role not in ("owner", "admin"):
        raise HTTPException(403, "Only a family manager can issue invitations")
    return member


@router.post("/api/families/{family_id}/invite-links")
@rate_limit(RATE_LIMITS["auth"])
def create_invite_link(request: Request, family_id: str, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    me = invite_manager(db, family_id, user.user_id)
    # Limit unused links; never retain recoverable invite secrets.
    db.query(FamilyInviteLinkDB).filter(FamilyInviteLinkDB.family_id == family_id,
        FamilyInviteLinkDB.created_by == user.user_id, FamilyInviteLinkDB.used_at.is_(None),
    ).update({"revoked": True}, synchronize_session=False)
    token = secrets.token_urlsafe(32)
    row = FamilyInviteLinkDB(token_hash=hashlib.sha256(token.encode()).hexdigest(), family_id=family_id,
        created_by=user.user_id, membership_revision=me.revision, expires_at=datetime.utcnow() + timedelta(hours=24))
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "token": token, "expires_at": stamp(row.expires_at)}


@router.get("/api/families/{family_id}/invite-links")
def list_invite_links(family_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    me = member_of(db, family_id, user.user_id)
    if me.role not in ("owner", "admin"):
        raise HTTPException(403, "Only a family manager can view invitations")
    rows = db.query(FamilyInviteLinkDB).join(FamilyMemberDB,
        (FamilyMemberDB.family_id == FamilyInviteLinkDB.family_id) &
        (FamilyMemberDB.user_id == FamilyInviteLinkDB.created_by)).filter(FamilyInviteLinkDB.family_id == family_id,
        FamilyInviteLinkDB.used_at.is_(None), FamilyInviteLinkDB.revoked.is_(False),
        FamilyInviteLinkDB.expires_at > datetime.utcnow(), FamilyMemberDB.status == "active",
        FamilyMemberDB.revision == FamilyInviteLinkDB.membership_revision,
        FamilyMemberDB.role.in_(("owner", "admin"))).all()
    return [{"id": row.id, "expires_at": stamp(row.expires_at)} for row in rows]


@router.post("/api/families/{family_id}/invite-links/{link_id}/revoke")
def revoke_invite_link(family_id: str, link_id: UUID, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    invite_manager(db, family_id, user.user_id)
    db.query(FamilyInviteLinkDB).filter(FamilyInviteLinkDB.family_id == family_id,
        FamilyInviteLinkDB.id == str(link_id)).update({"revoked": True}, synchronize_session=False)
    db.commit()
    return {"revoked": True}


class InviteToken(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


def valid_invite(db, token):
    row = db.query(FamilyInviteLinkDB).filter(
        FamilyInviteLinkDB.token_hash == hashlib.sha256(token.encode()).hexdigest()).first()
    if row is None or row.revoked or row.expires_at <= datetime.utcnow():
        raise HTTPException(410, "Invitation is unavailable")
    inviter = db.query(FamilyMemberDB).filter(FamilyMemberDB.family_id == row.family_id,
        FamilyMemberDB.user_id == row.created_by, FamilyMemberDB.status == "active",
        FamilyMemberDB.revision == row.membership_revision, FamilyMemberDB.role.in_(("owner", "admin"))).first()
    if inviter is None:
        raise HTTPException(410, "Invitation is unavailable")
    return row


@router.post("/api/family-invitations/preview")
@rate_limit(RATE_LIMITS["auth"])
def preview_invitation(request: Request, body: InviteToken, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    row = valid_invite(db, body.token)
    if row.used_at and row.used_by != user.user_id:
        raise HTTPException(410, "Invitation is unavailable")
    family = db.query(FamilyDB).filter(FamilyDB.family_id == row.family_id).first()
    if family is None:
        raise HTTPException(410, "Invitation is unavailable")
    return {"name": family.name, "expires_at": stamp(row.expires_at)}


@router.post("/api/family-invitations/accept")
@rate_limit(RATE_LIMITS["auth"])
def accept_link(request: Request, body: InviteToken, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = valid_invite(db, body.token)
    existing = db.query(FamilyMemberDB).filter(FamilyMemberDB.family_id == row.family_id,
        FamilyMemberDB.user_id == user.user_id).first()
    if row.used_at:
        if row.used_by == user.user_id and existing and existing.status == "active":
            return {"family_id": row.family_id, "accepted": True}
        raise HTTPException(410, "Invitation is unavailable")
    allowed = select(FamilyMemberDB.id).where(FamilyMemberDB.family_id == row.family_id,
        FamilyMemberDB.user_id == row.created_by, FamilyMemberDB.status == "active",
        FamilyMemberDB.revision == row.membership_revision, FamilyMemberDB.role.in_(("owner", "admin"))).exists()
    claimed = db.query(FamilyInviteLinkDB).filter(FamilyInviteLinkDB.id == row.id,
        FamilyInviteLinkDB.used_at.is_(None), FamilyInviteLinkDB.revoked.is_(False),
        FamilyInviteLinkDB.expires_at > datetime.utcnow(), allowed,
    ).update({"used_by": user.user_id, "used_at": datetime.utcnow()}, synchronize_session=False)
    if claimed != 1:
        db.rollback()
        raise HTTPException(409, "Invitation changed; review again")
    try:
        if existing is None:
            db.add(FamilyMemberDB(family_id=row.family_id, user_id=user.user_id, role="member", status="active",
                invited_by=row.created_by, permissions={}, joined_at=datetime.utcnow()))
        elif existing.status != "active":
            changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.id == existing.id,
                FamilyMemberDB.revision == existing.revision, FamilyMemberDB.status == existing.status,
            ).update({"status": "active", "role": "member", "permissions": {}, "invited_by": row.created_by,
                "joined_at": datetime.utcnow(), "revision": existing.revision + 1}, synchronize_session=False)
            if changed != 1:
                raise HTTPException(409, "Membership changed; review again")
        else:
            changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.id == existing.id,
                FamilyMemberDB.revision == existing.revision, FamilyMemberDB.status == "active",
            ).update({"revision": existing.revision}, synchronize_session=False)
            if changed != 1:
                raise HTTPException(409, "Membership changed; review again")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Membership changed; review again") from None
    return {"family_id": row.family_id, "accepted": True}


class JourneyWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["preparing", "waiting", "booked"] = "preparing"
    next_contact_at: Optional[datetime] = None
    revision: int = Field(ge=0, strict=True)
    cleared: StrictBool = False

    @field_validator("next_contact_at")
    @classmethod
    def zoned_time(cls, value):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("Include the time zone")
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value


def journey_dict(row):
    return {"contact_key": row.contact_key, "contact_name": row.contact_name, "state": row.state,
        "next_contact_at": stamp(row.next_contact_at), "revision": row.revision, "cleared": row.cleared,
        "updated_at": stamp(row.updated_at)}


@router.get("/api/support-journeys")
def journeys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [journey_dict(row) for row in db.query(SupportJourneyDB).filter(SupportJourneyDB.user_id == user.user_id).all()]


@router.post("/api/support-journeys/{contact_key}")
def save_journey(contact_key: str, body: JourneyWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    published = db.get(PilotProfileDB, "local")
    profile = published.profile if published else {}
    names = {str(item["resource_key"]): item.get("name", "") for item in profile.get("resources", []) if item.get("resource_key")}
    if profile.get("name"):
        names["organization"] = profile["name"]
    existing = db.get(SupportJourneyDB, (user.user_id, contact_key))
    if contact_key not in names and existing is None:
        raise HTTPException(404, "Contact not found")
    values = {"contact_name": names.get(contact_key, existing.contact_name if existing else ""),
        "state": body.state if not body.cleared else "preparing", "next_contact_at": None if body.cleared else body.next_contact_at,
        "cleared": body.cleared, "revision": body.revision + 1, "updated_at": datetime.utcnow()}
    try:
        if body.revision == 0:
            db.add(SupportJourneyDB(user_id=user.user_id, contact_key=contact_key, **values))
        else:
            changed = db.query(SupportJourneyDB).filter(SupportJourneyDB.user_id == user.user_id,
                SupportJourneyDB.contact_key == contact_key, SupportJourneyDB.revision == body.revision,
            ).update(values, synchronize_session=False)
            if changed != 1:
                raise HTTPException(409, "Help progress changed on another screen")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Help progress changed on another screen") from None
    row = db.query(SupportJourneyDB).filter(SupportJourneyDB.user_id == user.user_id,
        SupportJourneyDB.contact_key == contact_key).populate_existing().one()
    return journey_dict(row)
