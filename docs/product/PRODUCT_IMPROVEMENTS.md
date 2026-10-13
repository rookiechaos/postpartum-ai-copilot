# Family and institution product improvements

This change implements the seven-item product review for a small Japanese pilot. It is **source-only work**: the user requested no application execution or testing. Dependencies were not installed; no server, worker, build, tests, scanner, browser, QR generation or print dialog was run. The behavior below describes the implementation and intended acceptance criteria, not observed runtime results.

The next product-polish phase is documented in [PRODUCT_POLISH.md](PRODUCT_POLISH.md). It adds quick saves, explicit follow-up context, optional account draft recovery, phone scripts, staff draft/history management and granular family handoff. Its contracts supersede the session-only recovery and screen-only institution draft limits in the original table below. Both phases remain unverified at runtime.

| Review item | Source changes | Practical limits |
| --- | --- | --- |
| Backdate and correct records | JST date/time choice, owned-record replacement and deletion, large choices, folded notes, 8-second undo | Changing record type clears incompatible fields and retains time/general notes until save. Writes accept today and the previous 364 Japan calendar days. Immutable identity and revision checks reject stale changes/deletions. Undo creates a fresh identity with the original time/content. Reloading, leaving the family entrance or signing out removes this snapshot. Lists cover up to 365 days. |
| Continue across pages | Visited family panels remain mounted; drafts, answers, in-flight requests and retries remain in the current session; record views and public contacts refresh on return | Screen memory does not survive reloads or entrance changes. Previous visible chat is not automatically included in the next AI prompt. Saved records remain on the server. |
| Simple Japanese settings | Profile, data/privacy, display and help; statistics moved to `/operator`; Japanese help/install/security flows | Font size, contrast and motion settings are device preferences. Unimplemented profile notification/dark-mode switches were removed. Advanced notification settings manage permission and existing schedules; automatic feeding-time suggestions are not exposed. |
| Account and privacy support | Operator/provider information before registration and in settings, explicit AI attachments, manual request receipts and status lookup | No automatic email, password-reset link or account-erasure executor. A responsible operator must verify identity and perform the requested action through a controlled process. |
| Usable human support | Area, audience, hours, cost conditions, phone, booking/source links, real review dates; human-help directory in chat | One shared directory per deployment. Dates older than 30 days or missing are flagged; they do not establish present availability. The app does not contact staff automatically. |
| Consultation sheet | 3/7/14/30-day ranges, three questions, recorded counts/sleep/coverage, optional latest five details, reviewed text/print/PDF | Changes to records/options preserve the draft and block exporting stale text. Regeneration offers a separate updated candidate when manual edits exist. Accepting it retains prior edits for copying, outside the print/download content. Missing data means unknown. Parent records and notes require opt-in. Browser print settings and long edits may produce multiple pages. |
| Institution maintenance | Name/area templates, publication preview, review-due/missing-fields list, public family QR and printable start guide | Entrance buttons and SPA Back/Forward share a discard confirmation; canceling preserves the draft. Reload/close uses the browser unload warning. Navigation is blocked during publication. QR is generated locally using `qrcode` 1.5.4, which is declared but not installed here. Templates never invent sources, eligibility, hours or review dates. |

## Entrances and permissions

- `/family`: the signed-in family's own records and requests. Owner checks remain on the server.
- `/organization`: editors listed in `INSTITUTION_USER_IDS` manage the public directory. This role grants no family-record access or support-queue access.
- `/operator`: accounts listed in `ADMIN_USER_IDS` handle the private support queue and operator statistics. Admin rights are broader than directory editing and should be restricted accordingly.

The public support route accepts a contact email without querying whether the account exists. A random UUID reference provides read access to status, dates, request type and the operator's public response only. The queue's emails, user IDs and last handler are visible only to administrators. Logged-in request creation binds the email and identity to the authenticated account; it accepts no target user ID.

The private queue supports an oldest-first, paginated status view. Completed/declined requests require a nonempty public explanation. The last updating operator ID is recorded for operations; this is not a full immutable audit history.
The shared rate-limit decorator now awaits async handlers and runs synchronous handlers in Starlette's thread pool, avoiding an unconditional await on a normal response for manual-support and directory-publishing routes. Production-mode limiting remains untested in this task.

## Public information to prepare

Publish the real responsible organization/operator, business contact and hours. Fill in these fields using the actual deployment's practices:

- `retention_notice`: storage location, retention period, backups and erasure handling.
- `ai_data_notice`: answer provider and any OpenAI content checking/reference search, what is sent, and the actual provider processing conditions.
- `account_support_notice`: who handles recovery/deletion/privacy requests, how to contact them, response expectations and identity verification method.

These are public business notices, not a place for private family records, staff credentials or verification documents. The app displays missing information as missing rather than asserting a default policy. No actual operator contact or real family data is embedded by this change.

`GET /api/pilot` exposes `ai_provider` and configured `ai_services` purposes. These describe configuration, not live service health or proof that every request used every listed service. Reference search may process a question with OpenAI even when a different answer provider is selected.

## Manual account-support procedure

This workflow records and communicates requests. It does not execute recovery or erasure. Before accepting real households, the operator needs a documented, controlled way to complete those actions.

1. Review `/operator` regularly and publish a realistic response time. There is no automatic staff/email alert. Mark a request as being checked and leave non-sensitive next steps.
2. Verify identity through the operator's established private channel. An unauthenticated email entry is unverified; an authenticated request alone is insufficient for sensitive changes. Never request passwords or identity documents in the reference-visible response.
3. For recovery, use a controlled credential-reset procedure and account for existing access/refresh tokens and open connections. This repository does not add a reset executor or a general session-revocation API. Do not mark the request complete merely because a password value was changed.
4. For erasure, stop account access and in-flight processing before removing data. Inventory the actual enabled features and stores. Deleting a `users` row does not imply cascade deletion of all personal data.
5. Record an accurate result, remaining retention obligations and a contact for follow-up. Only mark completed after the actual action and its checks are finished. Do not include private operational evidence in the public reply.
6. Follow the published retention policy for the request itself. If retaining a receipt after erasure, remove unnecessary email/user association and explain the remaining receipt retention. The app does not automatically enforce this policy.

The data inventory should cover, as applicable:

| Store | Examples requiring review |
| --- | --- |
| Main records | `users`, `user_context`, `tracking_entries` |
| AI work | `tasks.task_data`, `tasks.result`, queued/running jobs, provider-side retention |
| Account security | `two_factor_auth`, `devices`, `login_history`, active access/refresh tokens and connections |
| Support and feedback | `account_requests` including email and reply, `feedback`, `nps_surveys` |
| Family handoff and recovery | Family membership/ownership, `tracking_writes`, `draft_preferences`, `user_drafts` |
| Public information work | `directory_workspaces`, `directory_history` and any applicable account attribution |
| Optional legacy features | Subscriptions, onboarding, feature requests/votes, goals and achievements |
| Operational copies | Backups, logs, caches, exports already downloaded, external services actually enabled |

This inventory is an operational starting point, not an implemented deletion transaction or a claim that third-party/downloaded copies can be recalled. The later family handoff UI uses granular, default-off category/notes sharing; see PRODUCT_POLISH.md. Legacy family task features are not promoted into that UI.

## AI data selection contract

`core/services/ai_data_scope.py` applies allowlists before normal sync/async chat and record analysis calls.

- Chat/personalized chat: `include_profile=false` by default. When true, only baby age, birth/feeding method and average sleep fields are considered. Names, account IDs and arbitrary context/preferences are excluded.
- Follow-up: `include_previous=false` by default. A previewed, explicitly selected question/answer pair is bounded to 2,000/4,000 characters and validated in sync, worker, personalized and streaming paths. No hidden full conversation is attached.
- Record analysis: baby feeding/diaper/sleep/pumping fields by default. `include_parent`, `include_notes`, `include_profile` default false and are independent. Selecting notes does not implicitly select parent records.
- Analysis includes counts of all selected entries, then up to 50 recent details within an 8,000-character detail budget; each note field is limited to 500 characters. The prompt states how many details are included and the UI explains possible omission. Long Japanese prose is preserved once rather than duplicated into several analysis sections.
- Emotional check-in: the current selected values and current text are sent. `include_history=false` by default; the current AI prompt summarizes mood categories, not prior mood notes.
- Night concern: `include_profile=false` and `include_records=false` by default. The current UI offers profile attachment only.
- UI attachment changes clear the acknowledgement. Scope flags constrain data use; the acknowledgement is not a legal consent ledger.

Raw asynchronous task flags grant optional scope only when their value is boolean `true`; strings or omitted flags do not opt in. Existing task ownership checks use the authenticated task owner.

Legacy daily/weekly summary endpoints and optional feature APIs are not converted into this per-request selection flow. Do not advertise this as a blanket change to every API's privacy contract. Normal record saving, editing, deleting and non-AI consultation preparation do not invoke external AI.

## Database and dependency changes

`account_requests` is a new table created by the existing `init_db()`/`create_all()` startup mechanism when the application is later started. API initialization also runs the idempotent migration in `backend/utils/tracking_migrations.py`: existing tracking rows receive unique UUID identities and revision 1, with a unique identity index. SQLite/PostgreSQL locks serialize migration inspection and backfill. Care content and numeric IDs stay intact; existing records outside the new write-time window are not deleted. No database startup/migration was performed here. Back up the deployment and validate migration before real use; start workers after API initialization completes.

Tracking update bodies and delete query parameters now require `record_key` and `revision` from the read API. Missing preconditions are validation errors; a stale identity/revision is a 409; an absent owned record is a 404. Both mutations use an atomic identity/version predicate, so a reused SQLite numeric ID cannot target a different record. Successful updates increment the revision. New/undo records always receive a server-generated identity. There is no fallback that bypasses these checks for old clients.

Record creation and supplied correction timestamps are limited to today and the previous 364 Japan calendar days, aligned in the form and service. A one-minute future tolerance handles clock skew. This prevents accepting backdates beyond the 365-day list/backup window. Existing older records are retained, not made newly accessible by this change.

CSV backups use a complete field list independent of consultation summaries: all supported record fields, identity/revision, precise UTC timestamps and a readable JST column. Enum values stay as stored; zeros, sleep quality, feeding side and all note fields are retained. CSV uses a UTF-8 BOM, quoted cells and formula-prefix neutralization. JSON remains the raw-data backup. The current UI does not import either format.

`frontend/package.json` adds the exact `qrcode` dependency version `1.5.4`. Its browser `toDataURL` API is described by the [upstream documentation](https://github.com/soldair/node-qrcode). No install, dependency audit, bundle or generated QR artifact was executed in this task.

Print sheets are cloned from the reviewed DOM into a dedicated print root, using text rendering rather than HTML interpolation. Print roots are removed after printing and on an authentication change. CSS hides the rest of the application in print mode. No external PDF/QR service is used.

## Acceptance still to perform

All items below are pending a later authorized verification session. Existing fixtures that assert complete directory objects, translated labels or old component hook shapes may need updating for the additive fields and redesigned screens before interpreting their results.

1. With installed dependencies, run appropriate backend and frontend regressions, then build the frontend. Cover identity/revision migration on existing and fresh SQLite/PostgreSQL databases, repeat/concurrent API initialization, and retained care content. Reproduce stale update/delete after deleting the highest SQLite ID and inserting a different record, plus simultaneous updates and missing preconditions. Cover owner isolation and absent-record 404s, account-request permissions, reference privacy, pagination and explicit AI scope in both worker and sync paths. Exercise production-mode rate limiting and 429 responses. Re-run repository privacy checks before publication.
2. On a phone, record now and backdate across Japan midnight and the earliest allowed day. Confirm older/future times are rejected by the UI and write API. Enter a backdate and note, switch record types and use home shortcuts; time/general notes must remain while incompatible measurements clear. Edit every record type, delete/cancel/undo and let undo expire. Verify home/charts/consultation updates, return refresh and Japan-midnight counts. Simulate failed/conflicting saves and preserve editable input. Compare every schema field in CSV/JSON exports, including sleep quality, side, zeros, notes, quotes, Unicode and formula-like text.
3. Start a delayed/failed chat, switch between family pages and return. Confirm answers, drafts and progress remain, retry works, and edits/new scene drafts behave as intended. Sign out or change accounts in another tab; delayed results must never reappear for the new account.
4. Inspect actual outgoing AI payloads for each selection, default-off scope and failure behavior. Verify the configured-provider notice describes actual deployment settings without exposing credentials.
5. Submit recovery without login and deletion/privacy requests after login. Check the same generic recovery behavior for registered/unregistered emails. Ordinary family/institution accounts must not read or update the admin queue. References must reveal no email, user ID or handler ID.
6. Handle a verified request manually, publish a non-sensitive result, look it up by reference and confirm pagination can reach older requests. Keep pending requests pending when operational recovery/erasure has not been completed.
7. Prepare question-only and record-based sheets for all ranges and parent/details/notes selections. Edit the preview, change a record on another family panel, return and confirm the draft remains with stale export blocked. Toggle sharing selections and language, simulate fetch failures, compare the refreshed candidate, accept it and copy selected manual additions from the retained draft. Confirm excluded parent/notes content is absent from the refreshed output and previous drafts never print/download. Check phone preview, Unicode, blank days, long edits and actual PDF pagination.
8. As staff, try each template, preview, modify and preview again, publish, verify safe call/booking links and update a real checked date. With unpublished edits, use entrance buttons, logout, reload, browser Back/Forward, history jumps and rapid repeated navigation. Cancel must retain the URL, draft and tracked history position; confirm must leave once. Check navigation during a delayed publication. QR scan/download and guide printing need the deployed public URL.
9. Follow the entire Japanese registration, install, settings, security, failure and help flow. Verify keyboard focus, text size, contrast, reduced motion, print cleanup and account changes. Ask Japanese-speaking care staff to review public copy and actual local service information.

The prior revision `452ccdd` recorded 181 checks across its backend/frontend/privacy suites. That historical result does not validate this change; no current pass count is claimed.
