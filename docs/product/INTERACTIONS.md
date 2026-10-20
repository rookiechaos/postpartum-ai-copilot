# Everyday interactions

This revision implements the eight requested interaction changes in source. The application, build, tests, browser flows, database initialization and migrations have **not** been executed. Earlier verification reports do not validate this revision.

The later [care-continuity revision](CARE_CONTINUITY.md) supersedes this file's original today-only timeline, timer-location guidance, session-only weekly review state and original schema rollout. It adds care subjects and explicit per-record baby sharing, confirmed ends and overlapping periods, persistent private review tasks, new tables/columns and corresponding migration requirements. Read that rollout before deploying the current source.

## Family flows

| Change | Behavior |
| --- | --- |
| Expandable save receipt | A quick save shows its name and Japanese event time. Time and measurement buttons expand a compact editor in place. Changes require Save changes. The existing eight-second undo applies to the original quick save and ends after a successful correction; the receipt remains available after undo expires. |
| Today's timeline | Home shows the entire Japanese calendar day's own records, newest first, with feeding/diaper/sleep filters. Selecting a row opens a native modal dialog, presented as a bottom sheet on phones. Own records offer a compact correction and a route to the full editor. Family sharing is a separate explicit selector, starts off, includes only shared baby care records and displays recorder labels/numbers. Its entries are read-only, including the viewer's own entries; switch to My records to edit. Missing records remain unknown. |
| Answer actions | Make it shorter and Add my circumstances prepare editable questions. They select one bounded previous question/answer pair for review, reset attachment choices and consent, and never send automatically. Existing input/context replacement asks first. The actual submission preview and explicit previous-exchange checkbox remain in use. |
| Custom shortcuts | Choose and reorder one to four buttons using checkboxes and Move up/down controls. Defaults remain the four instant-save buttons. Optional breastfeeding/sleep timer buttons open the timer; their captions distinguish them from immediate saves. Only shortcut identifiers persist in account-scoped browser preferences. |
| Confirmed timers | One breastfeeding or sleep timer can run at a time in this login session. Stop opens editable JST start/end fields and optional breastfeeding side. Whole-minute duration is rounded down. A separate checkbox and Save action are required. Leaving the screen does not infer an end time or save a record. Returning to a running timer asks the person to review actual times. |
| Handover acknowledgements | Each visible shared note includes its revision. A reader explicitly acknowledges another member's current version. The family sees who acknowledged which version and when. Earlier-version acknowledgements remain labeled as earlier; a note edit never counts as acknowledged automatically. Opening a screen does not acknowledge anything or record performed care. |
| Three-step human help | Choose a purpose/contact, prepare an editable opening with published application/preparation/fallback information and optional personal checklist, then maintain private progress. Steps can be visited directly or skipped. Consultation-sheet handoff retains the existing incoming-question and slot confirmation. Phone/booking clicks never update progress. Removed contacts keep their existing progress/editor state without inventing current contact details. |

The compact editor rereads the owned record before editing. It carries all existing care fields into replacement writes, including undisplayed notes, and uses immutable record keys and revisions. A response loss leaves the original payload available for checking or an explicit retry. It never silently rebases an old edit over a newer record. Dismissing unsaved/uncertain edits asks first; a write in flight blocks dismissal. No reconnect event sends a write.

Timer creation reuses one request key and frozen payload for every retry. Checking a result is a read of that account's creation receipt, not a new save. Not finding a receipt does not disprove an in-flight request. Deleted or changed timer records require review. Timers are recorded at the reviewed start time; a timer starting yesterday may therefore be found under All records rather than today's timeline.

Timer recovery uses the existing optional server-draft preference and a separate `timer` draft kind. It is off by default. Saved timers can be reviewed/restored/deleted within the existing seven-day recovery window; this is not browser health-data storage, guaranteed background timing, or an offline recording queue. Restored pending writes need confirmation again and keep the original operation. Disabling draft recovery clears timer drafts along with the other draft kinds. Signing out clears screen memory; shortcut preferences remain because they contain only layout choices.

## Organization flow

The weekly review takes a snapshot of due contact keys matching the selected maintainer filter. Staff review one contact at a time, open the existing editor, deliberately confirm unchanged information, or defer it. Confirming unchanged requires an attestation plus explicit checked/next-review dates and changes only the working draft. It does not claim all missing fields are resolved. Deferring does not update either date. Editing requires reviewing the changed content before continuing and does not silently stamp a checked date.

After review, Save draft and Preview all changes use the existing workspace revision, validation, before/after comparison and family-view preview. Publication remains a separate explicit action. Closing the weekly session keeps working draft edits and returns to normal editing. Reload/unload/entrance guards still belong to the existing organization workspace. Review-session position and deferred choices are session-only; actual contact changes can be saved through the existing draft API.

## API and rollout

Deploy the frontend and backend together. No dependencies or existing database columns were added. Existing startup initialization registers one new table, `family_handover_acknowledgements`; startup/table creation was not run in this editing session.

| API | Access and purpose |
| --- | --- |
| `GET /api/tracking/entries/{entry_id}?record_key=…` | Authenticated owner only; reads the exact immutable record for compact correction. |
| `GET /api/tracking/operations/{request_key}` | Authenticated owner only; returns `not_found`, `deleted`, or the currently stored record associated with the creation receipt. Never returns another account's receipt. |
| `GET /api/families/{family_id}/timeline` | Active family membership; only today's JST shared baby care records, without adult records, tracking notes or mutation identities. |
| `GET /api/families/{family_id}/overview` | Adds visible-note version and acknowledgement metadata under the existing membership/sharing rules. |
| `POST /api/families/{family_id}/handovers/{author_id}/acknowledge` | Active reader and author membership; requires the displayed note and author-membership revisions. Rejects self, stale, expired and unshared notes. A repeat for the same version/memberships preserves the original acknowledgement time. |
| Existing `/api/drafts/{kind}` | Adds `timer`, retaining account ownership, opt-in, preference/draft revisions and expiry rules. |

Acknowledgement writes lock memberships in a consistent order and guard the exact visible note against concurrent editing. Only the latest acknowledgement per reader/author is retained; no note text is copied. Acknowledgements from revoked or changed memberships are excluded from overview responses. Rejoining never revives old acknowledgements automatically.

Add acknowledgements to the controlled manual erasure inventory: remove rows where the erased account is either `user_id` (reader) or `author_id`, and remove family-scoped rows when a family is erased. Include `user_drafts` with `kind=timer` in account draft erasure. Access expiry is not a promise of physical deletion. The existing operator workflow records manual execution; this revision does not introduce automatic erasure.

## Pending acceptance, only when execution is authorized

- Compare receipt corrections with timeline/full-form edits, including zero values, empty measurements, unchanged timestamps with seconds, notes, concurrent updates/deletion, eight-second undo expiry and response loss. A compact correction must preserve undisplayed fields.
- Exercise mobile sheet focus, Escape/backdrop cancellation, unsaved confirmation, in-flight close protection, keyboard navigation, narrow layouts, enlarged text and high contrast. Check entering/leaving tabs preserves own edits.
- Cover JST midnight, all daily records rather than a small recent subset, family selection/switching, revocation while viewing, reconnection, filters and unknown periods. Automatic read refresh must not dismiss an otherwise available family detail sheet.
- Check both answer actions with existing drafts, draft recovery, selected previous exchanges, consent reset, edited questions and sync/async chat. No action may dispatch an AI request by itself.
- Cover shortcut limits/order, account separation and blocked browser storage. A timer shortcut must open the intended activity without saving or overwriting an active timer.
- Cover timer start/stop, interrupted use, correction across midnight, partial minutes, saved/unsaved draft recovery, restoring a pending write, disabling recovery, explicit discard, duplicate clicks, offline/429/timeout retries, operation checks and account changes. Reconnection must never save automatically.
- Use two family readers and an outsider for acknowledgement access, same-version idempotency, earlier-version labeling, edits, unsharing, expiry, revocation/rejoin and simultaneous note/permission changes.
- Move between every help step with and without a selected contact, edit the opening, prepare a sheet, remove a contact during an unsaved/in-flight progress edit and preserve the original form state. Confirm phone and booking links remain separate from progress updates.
- Review a maintainer-filtered institution queue, edit/defer/confirm unchanged, invalid dates, removed contacts, partial completion, shared-workspace conflicts and publication failure. Inspect the batch diff and family view before explicitly publishing.

No acceptance items above were executed.
