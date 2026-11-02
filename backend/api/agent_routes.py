"""Operator-only agent interfaces, separate from family chat and task processing."""

from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from sqlalchemy.orm import Session

from dependencies.container import get_container
from dependencies.database import get_db
from middleware.admin import require_admin
from middleware.rate_limit import RATE_LIMITS, rate_limit
from models.schemas import User

router = APIRouter(prefix="/api/agents", tags=["operator-agents"])
AgentBackend = Literal["codex", "claude_code", "agent"]
AgentRunStatus = Literal["reserved", "running", "completed", "failed", "unknown"]


class AgentRunRequest(BaseModel):
    """Only the explicitly confirmed text is sent to a server-configured runner."""

    model_config = ConfigDict(extra="forbid")

    backend: AgentBackend
    request_id: UUID
    prompt: str = Field(min_length=1, max_length=12000, strict=True)
    instructions: str = Field(default="", max_length=4000, strict=True)
    confirmed: StrictBool

    @field_validator("prompt")
    @classmethod
    def require_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Enter a non-empty prompt")
        return value

    @field_validator("confirmed")
    @classmethod
    def require_confirmation(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Confirm the content before running an agent")
        return value


class AgentBackendCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: AgentBackend
    configured: StrictBool


class AgentCapabilities(BaseModel):
    """Operational limits only; runner URLs, secrets and paths are never returned."""

    model_config = ConfigDict(extra="forbid")

    enabled: StrictBool
    protocol: Literal["postpartum.agent.v1"]
    backends: list[AgentBackendCapability]
    timeout_seconds: int = Field(gt=0, strict=True)
    max_output_chars: int = Field(gt=0, strict=True)
    output_retained: Literal[False] = False
    automatic_retry: Literal[False] = False


class AgentRunMetadata(BaseModel):
    """Owner-scoped receipt; stored records do not contain prompts or outputs."""

    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    request_id: UUID
    backend: AgentBackend
    status: AgentRunStatus
    created_at: str
    finished_at: Optional[str] = None
    output_retained: Literal[False] = False
    error_code: Optional[Literal["AGENT_RUN_FAILED", "AGENT_RESULT_UNKNOWN"]] = None


class AgentRunResult(AgentRunMetadata):
    # Output is delivered only by the original submission response, never by GET.
    output: Optional[str] = None


@router.get("/capabilities", response_model=AgentCapabilities)
@rate_limit(RATE_LIMITS["default"])
def get_agent_capabilities(
    request: Request,
    response: Response,
    current_user: User = Depends(require_admin),
):
    response.headers["Cache-Control"] = "no-store"
    return get_container().get("agent_service").capabilities()


@router.post("/runs", response_model=AgentRunResult, response_model_exclude_none=True)
@rate_limit(RATE_LIMITS["chat"])
async def run_agent(
    request: Request,
    response: Response,
    body: AgentRunRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    return await get_container().get("agent_service").run(
        user_id=current_user.user_id,
        backend=body.backend,
        prompt=body.prompt,
        instructions=body.instructions,
        request_id=str(body.request_id),
        db=db,
    )


@router.get("/runs/{run_id}", response_model=AgentRunMetadata, response_model_exclude_none=True)
@rate_limit(RATE_LIMITS["default"])
def get_agent_run(
    request: Request,
    response: Response,
    run_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    return get_container().get("agent_service").get_run(
        user_id=current_user.user_id,
        run_id=str(run_id),
        db=db,
    )


@router.get("/requests/{request_id}", response_model=AgentRunMetadata, response_model_exclude_none=True)
@rate_limit(RATE_LIMITS["default"])
def get_agent_run_by_request(
    request: Request,
    response: Response,
    request_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # A lost submission response must be checked without submitting again.
    response.headers["Cache-Control"] = "no-store"
    return get_container().get("agent_service").get_run_by_request(
        user_id=current_user.user_id,
        request_id=str(request_id),
        db=db,
    )
