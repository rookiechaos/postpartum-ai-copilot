# Contributing

Thank you for your interest in Postpartum AI Copilot.

## License

By contributing, you agree that your contributions will be licensed under the
[Apache License 2.0](LICENSE).

## Development setup

1. Clone the repository
2. Copy `backend/env.example` to `do-not-upload/local/backend.env` (or `backend/.env` locally)
3. Install backend dependencies: `pip install -r backend/requirements.txt`
4. Install frontend dependencies: `cd frontend && npm install`
5. Run tests: `python tests/run_tests.py`

See [docs/deployment/SETUP.md](docs/deployment/SETUP.md) for details.

## Pull requests

1. Keep changes focused and well-scoped
2. Match existing code style and conventions
3. Do not commit secrets, logs, databases, or files under `do-not-upload/` (except `.gitkeep` markers)
4. Update documentation when behavior or paths change

## What not to commit

Never commit:

- API keys or `.env` files with real secrets
- `do-not-upload/` runtime data (logs, SQLite files, vector DB)
- `node_modules/`, `venv/`, or `__pycache__/`

See [do-not-upload/README.md](do-not-upload/README.md).
