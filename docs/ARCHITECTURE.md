# Architecture

Postpartum AI Copilot uses a server-client architecture with an async task queue for long-running AI workloads.

## Overview

| Component | Role | Technology |
|-----------|------|------------|
| API server | HTTP endpoints, auth, task submission | FastAPI |
| Workers | Poll queue, run AI/tracking tasks | Python asyncio (`workers/`) |
| Task queue | Priority queue, retries, timeouts | SQL-backed custom queue |
| Database | Users, tracking, tasks | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Web UI | React + Vite |

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
