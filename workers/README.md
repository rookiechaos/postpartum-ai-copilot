# Workers

Background processes that poll the task queue and run AI workloads outside the FastAPI server.

## Entry points

| Script | Purpose |
|--------|---------|
| `worker.py` | Start one or more AI workers (`NUM_WORKERS` from settings) |
| `ai_worker.py` | AI task processor (imported by `worker.py`) |
| `notification_worker.py` | Retired compatibility entry point; exits without sending or completing reminders |

## Run locally

From the repository root (with backend dependencies installed and `.env` in `backend/`):

```bash
python workers/worker.py
```

Workers add `core/` and `backend/` to `sys.path` via `bootstrap.py` and load `backend/.env`.

## Docker

The `worker` service in `docker-compose.yml` mounts backend/core/worker source and runs `python /app/workers/worker.py`.

Reminders use the existing account-bound database queue and authenticated browser polling. The family UI reports acceptance only after the browser notification API succeeds; reading due IDs does not mark them delivered. API and standalone worker socket tables are separate, so the legacy notification worker must not complete reminders. See [delivery contracts and pending acceptance](../docs/security/REPO_REVIEW_FIXES_2026-10-16.md). Closed/offline/background delivery is not guaranteed. No worker was started for this revision.

## Task types

- `ai_chat`
- `tracking_analysis`
- `personalized_chat`
