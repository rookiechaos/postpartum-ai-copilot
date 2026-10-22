"""Explicit household handovers, single-use invitations and private help progress."""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import json
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dependencies.container import get_container
from dependencies.database import get_db
from middleware.auth import get_current_user
from middleware.rate_limit import RATE_LIMITS, rate_limit
from models.database import (FamilyDB, FamilyMemberDB, FamilyHandoverDB, FamilyHandoverAcknowledgementDB, FamilyInviteLinkDB,
                             SupportJourneyDB, PilotProfileDB, FamilyReviewDB)
from models.schemas import User
from exceptions import NotFoundError
from services.care_periods import period_bounds, in_period
from services.family_service import lock_family_membership_changes

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
    member_revisions = {person.user_id: person.revision for person in people}
    acknowledgements = db.query(FamilyHandoverAcknowledgementDB).filter(
        FamilyHandoverAcknowledgementDB.family_id == family_id).all()

    def receipts(note):
        return [{"recorder_label": labels.get(receipt.user_id, ""),
            "recorder_number": numbers[receipt.user_id], "note_revision": receipt.note_revision,
            "is_me": receipt.user_id == user.user_id, "acknowledged_at": stamp(receipt.acknowledged_at)}
            for receipt in acknowledgements if receipt.author_id == note.user_id
            and receipt.author_membership_revision == note.membership_revision
            and member_revisions.get(receipt.user_id) == receipt.reader_membership_revision]
    # No parent records or free-text tracking notes enter the home overview.
    allowed = ("record_key", "timestamp", "end_timestamp", "subject_id", "subject_name", "entry_type", "recorded_by", "feeding_type", "diaper_type",
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
        "handovers": [{"author_id": note.user_id, "revision": note.revision, "is_own": note.user_id == user.user_id,
            "membership_revision": note.membership_revision, "acknowledgements": receipts(note),
            "text": note.text, "recorder_label": labels.get(note.user_id, ""),
            "recorder_number": numbers.get(note.user_id), "updated_at": stamp(note.updated_at)}
            for note, person in notes if note.text.strip()]}


def review_digest(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def review_snapshot(db, family_id, user):
    user_id = user.user_id
    overview = family_overview(family_id, user=user, db=db)
    records = get_container().get("family_service").get_shared_tracking_data(family_id, user_id, days=7, db=db)
    records = [record for record in records if record["entry_type"] in ("feeding", "diaper", "sleep", "pumping")]
    people = db.query(FamilyMemberDB).filter(FamilyMemberDB.family_id == family_id,
        FamilyMemberDB.status == "active").all()
    memberships = {person.user_id: person.revision for person in people}
    snapshot = {"family_id": family_id, "reader_id": user_id, "membership": overview["membership_revision"],
        "records": {record["record_key"]: [record["revision"], memberships.get(record["recorded_by"])] for record in records},
        "notes": {note["author_id"]: [note["revision"], note["membership_revision"]] for note in overview["handovers"]}}
    return overview, records, snapshot


@router.get("/api/families/{family_id}/review")
def get_family_review(family_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    overview, records, snapshot = review_snapshot(db, family_id, user)
    saved = db.get(FamilyReviewDB, (family_id, user.user_id))
    baseline = saved.snapshot if saved and saved.membership_revision == overview["membership_revision"] else None
    old_records = (baseline or {}).get("records", {})
    old_notes = (baseline or {}).get("notes", {})
    fields = ("record_key", "entry_type", "timestamp", "end_timestamp", "subject_id", "subject_name",
        "feeding_type", "diaper_type", "amount_ml", "duration_minutes", "sleep_duration_minutes", "pumped_amount_ml", "recorder_label")
    changes = [{**{key: record.get(key) for key in fields},
        "change": "initial" if baseline is None else "new" if record["record_key"] not in old_records else "updated"}
        for record in records if old_records.get(record["record_key"]) != snapshot["records"][record["record_key"]]]
    notes = [{"author_id": note["author_id"], "revision": note["revision"], "recorder_label": note["recorder_label"],
        "recorder_number": note["recorder_number"], "updated_at": note["updated_at"],
        "change": "initial" if baseline is None else "new" if note["author_id"] not in old_notes else "updated"}
        for note in overview["handovers"] if old_notes.get(note["author_id"]) != snapshot["notes"][note["author_id"]]]
    return {"revision": saved.revision if saved else 0, "digest": review_digest(snapshot),
        "membership_revision": overview["membership_revision"], "first_review": baseline is None,
        "confirmed_at": stamp(saved.confirmed_at) if baseline is not None else None,
        "checked_at": stamp(datetime.utcnow()), "records": changes, "notes": notes,
        "withdrawn_count": len(set(old_records) - set(snapshot["records"])) + len(set(old_notes) - set(snapshot["notes"]))}


class FamilyReviewWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0, strict=True)
    membership_revision: int = Field(ge=1, strict=True)
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    confirmed: StrictBool


@router.post("/api/families/{family_id}/review")
def confirm_family_review(family_id: str, body: FamilyReviewWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    me = member_of(db, family_id, user.user_id, write=True)
    if not body.confirmed or me.revision != body.membership_revision:
        raise HTTPException(409, "Review current family access before confirming")
    saved = db.query(FamilyReviewDB).populate_existing().filter(FamilyReviewDB.family_id == family_id,
        FamilyReviewDB.user_id == user.user_id).first()
    if saved and saved.revision == body.revision + 1 and saved.membership_revision == me.revision and review_digest(saved.snapshot) == body.digest:
        return {"saved": True, "revision": saved.revision, "confirmed_at": stamp(saved.confirmed_at)}
    if (saved.revision if saved else 0) != body.revision:
        raise HTTPException(409, "Review confirmation changed on another screen")
    _, _, snapshot = review_snapshot(db, family_id, user)
    if review_digest(snapshot) != body.digest:
        raise HTTPException(409, "Family records changed; reload and review the new version")
    now = datetime.utcnow()
    if saved:
        saved.snapshot = snapshot; saved.membership_revision = me.revision
        saved.revision += 1; saved.confirmed_at = now
    else:
        db.add(FamilyReviewDB(family_id=family_id, user_id=user.user_id, membership_revision=me.revision,
            revision=1, snapshot=snapshot, confirmed_at=now))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Review confirmation changed on another screen") from None
    return {"saved": True, "revision": body.revision + 1, "confirmed_at": stamp(now)}


@router.get("/api/families/{family_id}/timeline")
def family_timeline(family_id: str, period: Literal["today", "yesterday", "last24"] = Query("today"),
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member_of(db, family_id, user.user_id)
    records = get_container().get("family_service").get_shared_tracking_data(family_id, user.user_id, days=2, db=db)
    people = db.query(FamilyMemberDB).filter(FamilyMemberDB.family_id == family_id,
        FamilyMemberDB.status == "active").order_by(FamilyMemberDB.id).all()
    numbers = {person.user_id: index + 1 for index, person in enumerate(people)}
    today = datetime.now(timezone(timedelta(hours=9))).date()
    # The home timeline never broadens sharing to adult records or free-text notes.
    start, end = period_bounds(period)
    allowed = ("record_key", "timestamp", "end_timestamp", "subject_id", "subject_name", "entry_type", "feeding_type", "diaper_type", "side",
               "amount_ml", "duration_minutes", "sleep_duration_minutes", "sleep_quality", "pumped_amount_ml")
    result = []
    for entry in records:
        if entry["entry_type"] not in ("feeding", "diaper", "sleep", "pumping"):
            continue
        if not in_period(entry, start, end):
            continue
        result.append({**{key: entry[key] for key in allowed if key in entry},
            "recorder_label": entry.get("recorder_label", ""), "recorder_number": numbers.get(entry["recorded_by"]),
            "is_own": entry["recorded_by"] == user.user_id})
    return {"family_id": family_id, "day": today.isoformat(), "period": period,
        "records": result, "checked_at": stamp(datetime.utcnow())}


class HandoverAcknowledgement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1, strict=True)
    membership_revision: int = Field(ge=1, strict=True)


@router.post("/api/families/{family_id}/handovers/{author_id}/acknowledge")
def acknowledge_handover(family_id: str, author_id: str, body: HandoverAcknowledgement,
                        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if author_id == user.user_id:
        raise HTTPException(422, "Confirm another family member's handover")
    # A consistent lock order serializes acknowledgements with membership changes.
    members = {member_id: member_of(db, family_id, member_id, write=True)
        for member_id in sorted((user.user_id, author_id))}
    author = members[author_id]
    if author.revision != body.membership_revision:
        db.rollback()
        raise HTTPException(409, "Handover sharing changed; review again")
    # Guard the exact visible version, and lock against a concurrent note edit.
    changed = db.query(FamilyHandoverDB).filter(FamilyHandoverDB.family_id == family_id,
        FamilyHandoverDB.user_id == author_id, FamilyHandoverDB.revision == body.revision,
        FamilyHandoverDB.membership_revision == author.revision, FamilyHandoverDB.shared.is_(True),
        FamilyHandoverDB.text != "", FamilyHandoverDB.updated_at >= datetime.utcnow() - timedelta(days=7),
    ).update({"revision": FamilyHandoverDB.revision}, synchronize_session=False)
    if changed != 1:
        db.rollback()
        raise HTTPException(409, "Handover changed; read the current version before confirming")
    key = (family_id, author_id, user.user_id)
    row = db.get(FamilyHandoverAcknowledgementDB, key)
    reader_revision = members[user.user_id].revision
    if row is None:
        row = FamilyHandoverAcknowledgementDB(family_id=family_id, author_id=author_id, user_id=user.user_id)
        db.add(row)
    if row.note_revision != body.revision or row.author_membership_revision != author.revision or row.reader_membership_revision != reader_revision:
        row.note_revision = body.revision
        row.author_membership_revision = author.revision
        row.reader_membership_revision = reader_revision
        row.acknowledged_at = datetime.utcnow()
    confirmed_at = row.acknowledged_at
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Confirmation changed; reload before trying again") from None
    return {"confirmed": True, "revision": body.revision, "acknowledged_at": stamp(confirmed_at)}


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
    # All invitation writers acquire family -> members -> invitation rows.
    lock_family_membership_changes(db, family_id)
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
    lock_family_membership_changes(db, family_id)
    invite_manager(db, family_id, user.user_id)
    db.query(FamilyInviteLinkDB).filter(FamilyInviteLinkDB.family_id == family_id,
        FamilyInviteLinkDB.id == str(link_id)).update({"revoked": True}, synchronize_session=False)
    db.commit()
    return {"revoked": True}


class InviteToken(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


def valid_invite(db, token):
    row = db.query(FamilyInviteLinkDB).populate_existing().filter(
        FamilyInviteLinkDB.token_hash == hashlib.sha256(token.encode()).hexdigest()).first()
    if row is None or row.revoked or row.expires_at <= datetime.utcnow():
        raise HTTPException(410, "Invitation is unavailable")
    inviter = db.query(FamilyMemberDB).populate_existing().filter(FamilyMemberDB.family_id == row.family_id,
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
    # Locate without a write lock or cached ORM token. The invitation can change
    # while waiting for the family lock and must be validated again afterwards.
    located = db.query(FamilyInviteLinkDB.family_id).filter(
        FamilyInviteLinkDB.token_hash == hashlib.sha256(body.token.encode()).hexdigest()).first()
    if located is None:
        raise HTTPException(410, "Invitation is unavailable")
    family_id = located[0]
    try:
        lock_family_membership_changes(db, family_id)
    except NotFoundError:
        raise HTTPException(410, "Invitation is unavailable") from None
    row = valid_invite(db, body.token)
    if row.family_id != family_id:
        raise HTTPException(410, "Invitation is unavailable")
    members = get_container().get("family_service")._lock_members_in_order(
        db, family_id, (row.created_by, user.user_id))
    # Sharing changes use the issuer's membership row without a family lock;
    # refresh the token and issuer after the ordered member locks as well.
    row = valid_invite(db, body.token)
    existing = members.get(user.user_id)
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
    state: Literal["preparing", "waiting", "booked", "completed", "paused"] = "preparing"
    next_contact_at: Optional[datetime] = None
    contact_response: Optional[str] = Field(default=None, max_length=1500)
    next_steps: Optional[str] = Field(default=None, max_length=1500)
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
        "contact_response": row.contact_response, "next_steps": row.next_steps,
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
        "state": body.state if not body.cleared else "preparing", "next_contact_at": None if body.cleared or body.state in ("completed", "paused") else body.next_contact_at,
        "contact_response": "" if body.cleared else body.contact_response if body.contact_response is not None else existing.contact_response if existing else "",
        "next_steps": "" if body.cleared else body.next_steps if body.next_steps is not None else existing.next_steps if existing else "",
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
