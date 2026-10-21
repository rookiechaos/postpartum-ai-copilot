# Whole-repository review fixes — 2026-10-20

All seven review findings have source changes. Application/worker startup, dependency installation, builds, tests, parser/lint/compile checks, Compose validation, database initialization/migration and browser acceptance have **not been executed**. Updated regression source is for a later authorized verification session, not evidence of passed tests.

## Session revocation

`users.session_revision` starts at 1. Both access and refresh tokens require a positive integer claim matching the active account's current value. Missing claims are rejected deliberately, including existing pre-upgrade tokens. HTTP authorization, refresh, worker token helpers and WebSocket session revalidation use the database check.

Two-factor setup, verification, enabling and disabling acquire the account lock before the factor lock. Actual enable/disable transitions increment the account revision in the same transaction as the factor change. Setup alone does not invalidate the setup session. Repeated enable/disable requests never reset or decrease the revision. A login captures its revision before factor verification and does not adopt a later revision after another operation changes the factors. Refresh preserves the verified revision.

**All existing users must sign in again after this upgrade.** Existing two-factor secrets and backup codes are retained. This is session revocation, not a password reset, account deletion or historical credential rotation.

## Account-status lookup and request logs

`POST /api/pilot/account-help/status` accepts only `{ "reference": "<UUID>" }`. The random reference still grants access to the limited public status/reply, so it must be kept private. The old `GET /api/pilot/account-help/{reference}` returns 410 and never returns a reply. No contact email/account lookup is introduced.

Performance metrics, API request logs, slow-request metadata and rate-limit metadata use the declared route template, or a fixed unmatched label. Uvicorn access logs omit the concrete path/query and client address; application metadata supplies the useful route template. The logging filter also redacts legacy account-reference paths and token/reference query values from Uvicorn/application messages and arguments. Exception output retains type and code locations without private exception text. Requests/bodies are not logged by the new lookup.

These changes do not erase existing application, container, reverse-proxy or monitoring history. Operators must review access/retention under their controlled privacy procedure, including retained account-reference URLs. Configure external proxies/APM not to capture these credentials or request bodies. Do not publish a log archive as verification evidence.

## One-baby analysis

Charts and both synchronous/asynchronous AI analysis select either one accessible `subject_id` or `unassigned=true`. AI analysis with omitted scope defaults to unassigned records only, including legacy queued jobs. Explicit `unassigned=false` without a subject, conflicting scope choices and inaccessible subjects are rejected. Generic task creation validates the same scope and the worker rechecks access immediately before reading records.

The read filters the authenticated owner's baby records before chart aggregation or AI field selection. It does not combine other caregivers' records. Own mood/recovery rows remain separate adult records; AI includes those rows and free text only through their existing opt-ins. AI still excludes subject identifiers/nicknames. Account-level baby age and feeding preferences are not linked to a subject and are excluded from analysis context; the adult's selected birth/sleep fields remain optional. Chat's separate profile selection is unchanged.

The general owner record list and backups retain all own records. The optional scoped tracking GET accepts `subject_id` or `unassigned=true` for the chart, while an unscoped owner read remains the full private list. A chart read failure clears its previous data and offers retry.

## Staff review conflicts

An internal review form captures its task revision on the first input, date change, public-edit action or explicit attestation. Saving another part of the workspace may refresh task props, but it cannot replace that captured revision. A mismatch preserves the local input, shows the currently saved task and blocks saving that form until the staff member explicitly discards its internal input/confirmation. Public directory edits remain in the main editor. The normal whole-workspace reload, after its existing unsaved-work confirmation, remounts the review queue and clears local review forms.

Workspace and task compare-and-swap checks and atomic review/draft writes remain in place. Preview and publication remain separate explicit actions.

## Correcting a rejected timer save

A pending timer offers an explicit result lookup before correction. If the operation exists, the UI resolves an exact matching first revision or points to the existing changed record. A deleted operation remains a conflict and is not recreated. If no receipt is found at that moment, the user may correct attribution or other input while retaining start/end times and the **same original request key**, then confirm again.

A negative lookup is not proof that an earlier request cannot finish later. Keeping the key lets the durable receipt reject conflicting content instead of creating a second record in that race. The correction state and original key participate in optional server-draft recovery; recovery never restores the final save confirmation. No lookup saves or deletes a record automatically.

## Coordinated upgrade

1. In a later authorized deployment, retain backups and stop old worker consumers before upgrading. Do not drop the existing database volume.
2. Deploy matching frontend, API and worker sources. The existing serialized migration adds `users.session_revision INTEGER NOT NULL DEFAULT 1`; it preserves care records and prior tracking receipts.
3. Compose starts healthy PostgreSQL, runs the one-shot `migrate` service, then starts the API after successful completion. Workers depend on migration completion and the API HTTP health check. Failure keeps new consumers from starting. API startup retains its idempotent initialization for direct/local deployment.
4. A directly started worker waits on a read-only table/column/identity-index check before RAG initialization, timeout processing or claiming tasks. It never runs a migration or consumes task retries while waiting for the schema. Operators must investigate a worker that keeps waiting; it will not repair the schema automatically.
5. `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`, `CLAUDE_MODEL` and `GEMINI_MODEL` are explicitly forwarded through the shared Compose backend environment. Overrides come from the ignored interpolation file or operator shell. The host environment file is not mounted by `--env-file`; omitted values retain Settings defaults.
6. Have users sign in again. Explain the new analysis target choice and update clients using the retired account-status URL. Review historical logs separately through the operator's retention procedure.

Compose dependencies govern startup order; they do not suspend an already running old worker during an upgrade. No deployment, database change, source indexing or account operation was executed during this edit.

## Pending acceptance after execution is authorized

- SQLite/PostgreSQL upgrade and repeated startup; both token types across enable/disable/re-enable, missing/bad revisions, concurrent logins, backup-code use, refresh and existing/idle WebSocket sessions.
- Synthetic request references/tokens must be absent from application, Uvicorn, metric and external proxy/APM outputs. The legacy GET must reveal no status. The new body-only lookup must retain rate limits, no-store behavior and generic not-found responses.
- Two baby subjects, unassigned records and own parent records across charts, synchronous summaries, generic queued analysis, legacy tasks and access revocation. Inspect actual provider payloads only with synthetic data and confirm subject/profile/notes exclusions.
- Two staff editors; editing an internal form, then saving another task/public draft; conflict preservation, explicit local discard and whole-workspace reload. Confirm the original revision is submitted rather than a refreshed prop revision.
- Timer attribution/sharing rejection; start/end retained during correction; delayed original save after negative lookup; differing existing receipt, edited/deleted record, retry, duplicate-review cancel and optional draft recovery. At most one record may be created for the original key.
- Fresh and retained databases in Compose; nondefault model overrides present in API/worker; failed/delayed migration; direct worker started before migration. No task may be claimed before schema readiness, and upgrade waiting must not increment retry counts.

None of these acceptance checks has been executed for this source revision.
