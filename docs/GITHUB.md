# Publishing to GitHub

Checklist before pushing this repository to GitHub.

## License

This project is licensed under **Apache License 2.0**. The full text is in [LICENSE](../LICENSE) at the repository root.

## What gets committed

| Included | Excluded (via `.gitignore` or `do-not-upload/`) |
|----------|--------------------------------------------------|
| Application source (`backend/`, `frontend/`, `workers/`) | `do-not-upload/local/backend.env` (secrets) |
| Tests, docs, locales | `do-not-upload/data/*.db` |
| `backend/env.example` (placeholders only) | `do-not-upload/logs/`, `do-not-upload/vector_db/` |
| `do-not-upload/README.md`, `.gitkeep` markers | `node_modules/`, `venv/`, `__pycache__/` |
| | Private docs in `do-not-upload/private-docs/` |

## First-time setup (local)

```bash
mkdir -p do-not-upload/{local,data,logs,vector_db}
cp backend/env.example do-not-upload/local/backend.env
# Edit do-not-upload/local/backend.env — add real API keys
```

## Initialize and push

```bash
cd /path/to/Postpartum

git init
git add .
git status
```

Review `git status` carefully. You must **not** see:

- `.env` or `backend.env` with real keys
- `*.db` files
- `do-not-upload/logs/*.log`
- `node_modules/`

Then:

```bash
git commit -m "Initial commit: Postpartum AI Copilot (Apache-2.0)"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

## GitHub repository settings (recommended)

1. **Description**: AI companion for postpartum support (EN/JA)
2. **License**: Apache License 2.0 (GitHub detects `LICENSE` automatically)
3. **Topics**: `postpartum`, `fastapi`, `react`, `ai`, `healthcare-companion`
4. **Branch protection** on `main` (optional): require PR reviews

## Docker note

`docker-compose.yml` expects environment variables from your shell or a local `.env` file at the project root (also gitignored). Do not commit production credentials.

## Privacy check before push

```bash
./check-privacy.sh
```

This scans **git-tracked files** for:

- Home directory paths (`/Users/...`, `/home/...`)
- Real API key patterns (`sk-...`)
- Personal email domains
- Accidental staging of `do-not-upload/local/backend.env`, logs, databases, or private docs

## Updating copyright

To add your name to the license header, edit the `Copyright` line in [LICENSE](../LICENSE):

```
Copyright 2026 Your Name
```

You may also add a [NOTICE](../NOTICE) file for additional attribution if needed.
