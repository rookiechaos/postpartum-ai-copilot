"""One-attempt gateway to isolated AI runners.

The care-record services and task queue are deliberately not dependencies.
Callers supply already selected text and authenticated scope. Only that text
crosses the runner boundary. The database retains dispatch metadata, never the
text, output or a content digest. Its ``output_retained`` flag describes this
receipt layer only; the existing household task queue can separately retain its
approved questions and results under its own storage policy.
"""

import asyncio
from datetime import datetime, timedelta
import json
from typing import Any, Dict
from uuid import UUID, uuid4

from fastapi import HTTPException
import httpx
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from config.settings import get_settings
from models.database import AgentRunDB


PROTOCOL = "postpartum.agent.v1"
BACKENDS = ("codex", "claude_code", "agent")
ACTIVE_STATES = ("reserved", "running", "unknown")


class _InvalidRunnerResponse(Exception):
    """A response cannot establish a safe, matching terminal result."""


class AgentService:
    """Dispatch at most once for each account/request ID, with no fallback."""

    def __init__(self, settings=None):
        self.settings = settings if settings is not None else get_settings()

    def _configuration(self, backend: str):
        prefix = "agent_custom" if backend == "agent" else f"agent_{backend}"
        url = getattr(self.settings, f"{prefix}_runner_url", None)
        token = getattr(self.settings, f"{prefix}_runner_token", None)
        secret = token.get_secret_value() if token is not None else ""
        return url, secret

    def capabilities(self) -> Dict[str, Any]:
        """Report configuration only; do not probe runners or disclose addresses."""
        return {
            "enabled": self.settings.agent_enabled,
            "protocol": PROTOCOL,
            "backends": [
                {"backend": backend, "configured": all(self._configuration(backend))}
                for backend in BACKENDS
            ],
            "timeout_seconds": self.settings.agent_timeout_seconds,
            "max_output_chars": self.settings.agent_max_output_chars,
            "output_retained": False,
            "automatic_retry": False,
        }

    @staticmethod
    def _metadata(row: AgentRunDB) -> Dict[str, Any]:
        result = {
            "run_id": row.run_id,
            "request_id": row.request_id,
            "backend": row.backend,
            "status": row.state,
            "created_at": row.created_at.isoformat() + "Z",
            "finished_at": row.finished_at.isoformat() + "Z" if row.finished_at else None,
            "output_retained": False,
        }
        if row.state == "failed":
            result["error_code"] = "AGENT_RUN_FAILED"
        elif row.state == "unknown":
            result["error_code"] = "AGENT_RESULT_UNKNOWN"
        return result

    @staticmethod
    def _unavailable():
        return HTTPException(503, "Agent service unavailable")

    @staticmethod
    def _expire_leases(user_id: str, db: Session) -> None:
        """Release stale dispatch slots without restarting or cancelling a run."""
        now = datetime.utcnow()
        db.execute(update(AgentRunDB).where(
            AgentRunDB.user_id == user_id,
            AgentRunDB.active_user_id == user_id,
            AgentRunDB.active_until <= now,
            AgentRunDB.state.in_(ACTIVE_STATES),
        ).values(
            state="unknown",
            finished_at=func.coalesce(AgentRunDB.finished_at, now),
            active_user_id=None,
            active_until=None,
        ).execution_options(synchronize_session=False))

    def _read_run(self, user_id: str, identifier_filter, db: Session) -> Dict[str, Any]:
        """Look up a receipt without dispatching or replaying content."""
        try:
            self._expire_leases(user_id, db)
            db.commit()
            row = db.query(AgentRunDB).populate_existing().filter(
                AgentRunDB.user_id == user_id, identifier_filter,
            ).first()
        except SQLAlchemyError:
            db.rollback()
            raise self._unavailable() from None
        if row is None:
            raise HTTPException(404, "Agent run not found")
        return self._metadata(row)

    def get_run(self, user_id: str, run_id: str, db: Session) -> Dict[str, Any]:
        """Return owner-scoped metadata only; outputs are never replayed."""
        return self._read_run(user_id, AgentRunDB.run_id == str(run_id), db)

    def get_run_by_request(self, user_id: str, request_id: str, db: Session) -> Dict[str, Any]:
        """Recover a receipt when the original response never exposed its run ID."""
        try:
            canonical_request = str(UUID(str(request_id)))
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(404, "Agent run not found") from None
        return self._read_run(user_id, AgentRunDB.request_id == canonical_request, db)

    def _conflict(self, user_id: str, request_id: str, db: Session):
        """A reused key never replays output, even if its new body is identical."""
        row = db.query(AgentRunDB).populate_existing().filter(
            AgentRunDB.user_id == user_id, AgentRunDB.request_id == request_id,
        ).first()
        if row is not None:
            return HTTPException(409, detail={
                "code": "AGENT_REQUEST_ALREADY_RESERVED",
                "message": "This request ID was already reserved; inspect its run status.",
                "run": self._metadata(row),
            })
        row = db.query(AgentRunDB).populate_existing().filter(
            AgentRunDB.active_user_id == user_id,
        ).first()
        if row is not None:
            return HTTPException(409, detail={
                "code": "AGENT_RUN_ACTIVE",
                "message": "An agent run is active or awaiting confirmation; inspect its run status.",
                "run": self._metadata(row),
            })
        return self._unavailable()

    def _reserve(self, user_id: str, backend: str, request_id: str, db: Session):
        now = datetime.utcnow()
        run_id = str(uuid4())
        lease_until = now + timedelta(seconds=self.settings.agent_timeout_seconds + 30)
        try:
            self._expire_leases(user_id, db)
            # Check first for a useful conflict receipt; the unique constraints
            # below remain the authority when concurrent requests race.
            existing = db.query(AgentRunDB).filter(
                AgentRunDB.user_id == user_id,
                AgentRunDB.request_id == request_id,
            ).first()
            if existing is not None:
                db.commit()
                raise self._conflict(user_id, request_id, db)
            row = AgentRunDB(
                run_id=run_id, user_id=user_id, request_id=request_id,
                backend=backend, state="reserved", created_at=now,
                active_user_id=user_id, active_until=lease_until,
            )
            db.add(row)
            # Commit the receipt before any network request. Process loss after
            # this point must never cause a replay of the same client request.
            db.commit()
            return run_id, lease_until
        except IntegrityError:
            db.rollback()
            try:
                raise self._conflict(user_id, request_id, db)
            except SQLAlchemyError:
                db.rollback()
                raise self._unavailable() from None
        except SQLAlchemyError:
            db.rollback()
            raise self._unavailable() from None

    def _start(self, user_id: str, run_id: str, lease_until: datetime, db: Session):
        try:
            changed = db.execute(update(AgentRunDB).where(
                AgentRunDB.run_id == run_id,
                AgentRunDB.user_id == user_id,
                AgentRunDB.state == "reserved",
                AgentRunDB.active_user_id == user_id,
                AgentRunDB.active_until == lease_until,
                AgentRunDB.active_until > datetime.utcnow(),
            ).values(state="running").execution_options(synchronize_session=False)).rowcount
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise self._unavailable() from None
        if changed != 1:
            raise HTTPException(409, detail={
                "code": "AGENT_RUN_STATE_CHANGED",
                "message": "Agent run status changed before dispatch; inspect its run status.",
                "run": self.get_run(user_id, run_id, db),
            })

    def _finish(self, user_id: str, run_id: str, lease_until: datetime,
                state: str, db: Session) -> Dict[str, Any]:
        values = {"state": state, "finished_at": datetime.utcnow()}
        if state != "unknown":
            values.update(active_user_id=None, active_until=None)
        # An uncertain result retains its bounded slot. Its expiry is explicitly
        # not proof that an external runner has stopped processing the request.
        try:
            db.execute(update(AgentRunDB).where(
                AgentRunDB.run_id == run_id,
                AgentRunDB.user_id == user_id,
                AgentRunDB.state == "running",
                AgentRunDB.active_user_id == user_id,
                AgentRunDB.active_until == lease_until,
                AgentRunDB.active_until > datetime.utcnow(),
            ).values(**values).execution_options(synchronize_session=False))
            self._expire_leases(user_id, db)
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise self._unavailable() from None
        return self.get_run(user_id, run_id, db)

    async def _dispatch(self, url: str, token: str, backend: str, prompt: str,
                        instructions: str, run_id: str):
        timeout = self.settings.agent_timeout_seconds
        maximum = self.settings.agent_max_output_chars
        # Twelve bytes accommodate JSON-escaped surrogate pairs. Fixed overhead bounds
        # every other field, including untrusted messages from custom runners.
        maximum_bytes = 12 * maximum + 16384
        payload = {
            "protocol": PROTOCOL, "request_id": run_id, "backend": backend,
            "prompt": prompt, "instructions": instructions,
            "timeout_seconds": timeout, "max_output_chars": maximum,
        }
        async with httpx.AsyncClient(
            trust_env=False, follow_redirects=False, timeout=httpx.Timeout(timeout),
        ) as client:
            async with client.stream("POST", url, headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Accept-Encoding": "identity",
            }, json=payload) as response:
                if response.status_code != 200 or response.headers.get(
                    "content-encoding", "identity").lower() != "identity":
                    raise _InvalidRunnerResponse()
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    if len(body) + len(chunk) > maximum_bytes:
                        raise _InvalidRunnerResponse()
                    body.extend(chunk)
        try:
            result = json.loads(body)
        except (ValueError, UnicodeError, RecursionError):
            raise _InvalidRunnerResponse() from None
        if not isinstance(result, dict) or (
            result.get("protocol") != PROTOCOL or result.get("request_id") != run_id
            or result.get("backend") != backend
        ):
            raise _InvalidRunnerResponse()
        if result.get("status") == "failed":
            return "failed", None
        output = result.get("output")
        if result.get("status") != "completed" or not isinstance(output, str) \
                or not output.strip() or len(output) > maximum:
            raise _InvalidRunnerResponse()
        try:
            output.encode("utf-8")
        except UnicodeError:
            raise _InvalidRunnerResponse() from None
        return "completed", output

    async def run(self, user_id: str, backend: str, prompt: str,
                  instructions: str, request_id: str, db: Session) -> Dict[str, Any]:
        """Make one outbound attempt, recording only its non-content receipt."""
        if not self.settings.agent_enabled:
            raise HTTPException(503, "Agent interfaces are disabled")
        if backend not in BACKENDS:
            raise HTTPException(422, "Unsupported agent backend")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 64000 \
                or not isinstance(instructions, str) or len(instructions) > 16000:
            raise HTTPException(422, "Agent input is outside the supported limits")
        try:
            prompt.encode("utf-8")
            instructions.encode("utf-8")
        except UnicodeError:
            raise HTTPException(422, "Agent input is outside the supported limits") from None
        try:
            request_id = str(UUID(str(request_id)))
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(422, "A valid agent request ID is required") from None
        url, token = self._configuration(backend)
        if not url or not token:
            raise HTTPException(503, "The selected agent runner is not configured")

        run_id, lease_until = self._reserve(user_id, backend, request_id, db)
        self._start(user_id, run_id, lease_until, db)
        try:
            # An explicit wall-clock bound complements httpx's per-I/O limits.
            # There is no retry, provider fallback or background queue handoff.
            state, output = await asyncio.wait_for(
                self._dispatch(url, token, backend, prompt, instructions, run_id),
                timeout=self.settings.agent_timeout_seconds,
            )
        except asyncio.CancelledError:
            self._finish(user_id, run_id, lease_until, "unknown", db)
            raise
        except Exception:
            # An unexpected response/transport failure still cannot establish
            # that a remote run did not start. Keep the receipt and never retry.
            state, output = "unknown", None
        result = self._finish(user_id, run_id, lease_until, state, db)
        # A result is returned only to this dispatching request and only while
        # its terminal state still belongs to this execution. GET is metadata.
        if result["status"] == "completed" and state == "completed":
            result["output"] = output
        return result
