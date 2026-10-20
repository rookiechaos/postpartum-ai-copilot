"""Minimal explicit baby identity, separate from the adult who records care."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from dependencies.database import get_db
from middleware.auth import get_current_user
from models.schemas import User
from models.database import CareSubjectDB, FamilyMemberDB
from services.care_subjects import accessible_subjects

router = APIRouter(prefix="/api/care-subjects", tags=["care-subjects"])


class SubjectWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nickname: str = Field(min_length=1, max_length=40)
    family_id: Optional[str] = Field(default=None, min_length=1, max_length=100)
    revision: int = Field(default=0, ge=0, strict=True)

    @field_validator("nickname")
    @classmethod
    def nonempty_name(cls, value):
        if not value.strip():
            raise ValueError("Enter a nickname")
        return value.strip()


def manager(db, family_id, user_id):
    row = db.query(FamilyMemberDB).filter(FamilyMemberDB.family_id == family_id,
        FamilyMemberDB.user_id == user_id, FamilyMemberDB.status == "active",
        FamilyMemberDB.role.in_(("owner", "admin"))).first()
    if row is None:
        raise HTTPException(403, "A family manager must create or rename the family care subject")
    changed = db.query(FamilyMemberDB).filter(FamilyMemberDB.id == row.id,
        FamilyMemberDB.revision == row.revision, FamilyMemberDB.status == "active",
    ).update({"revision": row.revision}, synchronize_session=False)
    if changed != 1:
        raise HTTPException(409, "Family access changed")


@router.get("")
def list_subjects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return accessible_subjects(db, user.user_id)


@router.post("")
def create_subject(body: SubjectWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.revision != 0:
        raise HTTPException(409, "Reload the current care subject")
    if body.family_id:
        manager(db, body.family_id, user.user_id)
    row = CareSubjectDB(nickname=body.nickname, family_id=body.family_id,
        personal_owner_id=None if body.family_id else user.user_id, created_by=user.user_id)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This account or family already has a care subject; select the existing one") from None
    return accessible_subjects(db, user.user_id)


@router.post("/{subject_id}")
def rename_subject(subject_id: UUID, body: SubjectWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(CareSubjectDB, str(subject_id))
    if row is None or not any(item["subject_id"] == str(subject_id) for item in accessible_subjects(db, user.user_id)):
        raise HTTPException(404, "Care subject not found")
    if row.family_id:
        manager(db, row.family_id, user.user_id)
    if body.family_id != row.family_id:
        raise HTTPException(422, "Renaming cannot move a care subject to another family")
    changed = db.query(CareSubjectDB).filter(CareSubjectDB.subject_id == str(subject_id),
        CareSubjectDB.revision == body.revision).update({"nickname": body.nickname,
        "revision": body.revision + 1}, synchronize_session=False)
    if changed != 1:
        db.rollback()
        raise HTTPException(409, "Care subject changed; reload before editing")
    db.commit()
    return accessible_subjects(db, user.user_id)
