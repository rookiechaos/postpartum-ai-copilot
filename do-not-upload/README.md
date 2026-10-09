# do-not-upload

**This folder holds local-only files that must not be pushed to GitHub.**

Everything here is listed in `.gitignore`, except this README and `.gitkeep` placeholder files (so empty directories exist after clone).

## Layout

| Path | Purpose |
|------|---------|
| `local/backend.env` | Your real secrets (copy from `backend/env.example`) |
| `local/frontend.env` | Optional frontend env overrides |
| `data/` | SQLite databases and exports |
| `logs/` | Application log files |
| `vector_db/` | RAG / Chroma vector store |
| `private-docs/` | Internal planning or promotion materials |
| `scripts/` | Personal or machine-specific helper scripts |

## First-time setup

```bash
# Backend secrets (recommended location)
cp backend/env.example do-not-upload/local/backend.env
# Edit do-not-upload/local/backend.env with your API keys

# Optional: symlink for tools that expect backend/.env
ln -sf ../do-not-upload/local/backend.env backend/.env
```

Default dev paths (when running from `backend/`):

- Database: `../do-not-upload/data/postpartum.db`
- Logs: `../do-not-upload/logs/`
- Vector DB: `../do-not-upload/vector_db/`

## GitHub

The repository `.gitignore` excludes all contents of this folder except markers and this README. Before pushing, verify:

```bash
git status
# Should NOT list do-not-upload/local/, logs, *.db, or .env
```
