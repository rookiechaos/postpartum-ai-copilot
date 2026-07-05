# Project Structure

This document describes the repository layout and organization conventions.

## Directory layout

```
Postpartum/
├── README.md                 # Main readme (English + Japanese)
├── LICENSE                   # Apache License 2.0
├── do-not-upload/            # Local-only (gitignored except README/.gitkeep)
├── docker-compose.yml
├── mypy.ini
│
├── backend/                  # FastAPI application (≤100 files target)
│   ├── main.py               # App entry point
│   ├── api/                  # Route modules by feature
│   ├── config/               # Settings
│   ├── dependencies/         # DI container, DB session
│   ├── middleware/           # Auth, rate limit, errors
│   ├── models/               # SQLAlchemy + Pydantic schemas
│   ├── services/             # Business logic
│   └── utils/                # Shared helpers
│
├── workers/                  # Background workers (outside backend/)
│   ├── worker.py             # AI worker entry point
│   ├── ai_worker.py
│   └── notification_worker.py
│
├── frontend/                 # React web app
│   └── src/
│       ├── components/
│       ├── utils/
│       └── i18n/
│
├── tests/                    # All test code
│   ├── unit/                 # pytest unit tests
│   ├── integration/          # API / worker integration scripts
│   ├── internal/             # Internal improvement tests
│   ├── pytest.ini
│   └── run_tests.py
│
├── locales/                  # Backend EN/JA user-facing strings
│   ├── en/
│   └── ja/
│
├── docs/                     # All project documentation
│   ├── ARCHITECTURE.md
│   ├── PROJECT_STRUCTURE.md  # This file
│   ├── CODE_ORGANIZATION.md
│   ├── backend/              # Backend-specific docs
│   ├── deployment/
│   ├── features/
│   ├── security/
│   └── testing/
│
└── mobile/                   # React Native (in progress)
```

## Organization principles

### Code vs documentation

- **Code**: `.py`, `.jsx`, `.ts`, config files stay in their runtime directories
- **Documentation**: all `.md` files under `docs/` (except root `README.md` and `CONTRIBUTING.md`)

### Backend size limit

`backend/` is capped at **100 files** (excluding `__pycache__`). Tests, docs, locales, and workers were moved out to stay under this limit.

### Workers

Workers import backend modules through `workers/bootstrap.py`, which adds `backend/` to `sys.path`. Run from the repo root:

```bash
python workers/worker.py
```

### Tests

| Directory | Purpose |
|-----------|---------|
| `tests/unit/` | Fast pytest tests with `conftest.py` |
| `tests/integration/` | Scripts that may hit a running server |
| `tests/internal/` | Internal regression / improvement checks |

Use `tests/bootstrap.py` or the `_BACKEND` path snippet to import backend code from tests.

## Naming conventions

| Type | Convention |
|------|------------|
| Python modules | `snake_case.py` |
| React components | `PascalCase.jsx` |
| JS utilities | `camelCase.js` |
| Docs | `UPPER_SNAKE_CASE.md` or descriptive names |

## Related links

- [Architecture](ARCHITECTURE.md)
- [Code organization](CODE_ORGANIZATION.md)
- [Backend docs](backend/README.md)
- [Docs index](README.md)
