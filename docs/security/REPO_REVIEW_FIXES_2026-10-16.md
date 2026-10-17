# Repository review fixes · 2026-10-16

This revision addresses the nine findings from the repository source review. It is **source only**: no application or worker startup, dependency installation, build, lint/parser/compile check, test, database migration, vector ingestion or browser acceptance was run. Publication privacy scanning and Git whitespace/diff inspection are separate read-only checks; they do not establish runtime correctness. Regression assertions were updated but not executed.

## Changes

1. Compose requires an explicit nonempty `POSTGRES_PASSWORD` and no longer publishes PostgreSQL's port on the host. The API and worker reach the database on the private container network. The example environment leaves the password blank; operators must generate a unique URL-safe value.
2. The legacy daily/weekly summary GET endpoints return current local counts and a short factual description. They do not instantiate/call an AI provider or attach personal context externally. Both periods use Japan calendar boundaries (weeks begin Monday). The old optional service argument is ignored for compatibility. Summary results are no longer cached across record edits/deletions. Optional AI analysis remains the separate existing scoped action.
3. Home combines the submitted care fields with the server's identity/version receipt. Names, time, undo and correction therefore refer to the actual saved record, including receipts returned by an idempotent retry. Correction retains the existing immutable-key/revision guard.
4. Profile reads use the database and refresh any previously loaded ORM instance. The API and independent AI workers no longer keep separate 30-minute profile caches. This does not grant permission to attach a profile; existing per-request scope selection still applies.
5. Fetch, token refresh and retry share cancellation and a bounded request lifetime. Refresh has its own limit as well. Transient refresh failures preserve the login and propagate communication failure; confirmed authentication rejection still clears it. Abort listeners/timers are removed on completion. No care record or AI question is automatically replayed after reconnecting.
6. Reminder delivery uses the existing database queue plus owner-authenticated browser polling, independent of the settings tab. The retired standalone notification worker exits without consuming/completing reminders. See the receipt contract below.
7. Error logs contain exception type, stack locations (file basename/function/line) and allowlisted operational codes/counts. They omit exception messages, source lines, locals, chains, nested request context and account identifiers. Database engines hide SQL parameters. Error handlers log declared route templates, and generic failure responses omit raw exception text even in debug mode. Provider warning paths no longer interpolate exception text. Existing runtime logs/backups are not rewritten by this code change; their retention remains an operator responsibility.
8. DAU, MAU, retention, conversion, global feature usage, global task performance and NPS statistics require the administrator allowlist. Public event submission and explicitly public feature requests keep their existing access policy; own usage/user-path endpoints remain owner-scoped. Institution editing alone does not grant operational statistics access.
9. RAG never automatically seeds a sample corpus. It reads/writes only `postpartum_public_sources_v2` and requires explicit approval, an HTTPS public source URL without credentials, a title and a non-future review date. Source metadata and the matching retrieved chunk are checked before either enters an answer. Textual mentions of authorities are not treated as source verification.

## Reminder receipt contract

- With notification permission, a logged-in family page polls `GET /api/notifications/due` while visible and connected, approximately every 30 seconds and on focus/reconnection. The response contains at most 25 owned due IDs, without health text. Reading it changes no delivery state.
- The client asks the browser to display a generic notice, through an active service worker when available or the browser notification constructor otherwise. Care text, profile data and account identifiers are not placed in the notice or its click URL.
- Only after the browser accepts the request does the client call `POST /api/notifications/{id}/acknowledge`. `is_sent`/`sent_at` retain their schema names and now mean **client-reported browser acceptance**, not proof of display, reading or guaranteed delivery. This acknowledgment is limited to the authenticated owner and an enabled, due reminder; retries are idempotent.
- A conditional update serializes acknowledgment and stopping a pending reminder. Only the successful first acknowledgment creates the next recurring occurrence. Missed recurrence times are skipped. If a stop races with acceptance, the API returns a conflict and the UI refreshes the schedule instead of claiming it stopped the already-accepted occurrence.
- If display fails, no acknowledgment is sent. If its response is lost, the same mounted login remembers that it already asked the browser and retries the receipt without showing the notice again. Separate browser instances/reloads may show duplicates; notification tags reduce duplication within a browser. No exactly-once display guarantee is made.
- Logout/session unmount aborts polling and attempts to close notices created by that mounted session. No reminder queue or health text is written to browser storage. Closed/offline/background delivery is not guaranteed. Existing help-progress next-contact dates are not converted into reminders.
- Explicit schedule offsets are stored as UTC. Legacy naive timestamps continue to mean UTC; existing stored schedules are not rewritten.

## Upgrade notes

Deploy matching API, worker and frontend versions together. There are no new SQL tables/columns or dependency additions in this revision; no migration or acceptance was executed.

For an existing PostgreSQL volume, changing `POSTGRES_PASSWORD` does not change the actual database role password. Coordinate a real credential rotation and API/worker configuration through the operator's controlled procedure. Retain the data volume and backups. The source change does not perform a credential rotation.

Old vector collections remain on disk and are excluded from retrieval. Do not automatically copy them into the new collection: the previous sample corpus included material inappropriate for the Japanese pilot. An operator must review public sources and explicitly re-ingest approved text with `approved: true`, `source_url`, `title` and `reviewed_on` metadata through `RAGService.add_documents`. Approval is the operator's attestation, not an automated fact check or clinical review. Until then, retrieval returns no source material. No existing vector files were opened, deleted or re-indexed during this edit.

Previously completed/dropped reminders are not automatically requeued because their real delivery status is unknown. Operators and families should review existing schedules deliberately. No existing notification data was rewritten.

## Pending acceptance

In a later authorized session, validate:

1. Compose rejects a blank password, exposes no host database port, and API/worker credentials match an existing retained database after coordinated rotation.
2. Daily/weekly reads make zero external AI calls with ordinary, parent and private-note records; count changes reflect corrections/deletions and JST day/week boundaries.
3. Every quick action names the saved record and opens correction from its receipt; retrying a lost response retains the same identity and version checks.
4. A separate worker reads updated profile data immediately, while excluded profile fields remain excluded from the AI request.
5. Expired-token requests recover within a bounded time on a hanging refresh, transient server failure, cancellation, logout and account change. Care retry keys/timestamps stay unchanged.
6. Due reads, display rejection, receipt loss, another account, multiple tabs, concurrent receipt/stop requests, recurrence, offline/reconnect and native/service-worker notification paths preserve ownership and truthful state. Check browser notification permissions and generic lock-screen content on target Japanese users' phones.
7. Database/provider/validation exceptions with synthetic private markers never put the markers or SQL parameters into logs or generic responses; diagnostic locations remain useful.
8. Anonymous, family and institution-only accounts cannot read any global metric endpoint; provisioned operators can, and own statistics still enforce ownership.
9. A retained old sample collection contributes no prompt context/source links; the new empty collection produces no fabricated sources; explicitly approved, attributed public material can be ingested and retrieved, while invalid metadata is rejected.

Historical reports and the updated regression source are not evidence that these acceptance checks have passed.
