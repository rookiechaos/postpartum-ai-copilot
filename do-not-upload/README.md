# do-not-upload

**This folder holds local-only files that must not be pushed to GitHub.**

Everything here is listed in `.gitignore`, except this README, `.gitkeep` placeholder files, and the public `local/backend.env.example` template.

## Layout

| Path | Purpose |
|------|---------|
| `local/backend.env` | Your real secrets (copy from `local/backend.env.example`) |
| `local/frontend.env` | Optional frontend env overrides |
| `data/` | SQLite databases and exports |
| `logs/` | Application log files |
| `vector_db/` | RAG / Chroma vector store |
| `private-docs/` | Internal planning or promotion materials |
| `scripts/` | Personal or machine-specific helper scripts |

## First-time setup

```bash
# Backend secrets (recommended location)
cp do-not-upload/local/backend.env.example do-not-upload/local/backend.env
# Edit do-not-upload/local/backend.env with your API keys

# Optional: symlink for tools that expect backend/.env
ln -sf ../do-not-upload/local/backend.env backend/.env
```

Default development storage lives under the project root, regardless of the process working directory:

- Database: `do-not-upload/data/postpartum.db`
- Logs: `do-not-upload/logs/`
- Vector DB: `do-not-upload/vector_db/`

## GitHub

The repository `.gitignore` excludes private contents of this folder. Before pushing, verify:

```bash
git status
# Should NOT list do-not-upload/local/, logs, *.db, or .env
```
