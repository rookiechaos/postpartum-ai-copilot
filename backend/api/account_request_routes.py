"""Manual account/privacy requests. Receiving a request never changes an account."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from dependencies.database import get_db
from middleware.admin import require_admin
from middleware.auth import get_current_user
from middleware.rate_limit import RATE_LIMITS, rate_limit
from models.database import AccountRequestDB
from models.schemas import User
from services.security_validator import InputSanitizer

router = APIRouter(tags=["account-support"])
RequestKind = Literal["access", "deletion", "privacy"]
RequestStatus = Literal["received", "verifying", "completed", "declined"]


class AccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: RequestKind
    language: Literal["ja", "en"] = "ja"


class AccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=255)
    language: Literal["ja", "en"] = "ja"

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if not InputSanitizer.validate_email(value):
            raise ValueError("Enter a valid contact email")
        return value


class RequestUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: RequestStatus
    public_response: str = Field(default="", max_length=1500)


def public_status(record):
    return {
        "reference": record.reference, "kind": record.kind, "status": record.status,
        "public_response": record.public_response,
        "created_at": record.created_at.isoformat() + "Z",
        "updated_at": record.updated_at.isoformat() + "Z",
    }


def create_request(db, kind, language, email, user_id=None):
    record = AccountRequestDB(reference=str(uuid4()), user_id=user_id, contact_email=email,
                              kind=kind, language=language, status="received", public_response="")
    db.add(record)
    db.commit()
    db.refresh(record)
    return public_status(record)


@router.post("/api/pilot/account-help", status_code=201)
@rate_limit(RATE_LIMITS["auth"])
def request_account_access(request: Request, body: AccessRequest, db: Session = Depends(get_db)):
    # Do not look up the email or reveal whether an account exists.
    return create_request(db, "access", body.language, body.email)


@router.get("/api/pilot/account-help/{reference}")
@rate_limit(RATE_LIMITS["default"])
def read_request_status(request: Request, reference: UUID, db: Session = Depends(get_db)):
    record = db.get(AccountRequestDB, str(reference))
    if record is None:
        raise HTTPException(status_code=404, detail="Request not found")
    # The unguessable reference returns status and an operator's public reply only.
    return public_status(record)


@router.post("/api/account/requests", status_code=201)
@rate_limit(RATE_LIMITS["default"])
def request_account_support(request: Request, body: AccountRequest,
                            current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_request(db, body.kind, body.language, current_user.email, current_user.user_id)


@router.get("/api/account/requests")
def own_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    records = db.query(AccountRequestDB).filter(AccountRequestDB.user_id == current_user.user_id).order_by(
        AccountRequestDB.created_at.desc()).limit(30).all()
    return [public_status(record) for record in records]


@router.get("/api/admin/account-requests")
def operator_requests(status: Optional[RequestStatus] = Query(None), limit: int = Query(50, ge=1, le=100),
                      offset: int = Query(0, ge=0),
                      current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    query = db.query(AccountRequestDB)
    if status:
        query = query.filter(AccountRequestDB.status == status)
    records = query.order_by(AccountRequestDB.created_at.asc(), AccountRequestDB.reference.asc()).offset(offset).limit(limit).all()
    return [{**public_status(record), "contact_email": record.contact_email,
             "user_id": record.user_id, "language": record.language, "updated_by": record.updated_by} for record in records]


@router.post("/api/admin/account-requests/{reference}")
def update_request(reference: UUID, body: RequestUpdate, current_user: User = Depends(require_admin),
                   db: Session = Depends(get_db)):
    record = db.get(AccountRequestDB, str(reference))
    if record is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if body.status in ("completed", "declined") and not body.public_response.strip():
        raise HTTPException(status_code=422, detail="Add a response explaining the outcome")
    record.status = body.status
    record.public_response = body.public_response.strip()
    record.updated_by = current_user.user_id
    record.updated_at = datetime.utcnow()
    db.commit()
    return public_status(record)
