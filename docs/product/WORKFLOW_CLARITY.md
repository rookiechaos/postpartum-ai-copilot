# Clear care workflows — 2026-10-21

The seven product-review recommendations are implemented in source. No application, worker, dependency installation, build, test, lint/parser/compile check, database initialization/migration or browser/print acceptance was executed. Source inspection and read-only publication checks do not establish runtime correctness.

## Family workflows

| Area | Source behavior |
| --- | --- |
| Subject and visibility | Record editors, running timers, timeline, AI analysis and consultation sheets show a common scope banner. The current login remembers a recently selected subject in memory. Where offered, using it requires an explicit confirmation and never carries sharing choices. Family viewing remains distinct from sharing a record. Logout/account-session unmount clears the suggestion. |
| Old unassigned records | An owner can find unassigned, private baby records by start date in JST and type, page through results, select up to 50, preview one target subject and confirm. Only attribution changes; records stay private. Adult records, care quantities/times and notes are excluded from the mutation. Sharing remains a separate decision in each record's editor. |
| Atomic undo | Each organization operation has a durable owner-scoped key and identity/revision receipt. Repeating the same key/content returns that operation's outcome. Undo restores unassigned status only if every affected record still has its resulting identity, revision, target and private state. Any later edit/share/deletion stops the entire undo, with no partial reversion or revision decrease. The ten most recent receipts remain accessible after a new login. |
| Home continuation | Pending care saves and timers carry their subject, type and original time. Contact plans show the contact name. Actions say what opens next. Pending creation/attribution results cannot be hidden individually; other items can still be hidden for this login. Opening an item performs no save, recovery or contact action. Attribution operations link back to their existing preview/result controls. |
| Handover changes | A family member can review currently visible baby records and shared handover-note versions against their own last explicit baseline. New/changed entries show current permitted facts; withdrawn entries contribute a count only, with no retained contents revealed. Deletion, unsharing and leaving the seven-day window are deliberately not distinguished. The baseline contains IDs/versions, not health or handover text. |
| Consultation material | Each explicitly saved consultation links a chosen contact, optional appointment, subject, three questions, inclusion choices and edited sheet text. Saved text is private and is never sent to the contact or automatically regenerated. Opening a saved version requires replacing the working sheet explicitly. New records make a working sheet stale; a saved version with unchanged options can be deliberately reaccepted as historical material, or regenerated. |
| AI send confirmation | Chat uses the explicit “Send this content to AI” button instead of an agreement checkbox followed by a separate send button. Attachments/previous exchange remain opt-in, visible and editable. Ordinary form submission does not send. The click captures the current payload; double clicks are guarded, and failed sends require another explicit activation. Analysis retains its separate existing confirmation. |

The handover review digest and reader revision must still match at confirmation. If records, permissions or another window's confirmation changed, the UI requests a fresh review. Refresh/focus/reconnect reads never mark anything reviewed. Polling disables confirmation while a read is pending; a matching returned version preserves the checkbox and reading position. The existing individual note acknowledgement is separate and is not set by confirming the change list. Neither confirmation means care was performed.

Consultation save retries retain the packet ID, write key and frozen content. A later conflicting version is shown for explicit review; it is not silently adopted as the local edit base. Stopping a retry retains the unresolved packet identity and prevents starting another packet until the operation is resolved or a corrected save succeeds. Deletion clears the stored content/fingerprint and current sheet buffers; a small tombstone prevents late requests from recreating the deleted packet. Printed/downloaded copies and separate retained backups are outside that deletion.

**Explicit consultation saves are separate from opt-in seven-day draft recovery.** They have no automatic seven-day expiry and remain until deliberately deleted or handled through the operator's retention process. The UI explains this distinction before saving. Organization previews, pending operations and timers are still current-login state unless their existing opt-in draft workflow covers them; no new offline queue or automatic mutation recovery is added.

## Operator workflow

Parent-health record banners read current family sharing destinations and note choices, including the seven-day sharing scope. An unavailable metadata read is labelled unknown; it never implies that globally shared parent records are private. Home shows all unresolved creation/attribution items before optional continuation items; the latter retain the compact initial view.

An administrator's action summary shows received/in-progress/overdue account-request counts, waiting AI tasks, waiting over 15 minutes, recently updated failed tasks and contacts requiring review. The queue threshold is an operational prompt, not a promised response time. Contact review uses the same public-content digest as the institution queue, including pending or changed tasks.

The summary excludes account references, contact emails, question bodies, care text and internal review reasons. Account actions open the existing authorized queue, with an explicit overdue filter when requested. Directory actions use the institution entrance and its existing authorization/leave guards. AI status does not resend questions or restart tasks. The detailed operator queue retains its existing legitimate account-processing fields and manual-processing limits.

## API and storage rollout

Deploy matching frontend, API and worker versions. There are no new dependencies or changes to existing SQL columns. Existing deployment/startup initialization creates three new tables; **it has not been run**. Preserve backups, stop old worker consumers during the coordinated upgrade and retain the existing database volume. The existing worker schema gate checks the new model tables before claiming jobs.

| Storage | Purpose |
| --- | --- |
| `record_organizations` | Owner/request-key receipt, target subject, selected record identities/resulting versions, fingerprint and undo flag. Contains no care notes or measurements. |
| `family_reviews` | Last explicit family review per reader; membership revision, baseline revision, record/note identity-version maps and confirmation time. No record/note text. |
| `consultations` | Private, explicitly saved material, selected metadata and sheet text, revision and last write identity; cleared tombstones prevent resurrection after deletion. |

| API | Access / behavior |
| --- | --- |
| `GET /api/record-organization/unassigned` | Authenticated owner; optional `from_day`, `to_day`, type and ID cursor. At most 50 structured choices per page. |
| `GET /api/care-subjects/visibility` | Authenticated owner; current parent-record sharing destinations/note choices, without health content. Failed metadata reads display unknown, never a false private label. |
| `POST /api/record-organization` | Owner; confirmation, stable request key, subject revision and 1–50 immutable record identities/versions. Atomic assignment, always private. |
| `GET /api/record-organization/receipts`, `GET /api/record-organization/{request_key}` | Owner-only operation results. No raw request-body replay. |
| `POST /api/record-organization/{request_key}/undo` | Owner; explicit confirmation and all-or-nothing version checks. |
| `GET/POST /api/families/{family_id}/review` | Active member; own baseline and explicit digest/membership/revision confirmation. Current sharing permissions apply to every read. |
| `GET /api/consultations`, `GET/POST/DELETE /api/consultations/{id}` | Owner-only private packets. Paginated creation order; revision/write-key checks, explicit save and deletion. |
| `GET /api/monitoring/actions` | Existing administrator allowlist; status/count metadata only. |
| `GET /api/admin/account-requests?overdue_only=true` | Existing administrator queue; filters unfinished requests by their recorded expected reply time. |

## Privacy and deletion inventory

Include all three tables in controlled account/family erasure and retention review. Organization receipts retain owner/subject/record identifiers even after a record is removed; family baselines retain participant/note/record identifiers until replaced or erased. Consultation packets can contain health text deliberately saved by the owner, separate from server drafts. Cleared packet tombstones still retain account/packet/write identifiers and timestamps. Apply the operator's documented backup/log retention process separately; no automatic account erasure runner is introduced.

Recent-subject hints and Home work metadata remain in current-account memory, not browser health-data storage. These new workflows make no external AI calls, except when the person explicitly sends a chat question through the existing AI path. No email, phone call, booking or contact message is dispatched by saving or opening these features.

## Pending acceptance after execution is authorized

- Validate creation/repeated initialization of all three tables on SQLite/PostgreSQL and coordinated API/worker startup with retained data.
- Verify subject suggestions across personal/family targets, same-named babies, unavailable subjects, restored drafts, account changes and logout. Carrying a target must never carry sharing consent.
- Exercise organization with multiple pages, JST dates, 50-record limits, stale target/record revisions, adult/foreign IDs, concurrent edits, receipt loss, repeated writes and interrupted undo. Confirm atomic rollback and preservation of all care content/sharing decisions.
- Verify Home actions against pending saves, running/stopped timers, attribution results and contact plans. Opening must focus the existing control without submitting; separate read failures must not hide available items.
- Use separate family accounts to add, edit, unshare, delete and age records out of the seven-day window. Confirm note/record changes, membership revocation/rejoining, two-window confirmations, digest conflicts and loss of a confirmation response. Previously hidden content must never return through the baseline.
- Save/open/edit/delete distinct consultation packets, including removed contacts/subjects, old text, changed options, reaccepting a historical version, concurrent updates, lost responses, unresolved saves, deletion tombstones, pagination, optional draft recovery and print/download output.
- Check explicit chat button activation, keyboard-only use, no implicit form send, editable follow-up drafts, selected attachments, double clicks, retry, logout and account switches. Inspect provider payloads using synthetic data only.
- Verify operator-summary/overdue-filter access for anonymous, ordinary, institution and administrator accounts. Confirm matching review digests, no family text in summary responses, correct counts and preserved unsaved account edits.
- Check mobile layout, enlarged text, focus behavior, screen-reader labels and both languages. No browser or visual acceptance has been performed.
