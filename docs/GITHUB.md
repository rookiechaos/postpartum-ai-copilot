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

This read-only scan checks publishable working files, staged Git blobs, reachable
local/remote branches and tags, and commit author/committer/message metadata for:

- Home directory paths (`/Users/...`, `/home/...`)
- Real API key patterns (`sk-...`)
- Personal email domains
- Real IP addresses and credential-bearing connection URLs (development bind/loopback and reserved example addresses are allowed)
- Accidental staging of `do-not-upload/local/backend.env`, logs, databases, or private docs

Matched values are withheld from the report. Ignored runtime files, unreachable
Git objects and copies retained elsewhere are outside this check's scope. A clean
file tree alone does not mean historical commit metadata is clean.

Before committing, set this repository's identity to the GitHub-provided noreply
email from your GitHub email settings, then inspect the staged files:

```bash
git config --local user.email YOUR_GITHUB_NOREPLY_EMAIL
git diff --cached --check
git diff --cached --stat
```

Use ordinary pushes for new commits. Cleaning private metadata already published
in history changes commit IDs and requires a separately approved history rewrite
and an explicit remote-head lease. Preserve every commit's file tree, and review
and scan the prepared candidate before publishing it.

## Updating copyright

To add your name to the license header, edit the `Copyright` line in [LICENSE](../LICENSE):

```
Copyright 2026 Your Name
```

You may also add a [NOTICE](../NOTICE) file for additional attribution if needed.
