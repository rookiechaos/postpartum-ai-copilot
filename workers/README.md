# Workers

Background processes that poll the task queue and run AI workloads outside the FastAPI server.

## Entry points

| Script | Purpose |
|--------|---------|
| `worker.py` | Start one or more AI workers (`NUM_WORKERS` from settings) |
| `ai_worker.py` | AI task processor (imported by `worker.py`) |
| `notification_worker.py` | Send pending notifications (optional separate process) |

## Run locally

From the repository root (with backend dependencies installed and `.env` in `backend/`):

```bash
python workers/worker.py
```

Workers add `backend/` to `sys.path` via `bootstrap.py` and load `backend/.env`.

## Docker

The `worker` service in `docker-compose.yml` mounts `./backend` and `./workers` and runs `python /workers/worker.py`.

## Task types

- `ai_chat`
- `tracking_analysis`
- `personalized_chat`
