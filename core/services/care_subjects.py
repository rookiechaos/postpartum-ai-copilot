"""Explicit attribution and family sharing checks, without external processing."""

from sqlalchemy import or_
from models.database import CareSubjectDB, FamilyDB, FamilyMemberDB
from exceptions import NotFoundError, ValidationError, ConflictError

CARE_TYPES = {"feeding", "diaper", "sleep", "pumping"}


def accessible_subjects(db, user_id):
    families = db.query(FamilyMemberDB, FamilyDB).join(FamilyDB,
        FamilyMemberDB.family_id == FamilyDB.family_id).filter(FamilyMemberDB.user_id == user_id,
        FamilyMemberDB.status == "active").all()
    memberships = {member.family_id: (member, family) for member, family in families}
    rows = db.query(CareSubjectDB).filter(or_(CareSubjectDB.personal_owner_id == user_id,
        CareSubjectDB.family_id.in_(list(memberships)))).all()
    result = []
    for row in rows:
        member, family = memberships.get(row.family_id, (None, None))
        result.append({"subject_id": row.subject_id, "nickname": row.nickname, "revision": row.revision,
            "family_id": row.family_id, "family_name": family.name if family else "",
            "sharing_revision": member.revision if member else None,
            "may_share": bool(member and (member.permissions or {}).get("share_baby") is True),
            "may_edit": row.personal_owner_id == user_id or bool(member and member.role in ("owner", "admin"))})
    return result


def validate_attribution(db, user_id, values, sharing_revision=None):
    kind = values["entry_type"]
    subject_id = values.get("subject_id")
    shared = values.get("family_shared") is True
    if kind not in CARE_TYPES:
        if subject_id or shared:
            raise ValidationError("Adult records must not be attributed to a baby")
        return
    if not subject_id:
        if shared:
            raise ValidationError("Choose a family care subject before sharing a baby record")
        return  # Unassigned historical/new private records remain explicitly unknown.
    subject = db.get(CareSubjectDB, str(subject_id))
    if subject is None:
        raise NotFoundError("Care subject not found")
    if subject.personal_owner_id == user_id:
        if shared:
            raise ValidationError("A personal care subject cannot share records to a family")
        return
    member = db.query(FamilyMemberDB).filter(FamilyMemberDB.family_id == subject.family_id,
        FamilyMemberDB.user_id == user_id, FamilyMemberDB.status == "active").first()
    if member is None:
        raise NotFoundError("Care subject is no longer accessible")
    # Membership lock also serializes creation with revocation on SQLite.
    changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.id == member.id,
        FamilyMemberDB.status == "active", FamilyMemberDB.revision == member.revision,
    ).update({"revision": member.revision}, synchronize_session=False)
    if changed != 1:
        raise ConflictError("Family access changed; review the care subject again")
    if shared and ((member.permissions or {}).get("share_baby") is not True or member.revision != sharing_revision):
        raise ConflictError("Review current baby sharing preferences before sharing this record")


def owned_record_metadata(db, user_id):
    return {item["subject_id"]: item for item in accessible_subjects(db, user_id)}
