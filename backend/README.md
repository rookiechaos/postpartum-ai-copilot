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
| `pilot_routes` | Public `/api/pilot`; separately authorized `/api/pilot/organization` |
| `community_routes` | `/api/community` |
| `family_routes` | `/api/families` |
| `notification_routes` | `/api/notifications` |
| `monitoring_routes` | health, metrics |
| Others | feedback, help, payment, voice, analytics, … |

See `main.py` for the full router registration list.

## Japan small-pilot directory

`GET /api/pilot` exposes only the deployment's public organization profile and local resources.
`GET` / `POST /api/pilot/organization` require a current active account whose server-generated ID is listed in `INSTITUTION_USER_IDS`.
This allowlist is independent of `ADMIN_USER_IDS` and does not bypass the owner checks on private APIs.

The new `pilot_profiles` table stores one public directory per deployment; it contains no family records or memberships.
The existing database initialization creates this table without altering existing tables.
Source links require HTTPS without embedded credentials. Checked dates cannot be in the future, and each directory has at most ten resources.

See the [main README](../README.md) for environment setup and staff provisioning, and the [pilot guide](../docs/product/JAPAN_PILOT.md) for scope and acceptance scenarios.
