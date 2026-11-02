# Architecture

Postpartum AI Copilot uses a server-client architecture with an async task queue for long-running AI workloads.

## Overview

| Layer | Location | Role |
|-------|----------|------|
| API server | `backend/` | HTTP endpoints, auth middleware, models |
| Domain logic | `core/services/` | Business services |
| Workers | `workers/` | Async task processing |
| Task queue | SQL-backed custom queue | Priority, retries, timeouts |
| Agent providers | `core/services/ai_providers.py`, `core/services/agent_service.py`, `integrations/agent_runner/` | Optional household AI providers; isolated CLI adapters |
| Database | SQLite (dev) / PostgreSQL (prod) | Users, tracking, tasks |
| Frontend | React + Vite | Web UI |

## Core design

### Database session management

Services receive a SQLAlchemy `Session` per request via FastAPI dependency injection (`Depends(get_db)`). Sessions are not stored on service instances, which avoids connection leaks.

### Configuration

All environment variables are validated through `backend/config/settings.py` (`pydantic-settings`). Use `get_settings()` instead of raw `os.getenv()`.

### Dependency injection

A service container (`backend/dependencies/container.py`) manages singleton services. Routes resolve services through the container.

### Authentication and authorization

- JWT access + refresh tokens on `/api/auth/*`
- Protected routes use `Depends(get_current_user)`
- Resource access is checked with `check_user_authorization()` (user can only access their own data)
- Tracking POST, chat, crisis, tasks, and emotional check-in all require JWT

### Rate limiting

`backend/middleware/rate_limit.py` applies per-endpoint limits (chat, auth, tracking, tasks). Redis-backed limits are used when `REDIS_URL` is set.

### Async task flow

1. Client calls an API endpoint (e.g. `/api/chat`, `/api/tracking/{user_id}/summary`)
2. API creates a task and returns `202` with `task_id`
3. Worker processes the task and updates status in the database
4. Client polls `/api/tasks/{task_id}` or uses WebSocket subscription

### Worker processes

Workers live in the top-level `workers/` directory (outside `backend/`) to keep the backend folder lean. They import backend code via `workers/bootstrap.py`.

```bash
python workers/worker.py
```

### Agent providers and execution gateway

`AI_PROVIDER=codex|claude_code|agent` selects an optional `AgentRunnerProvider` behind the existing household `AIService`. It receives the same selected system/user/previous-answer messages and does not fetch extra records. Its result continues through the existing answer checks. Streaming aggregates a completed, checked answer before emitting one chunk. `AGENT_ENABLED` defaults to false. A call-local `ContextVar` binds the authenticated owner and request ID; workers derive a stable ID from the persisted task ID and do not automatically retry failures for these providers. No per-user state is placed on singleton service instances.

The shared gateway reserves `agent_runs` metadata before one bounded HTTP attempt to a fixed endpoint, including a unique active slot per account. Reused request IDs return conflict metadata, never another execution or output replay. Separate `/api/agents/*` routes remain admin-only and provide explicit operational calls and owner-scoped metadata queries; household users use the existing chat/task endpoints. Unknown results require operational reconciliation.

The optional CLI runner is deployed separately, with a fresh scratch home, application system instructions in a temporary private file, fixed CLI options, bounded streams, process-group cleanup and persistent SQLite reservations. Its network/filesystem isolation is an operator deployment requirement; it cannot mount application data or host credentials. API/worker containers do not install or invoke coding CLIs. Execution receipts omit text; existing family task storage still retains its questions and processed results. This revision adds a table to startup schema initialization; migration and runtime acceptance have not been executed. See [Agent contracts and rollout](integrations/AGENTS.md) and the [reference runner](../integrations/agent_runner/README.md).

### Localization

User-facing backend strings for EN/JA live in `locales/`. Python code loads them through `backend/utils/locale_loader.py`.

## Security

- Password hashing (pbkdf2_sha256)
- NSFW input filtering on chat and tracking notes
- Structured security logging
- No medical diagnosis claims — companion tool only

## Observability

- JSON structured logging (`backend/services/logging_service.py`)
- Performance middleware (`backend/middleware/performance.py`)
- Health checks: `/health`, `/api/monitoring/health`

## Scaling

- **API**: multiple instances behind a load balancer
- **Workers**: increase `NUM_WORKERS` or run multiple worker containers
- **Queue/ cache**: in-memory by default; Redis optional for distributed rate limits

## Related docs

- [Project structure](PROJECT_STRUCTURE.md)
- [Code organization](CODE_ORGANIZATION.md)
- [Deployment](deployment/DEPLOYMENT.md)
