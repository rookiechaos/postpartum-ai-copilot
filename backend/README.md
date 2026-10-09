# Backend — HTTP / API layer

FastAPI application entry point and routing. Business logic lives in [`../core/`](../core/README.md).

## Layout (~56 files)

| Folder | Files | Purpose |
|--------|------:|---------|
| `api/` | 26 | Route handlers (chat, auth, tracking, community, …) |
| `middleware/` | 8 | JWT auth, rate limits, CORS, errors |
| `models/` | 6 | SQLAlchemy + Pydantic schemas |
| `utils/` | 5 | Locale loader, DB helpers |
| `dependencies/` | 3 | DI container, DB session |
| `config/` | 2 | Settings (`pydantic-settings`) |
| root | 6 | `main.py`, `exceptions.py`, Docker, deps |

## Run locally

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

`main.py` adds `../core` to `sys.path` so `from services.X` imports work.

## API route map

| Module | Prefix / tags |
|--------|----------------|
| `chat_routes` | `/api/chat`, crisis, stream |
| `auth_routes` | `/api/auth` |
| `task_routes` | `/api/tasks` |
| `tracking_routes` | `/api/tracking`, emotional check-in |
| `personalization_routes` | `/api/user`, personalization |
| `community_routes` | `/api/community` |
| `family_routes` | `/api/family` |
| `notification_routes` | `/api/notifications` |
| `monitoring_routes` | health, metrics |
| Others | feedback, help, payment, voice, analytics, … |

See `main.py` for the full router registration list.
