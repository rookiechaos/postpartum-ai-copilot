"""Small-pilot directory. Staff privileges never grant access to family records."""

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from config.settings import get_settings
from dependencies.database import get_db
from middleware.auth import get_current_user
from middleware.rate_limit import RATE_LIMITS, rate_limit
from models.database import PilotProfileDB
from models.schemas import User

router = APIRouter(prefix="/api/pilot", tags=["local-pilot"])


class LocalResource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=500)
    hours: str = Field(default="", max_length=200)
    checked_on: Optional[date] = None

    @field_validator("url")
    @classmethod
    def public_https_link(cls, value):
        parts = urlsplit(value)
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
    resources: List[LocalResource] = Field(default_factory=list, max_length=10)


async def require_institution_staff(current_user: User = Depends(get_current_user)):
    configured = get_settings().institution_user_ids or ""
    allowed = {value.strip() for value in configured.split(",") if value.strip()}
    if not current_user.is_active or current_user.user_id not in allowed:
        raise HTTPException(status_code=403, detail="Institution access has not been granted")
    return current_user


def read_profile(db: Session):
    record = db.get(PilotProfileDB, "local")
    return {
        "profile": record.profile if record else PilotProfile().model_dump(mode="json"),
        "updated_at": record.updated_at.isoformat() + "Z" if record else None,
        "ai_provider": get_settings().ai_provider,
    }


@router.get("")
def public_directory(db: Session = Depends(get_db)):
    """Public, operator-maintained contact information; works without AI or login."""
    return read_profile(db)


@router.get("/organization")
def staff_directory(
    current_user: User = Depends(require_institution_staff),
    db: Session = Depends(get_db),
):
    return read_profile(db)


@router.post("/organization")
@rate_limit(RATE_LIMITS["default"])
def save_directory(
    request: Request,
    profile: PilotProfile,
    current_user: User = Depends(require_institution_staff),
    db: Session = Depends(get_db),
):
    record = db.get(PilotProfileDB, "local")
    if record is None:
        record = PilotProfileDB(id="local")
        db.add(record)
    record.profile = profile.model_dump(mode="json")
    record.updated_by = current_user.user_id
    record.updated_at = datetime.utcnow()
    db.commit()
    return read_profile(db)
