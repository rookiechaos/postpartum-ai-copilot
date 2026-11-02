# Isolated Codex / Claude Code runner

This optional service implements `POST /v1/execute` for the family AI provider's `postpartum.agent.v1` gateway. It receives the application's system instructions and the text conversation approved for this request, and returns answer text to the existing AI service for normal validation and presentation. It is separate operator infrastructure: never import it into the care API or run its CLI children on an application/database host. One image serves one configured backend, `codex` or `claude_code`. Families do not operate a CLI or supply provider credentials.

## Deployment contract

- Build with an explicit reviewed `AGENT_BACKEND` and exact published `CLI_VERSION`; no default or `latest` version is selected. The build context is this directory only. No build or execution was performed as part of this change.
- This service has independent Python dependency pins, checked against the published [FastAPI](https://pypi.org/project/fastapi/0.162.0/), [Uvicorn](https://pypi.org/project/uvicorn/0.54.0/) and [Pydantic](https://pypi.org/project/pydantic/2.14.2/) releases on 2026-11-01. They do not upgrade the main application's dependencies. Installation, resolution and runtime compatibility remain unverified.
- Supply a random `AGENT_RUNNER_TOKEN` of at least 32 characters and only the selected provider credential (`CODEX_API_KEY` or `ANTHROPIC_API_KEY`). An optional `AGENT_RUNNER_MODEL` is configured by the operator. Request bodies cannot choose binaries, models, arguments, paths, environment variables, plugins, or tools.
- Use a separate non-root Linux container/host with a read-only root filesystem, a bounded writable `/tmp`, a durable private volume at `/var/lib/agent-runner`, dropped capabilities, `no-new-privileges`, process/memory/CPU limits, and ingress restricted to the API gateway. Do not expose this port publicly or mount the repository, application data, database, credentials directories, container runtime socket, or host home.
- Enforce an outbound firewall/proxy allowlist for the chosen provider. The process must not reach the care API, database, internal services, cloud metadata, or arbitrary external destinations. The Dockerfile does not itself implement this network policy. Restrict any provider credentials to the runner's own account/project and usage budget.
- Outside the container, startup additionally requires `AGENT_RUNNER_ISOLATED=true`, a non-root Linux user, an absolute `AGENT_RUNNER_STATE_PATH` with an existing private parent directory, the selected binary at `/usr/local/bin/codex` or `/usr/local/bin/claude`, token, and provider key. The flag asserts operator-supplied isolation; it does not create a sandbox.
- Keep stdout/stderr and body capture disabled in reverse proxies/APM. The supplied server command disables access logging and routine application logging. Protect and rotate the token through infrastructure secrets, never repository files.

The service's SQLite file retains only request ID, backend, status, and timestamps. A reservation is committed before launching a process, and a duplicate ID receives HTTP 409 without re-execution, including after restart. It retains no prompt, answer, CLI session ID, stderr, or credential in its durable state. The temporary system file described below is removed after process cleanup. Do not delete reservations while callers may still repeat those IDs; the reference implementation deliberately has no automatic pruning. Persistent storage is required for restart-safe duplicate protection.

## Wire format

The authenticated request uses `Authorization: Bearer <runner token>` and exactly these fields:

```json
{
  "protocol": "postpartum.agent.v1",
  "request_id": "00000000-0000-4000-8000-000000000001",
  "backend": "codex",
  "prompt": "An explicitly approved text question",
  "instructions": "Application-provided text instructions",
  "timeout_seconds": 90,
  "max_output_chars": 8000
}
```

`prompt` permits 1–64,000 characters, `instructions` at most 16,000, timeout 1–300 seconds, and output 1–20,000 characters. Unknown fields, invalid types, and text that cannot be encoded as valid UTF-8 are rejected. The total request body is bounded to 1 MiB and captured output streams are also byte bounded. Success returns the matching protocol, request ID, backend, `status: "completed"`, and `output`. Other results have `status: "failed"` or `"unknown"` and an `error.code`, without output or private diagnostics. A timeout/disconnection/oversized output does not trigger another CLI call. Busy requests receive HTTP 429; duplicates receive 409. `GET /health` exposes only readiness and protocol.

Each accepted call has a fresh scratch directory/home and an allowlisted environment. Only conversation text goes to stdin; no family text appears in process arguments. The system instructions are written to a new `0600` file inside this call's private scratch directory, alongside a fixed text-only/no-tools policy. This file replaces the CLI's default coding identity. Empty instructions select a restricted postpartum text-support default. The system file remains until the process stops and the whole scratch directory is removed; deploy `/tmp` as bounded tmpfs so this temporary content is not written to a persistent disk. The CLI receives only the generated system-file path, never a caller-selected path. No host or application files are opened. Linux process groups are killed and reaped on timeout, cancellation, disconnect, or capture limit. Run exactly one service instance and one Uvicorn worker with its durable volume. Horizontal replicas with separate SQLite files would lose global duplicate protection and are unsupported by this reference implementation.

## CLI capability limits

Claude Code uses `--bare`, `--tools ""`, MCP denial, `--no-session-persistence`, `--system-prompt-file`, JSON output and a one-turn limit. The official system-prompt flags work in non-interactive mode and replace the default prompt; bare mode does not prevent explicit system-file input. It does not load host OAuth/keychain credentials. Nonessential traffic and official marketplace auto-install are disabled through explicit environment settings. The parser checks the result type, success subtype, `is_error`, API error status, stop reason and process exit code before accepting answer text.

Codex uses strict configuration validation, ignored user configuration/rules, ephemeral sessions, a read-only sandbox, disabled shell/multi-agent/web search/analytics/feedback, API-key authentication, JSONL and no history persistence. `--strict-config` rejects unrecognized configuration fields instead of silently ignoring requested restrictions. Its `model_instructions_file` points to the generated scratch system file and replaces the built-in instructions; the generated path is quoted as a TOML string, not interpolated as a command. These flags do **not** establish that every Codex tool is unavailable. Filesystem and network isolation remain mandatory. No host configuration or private files may be visible inside the runner. The parser requires a completed turn, a final agent message and a successful exit, and rejects error events. Answers containing the exact runner token or provider key are rejected as an extra safeguard; this cannot detect every encoding or substitute for isolation. Pin and manually qualify a CLI version supporting all flags before deployment; a version rejecting them fails rather than falling back to broader permissions.

Official contracts: [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [Codex developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli), [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference), [Claude Code headless mode](https://code.claude.com/docs/en/headless), [Claude CLI reference](https://code.claude.com/docs/en/cli-reference), [Claude result message](https://code.claude.com/docs/en/agent-sdk/typescript#sdkresultmessage), [Claude environment controls](https://code.claude.com/docs/en/env-vars).

## Source review and manual acceptance

No image build, dependency install, CLI invocation, application run, or test was performed. Before enabling this opt-in integration, qualify the pinned binary in an isolated staging deployment with synthetic text: success; invalid credentials; malformed output; timeout/disconnect; stream overflow; provider failure; same-ID duplicate after restart; unsupported CLI flag; denied filesystem/network access; and inspection confirming no prompt/output or keys in service, proxy, CLI persistence, or telemetry logs. Do not use family data for this acceptance pass.
