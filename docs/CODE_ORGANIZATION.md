# Code Organization

Last updated: 2026-07-04

## Goals

1. Separate application code from documentation
2. Keep each top-level folder at **≤100 files**
3. Keep Python source **English-only**; user-facing EN/JA strings in `locales/`

## What moved where

| From | To | Reason |
|------|-----|--------|
| `backend/docs/` | `docs/backend/` | Docs out of code tree |
| `backend/tests/`, `backend/test_*_internal.py` | `tests/` | Centralized testing |
| `backend/locales/` | `locales/` | Shared locale assets |
| `backend/workers/` | `workers/` | Reduce backend file count |
| `backend/services/` | `core/services/` | Split API layer from domain logic |
| Root `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`, etc. | `docs/` | Cleaner repo root |
| Root `test_*.py`, `stress_test.py` | `tests/integration/` | Test consolidation |
| Local runtime / private files | `do-not-upload/` | Secrets, DB, logs (gitignored) |

## Current layout

```
backend/     API, models, middleware, config (~56 files)
core/        services/ — business logic (~40 files)
workers/     AI + notification workers
tests/       unit, integration, internal
locales/     en/ and ja/ JSON + text
docs/        all markdown documentation
frontend/    React app
mobile/      React Native scaffold
```

## Backend (`backend/`)

HTTP/API layer only (target: ≤100 files):

- `api/` — FastAPI routers (one module per feature area)
- `models/` — SQLAlchemy models + Pydantic schemas
- `middleware/` — auth, rate limits, error handling
- `dependencies/` — DB session + service container
- `config/` — settings
- `utils/` — helpers (e.g. `locale_loader.py`)
- `main.py` — app entry (adds `core/` to `sys.path`)

## Core (`core/`)

Domain / business logic:

- `services/` — AI, tracking, auth, community, analytics, etc.

Imports stay `from services.X import ...` when `core/` is on `PYTHONPATH` (handled by `main.py`, workers, and tests).

## Documentation (`docs/`)

| Subfolder | Contents |
|-----------|----------|
| `docs/backend/development/` | Code quality, design reviews |
| `docs/backend/features/` | Feature specs (AI, personalization, etc.) |
| `docs/backend/security/` | Security and NSFW docs |
| `docs/backend/testing/` | Backend test reports |
| `docs/deployment/` | Setup and deployment |
| `docs/features/` | Product-level feature docs |
| `docs/security/` | Project security reports |
| `docs/testing/` | Test guides and reports |

## Locales (`locales/`)

JSON and text files for runtime i18n loaded by `backend/utils/locale_loader.py`:

```
locales/
├── en/
└── ja/
```

## Workers (`workers/`)

- `worker.py` — starts one or more `AIWorker` instances
- `ai_worker.py` — processes `ai_chat`, `tracking_analysis`, `personalized_chat`
- `notification_worker.py` — sends pending notifications
- `bootstrap.py` — adds `backend/` to `sys.path`

## Tests (`tests/`)

- `tests/unit/conftest.py` — pytest fixtures; adds `backend/` to path
- `tests/bootstrap.py` — shared path setup
- `tests/pytest.ini` — pytest config

Run unit tests:

```bash
python tests/run_tests.py
# or
python -m pytest tests/unit -c tests/pytest.ini
```

## do-not-upload/

Local-only files that must not be pushed to GitHub:

```
do-not-upload/
├── local/backend.env    # Secrets (copy from backend/env.example)
├── data/                # SQLite databases
├── logs/                # Application logs
├── vector_db/           # RAG vector store
├── private-docs/        # Internal planning materials
└── scripts/             # Machine-specific helper scripts
```

See [do-not-upload/README.md](../do-not-upload/README.md) and [GITHUB.md](GITHUB.md).

## Conventions

1. Do not add `.md` files under `backend/` or `frontend/src/`
2. Prefer extending existing services/routes over new top-level packages
3. Before adding files to `backend/`, check count: `find backend -type f ! -path '*/__pycache__/*' | wc -l`
4. User-facing copy belongs in `locales/` or `frontend/src/i18n/`, not hardcoded in Python

## Related docs

- [Project structure](PROJECT_STRUCTURE.md)
- [Architecture](ARCHITECTURE.md)
- [Backend docs index](backend/README.md)
