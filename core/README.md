# Core — business logic and services

Domain services live here, separate from the HTTP/API layer in `backend/`.

## Layout

```
core/
└── services/    # Business logic (AI, tracking, auth, community, …)
```

## Imports

With `core/` on `PYTHONPATH`, imports match the API layer:

```python
from services.ai_service import AIService
from services.tracking_service import TrackingService
```

Path setup is handled by:

- `bootstrap.py` at the repo root (workers, scripts)
- `tests/bootstrap.py` (tests)
- `PYTHONPATH=../core:.` when running from `backend/`

## Why split?

Keeps `backend/` under the 100-file limit and separates HTTP routing from domain logic.
