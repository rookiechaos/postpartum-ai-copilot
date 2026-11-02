"""Per-call identity for household AI runner dispatches, never singleton state."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class AgentCallContext:
    user_id: str
    request_id: str


_agent_call: ContextVar[Optional[AgentCallContext]] = ContextVar("agent_call", default=None)


@contextmanager
def agent_call_scope(user_id: str, request_id: Optional[str] = None):
    """Bind one authenticated caller and a stable UUID to one AI operation.

    API callers omit the UUID for a fresh server-generated call. Queue workers
    must supply the same UUID for every execution of the same task. Nesting and
    concurrent asyncio tasks restore their previous context independently.
    """
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("An authenticated agent caller is required")
    try:
        canonical_request = str(uuid4()) if request_id is None else str(UUID(str(request_id)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A valid agent request ID is required") from None
    context = AgentCallContext(user_id=user_id, request_id=canonical_request)
    token = _agent_call.set(context)
    try:
        yield context
    finally:
        _agent_call.reset(token)


def get_agent_call_context() -> Optional[AgentCallContext]:
    """No context means dispatch is forbidden, rather than a new anonymous run."""
    return _agent_call.get()
