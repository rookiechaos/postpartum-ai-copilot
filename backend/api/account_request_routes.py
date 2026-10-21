"""Manual account/privacy requests. Receiving a request never changes an account."""

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dependencies.database import get_db
from middleware.admin import require_admin
from middleware.auth import get_current_user
from middleware.rate_limit import RATE_LIMITS, rate_limit
from models.database import AccountRequestDB, AccountWorkflowDB, AccountWorkflowEventDB
from models.schemas import User
from services.security_validator import InputSanitizer

router = APIRouter(tags=["account-support"])
RequestKind = Literal["access", "deletion", "privacy"]
RequestStatus = Literal["received", "verifying", "completed", "declined"]
REQUIRED_STEPS = {
    "access": ["identity_checked", "recovery_executed", "delivery_confirmed"],
    "deletion": ["identity_checked", "active_data_erased", "family_access_revoked", "credentials_revoked", "retention_explained"],
    "privacy": ["response_prepared"],
}


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


class AccountStatusLookup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: UUID


class RequestUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: RequestStatus
    public_response: str = Field(default="", max_length=1500)
    revision: int = Field(ge=0, strict=True)
    identity_verified: StrictBool = False
    verification_reference: str = Field(default="", max_length=200)
    execution_reference: str = Field(default="", max_length=200)
    steps: list[str] = Field(default_factory=list, max_length=8)
    next_action: str = Field(default="", max_length=500)
    expected_reply_at: Optional[datetime] = None
    outcome: str = Field(default="", max_length=1000)
    retained_data_notice: str = Field(default="", max_length=1000)

    @field_validator("expected_reply_at")
    @classmethod
    def zoned_reply(cls, value):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("Include the time zone")
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value


def public_status(record, db):
    workflow = db.get(AccountWorkflowDB, record.reference)
    details = workflow.details if workflow else {}
    return {
        "reference": record.reference, "kind": record.kind, "status": record.status,
        "public_response": record.public_response,
        "created_at": record.created_at.isoformat() + "Z",
        "updated_at": record.updated_at.isoformat() + "Z",
        "next_action": details.get("next_action", ""),
        "expected_reply_at": details.get("expected_reply_at"),
        "receipt": details.get("receipt"),
    }


def create_request(db, kind, language, email, user_id=None):
    record = AccountRequestDB(reference=str(uuid4()), user_id=user_id, contact_email=email,
                              kind=kind, language=language, status="received", public_response="")
    db.add(record)
    db.commit()
    db.refresh(record)
    return public_status(record, db)


@router.post("/api/pilot/account-help", status_code=201)
@rate_limit(RATE_LIMITS["auth"])
def request_account_access(request: Request, body: AccessRequest, db: Session = Depends(get_db)):
    # Do not look up the email or reveal whether an account exists.
    return create_request(db, "access", body.language, body.email)


@router.post("/api/pilot/account-help/status")
@rate_limit(RATE_LIMITS["default"])
def read_request_status(request: Request, body: AccountStatusLookup, db: Session = Depends(get_db)):
    record = db.get(AccountRequestDB, str(body.reference))
    if record is None:
        raise HTTPException(status_code=404, detail="Request not found")
    # The unguessable reference returns status and an operator's public reply only.
    return public_status(record, db)


@router.get("/api/pilot/account-help/{reference}")
def retired_status_lookup(reference: str):
    # Never expose a reply through a URL bearer credential, including old clients.
    raise HTTPException(status_code=410, detail="Update the app to check request status")


@router.post("/api/account/requests", status_code=201)
@rate_limit(RATE_LIMITS["default"])
def request_account_support(request: Request, body: AccountRequest,
                            current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_request(db, body.kind, body.language, current_user.email, current_user.user_id)


@router.get("/api/account/requests")
def own_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    records = db.query(AccountRequestDB).filter(AccountRequestDB.user_id == current_user.user_id).order_by(
        AccountRequestDB.created_at.desc()).limit(30).all()
    return [public_status(record, db) for record in records]


@router.get("/api/admin/account-requests")
def operator_requests(status: Optional[RequestStatus] = Query(None), limit: int = Query(50, ge=1, le=100),
                      offset: int = Query(0, ge=0),
                      current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    query = db.query(AccountRequestDB)
    if status:
        query = query.filter(AccountRequestDB.status == status)
    records = query.order_by(AccountRequestDB.created_at.asc(), AccountRequestDB.reference.asc()).offset(offset).limit(limit).all()
    result = []
    for record in records:
        workflow = db.get(AccountWorkflowDB, record.reference)
        events = db.query(AccountWorkflowEventDB).filter(AccountWorkflowEventDB.reference == record.reference).order_by(
            AccountWorkflowEventDB.created_at.desc(), AccountWorkflowEventDB.id.desc()).limit(20).all()
        result.append({**public_status(record, db), "contact_email": record.contact_email,
            "user_id": record.user_id, "language": record.language, "updated_by": record.updated_by,
            "revision": workflow.revision if workflow else 0, "workflow": workflow.details if workflow else {},
            "required_steps": REQUIRED_STEPS[record.kind],
            "events": [{"status": event.status, "at": event.created_at.isoformat() + "Z"} for event in events]})
    return result


@router.post("/api/admin/account-requests/{reference}")
def update_request(reference: UUID, body: RequestUpdate, current_user: User = Depends(require_admin),
                   db: Session = Depends(get_db)):
    record = db.query(AccountRequestDB).filter(AccountRequestDB.reference == str(reference)).with_for_update().first()
    if record is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if body.status in ("completed", "declined") and not body.public_response.strip():
        raise HTTPException(status_code=422, detail="Add a response explaining the outcome")
    if record.status in ("completed", "declined"):
        raise HTTPException(409, "A finalized receipt cannot be changed")
    required = REQUIRED_STEPS[record.kind]
    if any(step not in required for step in body.steps):
        raise HTTPException(422, "Unknown processing step")
    if body.identity_verified and not body.verification_reference.strip():
        raise HTTPException(422, "Record the verification procedure reference, not identity documents")
    if body.status == "completed":
        if record.kind in ("access", "deletion") and not body.identity_verified:
            raise HTTPException(422, "Verify identity before confirming account processing")
        if not set(required).issubset(body.steps) or not body.outcome.strip() or not body.execution_reference.strip():
            raise HTTPException(422, "Confirm actual processing and add its reference and result")
        if record.kind == "deletion" and not body.retained_data_notice.strip():
            raise HTTPException(422, "Explain the scope and retention of remaining copies")
    elif body.status not in ("declined",) and (not body.next_action.strip() or body.expected_reply_at is None):
        raise HTTPException(422, "Give the family a next step and expected response time")
    now = datetime.utcnow()
    details = body.model_dump(exclude={"status", "revision", "public_response", "expected_reply_at"})
    details = {key: value.strip() if isinstance(value, str) else value for key, value in details.items()}
    details["expected_reply_at"] = body.expected_reply_at.isoformat() + "Z" if body.expected_reply_at else None
    # This is an attestation of controlled manual work, not an automatic reset or erasure.
    details["receipt"] = {"id": str(uuid4()), "completed_at": now.isoformat() + "Z",
        "kind": record.kind, "outcome": body.outcome.strip(), "retained_data_notice": body.retained_data_notice.strip(),
        "method": "operator_confirmed_manual_processing"} if body.status == "completed" else None
    workflow = db.get(AccountWorkflowDB, record.reference)
    if workflow is None:
        if body.revision != 0:
            raise HTTPException(409, "Request changed; reload before saving")
        db.add(AccountWorkflowDB(reference=record.reference, revision=1, details=details))
    else:
        changed = db.query(AccountWorkflowDB).filter(AccountWorkflowDB.reference == record.reference,
            AccountWorkflowDB.revision == body.revision).update(
                {"revision": body.revision + 1, "details": details}, synchronize_session=False)
        if changed != 1:
            db.rollback()
            raise HTTPException(409, "Request changed; reload before saving")
    record.status = body.status
    record.public_response = body.public_response.strip()
    record.updated_by = current_user.user_id
    record.updated_at = now
    db.add(AccountWorkflowEventDB(reference=record.reference, operator_id=current_user.user_id,
        status=body.status, created_at=now))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Request changed; reload before saving") from None
    db.expire_all()
    return public_status(db.get(AccountRequestDB, str(reference)), db)
