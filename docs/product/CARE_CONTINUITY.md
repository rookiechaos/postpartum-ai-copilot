# Care continuity and staff handoff

The seven product improvements below are implemented in source. The application, dependency installation, builds, tests, database initialization, migrations and browser flows have **not been executed**. Earlier verification reports do not validate this revision.

## Family behavior

| Improvement | Implemented behavior |
| --- | --- |
| Explicit baby identity | Register a nickname for one personal baby and one baby per family. The recorder remains the authenticated adult. Family managers create or rename the family nickname; active members can select it. No birth date or legal name is required. Creating a nickname never assigns, moves, merges or shares existing records. |
| Separate sharing decisions | New baby records can remain unassigned and private. A family record is visible only when its owner explicitly selects the family baby, selects sharing for that record, and permits baby sharing in that family's settings. Adult health/mood records and free-text notes keep their separate sharing controls. |
| Overnight records | Home offers Last 24 hours, Today and Yesterday, in JST. Feeding and sleep can retain a reviewed end time; their whole-minute duration is derived from the reviewed start/end. Records with confirmed intervals appear in each overlapping viewing period. Duration-only historical records retain their original event time; an end is never inferred. |
| Find a saved record | Quick receipts and timer results offer an explicit link to the exact owned record, including a backdated or overnight record. This opens details; it does not make another save. The full record list also shows the care subject. |
| Continue unfinished work | Home shows running/stopped timers, uncertain quick/full-form saves, and recoverable record drafts before private contact plans. It shows two items initially, with an option to reveal more or hide an item for this login session. Opening an item navigates to its existing editor/recovery notice without saving, restoring or contacting anyone automatically. |
| Soft duplicate review | Before a new attributed baby record is sent, a local API checks currently visible shared family records from the last seven days. Another recorder's same-type event within five minutes prompts review; feeding/diaper subtype is compared when specified. These are possible matches, not proof of duplication. The person can continue as a separate record or return to input. No record is merged, deleted or edited by this check. |
| Consultation closure | In addition to Preparing, Waiting and Booked, the person can choose Finished or Not continuing for now, and retain private notes about the contact's response and their own next steps. Closing/pausing clears the planned contact time and removes that item from Home continuation. Calls and booking links do not change status. |
| Task-based first use | The first-use screen offers starting a record, joining family care, or preparing human help. Each opens the corresponding existing screen with short, dismissible guidance. Profile setup stays optional; the recording example remains available without creating real data. |

The consultation sheet selects one care subject's **own** baby records, or unassigned records. Adult health and notes remain separate optional inclusions. It does not pull in family members' records or merge different babies by default. Changing the selected subject or its nickname makes the previous generated sheet stale until reviewed again. Record backups include subject identity, the per-record sharing choice and confirmed end times.

The timeline displays overlapping records, not durations clipped to a viewing window. Home totals and consultation-sheet totals still group by the **start day**, and the interface labels this distinction. Missing observations remain unknown.

Save retries retain the original request key and payload. Duplicate review does not generate a second key, and reconnecting does not dispatch writes. If the comparison cannot be fetched, the person explicitly chooses whether to save anyway. The check cannot detect private/unshared events, an event saved after the comparison, or care outside its seven-day sharing window.

Care-subject choices and continuation metadata live in the current account session. Existing optional server drafts keep their seven-day, opt-in recovery rules. There is no offline queue or guaranteed background timer/notification delivery. One personal baby and one per family is the current limit; multiple babies within a family and automatic personal/family identity linking are not implemented.

## Institution behavior

The weekly queue now saves an internal task for each reviewed contact: decision, assignee, reason, next review date, source-content digest and revision. These fields are stored outside the public directory. Signing in again resumes pending, changed or due items; a deferred item is postponed until its chosen date unless its saved directory content changes. Saved items can be reopened explicitly.

- Deferring requires a reason and a future review date. It saves only the internal task, leaves public verification dates alone, and preserves any unsaved public edits on the current screen. A new contact must first be saved in the workspace before it can be deferred.
- Confirming unchanged requires an explicit attestation and reviewed dates. It saves the entire working draft, including those dates, together with the internal task in one transaction.
- Reviewing edited content likewise saves the entire current working draft together with the internal task. This does not independently assert that every missing public field has been verified.
- Workspace and task revisions both guard against another staff member's changes. Conflicts retain input for review; they do not silently overwrite a newer draft/task. Unsaved internal text participates in the existing leave/reload guards.
- Preview, before/after comparison and publication remain separate actions. Only publication updates the family-facing directory. Public JSON, family previews and publication history do not include internal task notes.

This is a shared workspace for one deployment/organization. Assignees are staff-entered names or departments, not a new staff permission system. The latest task state is retained; this change does not add a full internal task audit history. Staff should not place family health information in these notes.

## API and storage rollout

Update the API and frontend together. No dependency was added. The existing startup initialization is configured to create the two new tables and extend existing columns below; **startup and migration have not been run in this session**. Before an authorized deployment, back up the existing database and validate this transition on an isolated copy.

| Storage | Source change |
| --- | --- |
| `care_subjects` | New nickname/scope table. Each row has exactly one personal owner or family, with one subject per such scope. |
| `tracking_entries` | Adds nullable `subject_id`, nullable `end_timestamp`, and `family_shared` defaulting to false; adds a subject/time index. |
| `support_journeys` | Adds private `contact_response` and `next_steps` text, initially empty. Existing journeys retain their status. |
| `directory_review_tasks` | New staff-only latest-task table, separate from the public profile and publication snapshots. |

**Historical sharing changes deliberately.** Existing baby records remain owned by their original recorder, with no care subject and no per-record family sharing. They are still available to that person, but are excluded from the new family overview/timeline until the owner explicitly assigns the appropriate family baby and opts that record into sharing. Enabling the family's general baby-sharing preference alone does not assign or share unassigned records. There is no bulk attribution or automatic identity migration. Explain this to existing pilot families before updating.

Old clients that omit the new columns during a same-type correction preserve the stored attribution/end values. A shared write still requires the current family-sharing revision; an old client cannot bypass the new consent check. Frontend and API upgrades should therefore be coordinated. Pre-upgrade retry receipts retain their old fingerprints when the original request did not include the new fields.

| API | Purpose / access |
| --- | --- |
| `GET /api/care-subjects` | Authenticated owner sees personal and currently accessible family subjects, with current sharing/edit metadata. |
| `POST /api/care-subjects` | Explicit nickname registration; a family scope requires an active family manager. |
| `POST /api/care-subjects/{subject_id}` | Revision-guarded rename; cannot move the subject to another family or change its owner scope. |
| Existing tracking create/update/owned reads | Carry subject, per-record sharing and confirmed-end fields. Owner, immutable record identity and revision checks remain in force. |
| `POST /api/tracking/duplicate-check` | Read-only comparison under the current family membership/sharing rules. Returns limited structured facts, without health notes or adult records. No external AI processing. |
| `GET /api/families/{family_id}/timeline?period=last24` | Active member; accepts `last24`, `today`, `yesterday`. Only explicitly attributed and shared baby records; read-only family details. |
| Existing support-journey reads/writes | Owner only; adds completion/pausing and private response/next-step notes. |
| `POST /api/pilot/organization/review-tasks/{contact_key}` | Existing institution allowlist; task/workspace revisions, optional atomic draft update. Never publishes. |

The care-subject identifier/nickname and new support notes are not automatically attached to AI requests. The existing explicit AI field allowlist and send confirmation remain in use. Text the person deliberately types into a question is still part of that question.

## Manual privacy/deletion inventory

Extend the existing controlled manual erasure procedure to cover the new fields and tables. The operator request workflow records manual completion; it does not execute deletion or password resets.

- Include `care_subjects.personal_owner_id`, `created_by` and personal nickname rows in account-data review. Resolve any family-owned subject under the family's controlled retention/erasure decision; deleting its creator must not accidentally remove another member's records or reveal a private personal identity.
- Include tracking subject references, confirmed end times, per-record sharing flags, creation receipts, optional record/quick/timer/sheet drafts and any exported copies in the applicable inventory. Do not blindly cascade family-subject deletion into other recorders' data.
- Include `support_journeys.contact_response` and `next_steps`, as well as existing progress fields. Clearing a journey clears these texts; logs/backups and downloaded copies require the existing separate operational handling.
- Include internal task reason/assignee, `updated_by`, content digest and timestamps in institution/staff retention and erasure review. A removed contact's latest internal task remains visible to authorized staff until handled through that controlled process.

Removing shared access does not retract copies already downloaded or handed to another person. Account deletion, family deletion and staff-task retention still need an operational policy; no automatic erasure runner is added here.

## Pending acceptance, only after execution is authorized

- Upgrade an isolated pre-change database on each supported database engine; confirm historical ownership/content, unassigned/private defaults and retry receipts are preserved. Verify repeated initialization and concurrent startup behavior.
- Use separate personal, family and outsider accounts for subject creation/rename, direct-ID access attempts, revocation, concurrent sharing changes, stale revisions, record attribution, correction and family timeline isolation. General permission alone must not expose unassigned/personal/other-family baby records.
- Cover JST midnight, rolling 24 hours, yesterday, explicit overnight intervals, zero-minute records, unchanged seconds, end-before-start/future dates, missing old ends and long intervals. Check the saved-record link for today, yesterday and older backdated records.
- Cover pending saves, opt-in recovered drafts, timer return, hide/reopen, contact plans, account/entrance changes and reload. Background reads may refresh status but must not save, restore drafts, contact anyone or steal focus.
- Cover possible duplicates, legitimately separate events, unshared/other-family records, failed comparison, double clicks, retries and cancelled comparisons. Cancelling/discarding one review must not leave a warning attached to the next timer/record.
- Close, pause, reopen and clear support journeys; verify notes remain owner-only and persist under revision conflicts/removed contacts. Phone/booking actions must not imply a completed consultation.
- Save/defer/reopen weekly tasks, reload/sign in again, change the saved source, switch maintainers and race two editors. Check atomicity, retained unsaved edits, public preview/publication payloads and fresh verification dates.
- Check all three first-use routes, keyboard/focus behavior, phone layouts, enlarged text, both languages and consultation-sheet/backup output. A recovered or changed nickname must not silently relabel an old generated sheet.

None of these acceptance checks has been executed for this revision.
