# Record retries and UI review fixes — 2026-10-22

This revision addresses the five findings from the static review of `2227ad6`: creation retries using historical receipts, undisclosed two-factor recovery codes, chart controls disappearing in empty states, inaccessible failure notifications and movement that ignored reduced-motion preferences.

No application, build, tests, parser checks, browser rendering, migrations or database operations were run. Source review, Git whitespace checks and the repository privacy scanner are the publication checks; they do not establish runtime correctness.

## Current records after creation

Home quick records, the detailed creation form and the care timer now share an owner-only lookup by the original creation request key. A POST response alone no longer clears pending input or supplies the saved-record card. The current record must still be revision 1 and match all submitted care fields, normalized UTC timestamps and the server's null/private defaults. Current subject display metadata and sharing-permission revisions are not compared as care content.

A deliberate retry first reads the result. A matching record completes the operation without another POST. A missing result permits a resend only as part of the person's explicit retry, retaining the original content and key in case an earlier request finishes later. A changed or deleted record retains the input and prevents another creation attempt. Failed reads retain the pending state, including when creation already succeeded. The separate check buttons never create or update care records.

Previously offline or recovered pending creations also receive the family duplicate check before a new send. Continuing past a duplicate warning applies only to the operation shown. Cancelling that warning asks for confirmation if an earlier save is still unconfirmed.

Changed records can be opened for review. The detailed form requires confirmation before discarding its pending input and switching to editing the current record; the existing immutable key and revision still protect that edit. Starting a new quick record removes the prior receipt and Undo offer so they cannot be mistaken for the new result. The previous restoration workflow remains separate.

These checks describe the record at the time of the read. They do not prevent subsequent changes from another page. Existing update/delete revision guards continue to protect those operations. Pending input remains subject to the existing login-session lifecycle and opt-in server draft recovery; it is not written to browser health-data storage.

## Two-factor recovery codes

Authenticator setup displays the recovery codes returned by the server before activation. The person can copy them explicitly or save them manually, and must confirm they have saved them before enabling two-factor authentication. A failed clipboard operation offers manual copying. Setup material is kept in component memory and cleared on cancellation, completion or account changes. The existing activation flow still revokes old sessions and signs out.

This does not regenerate recovery codes for already-enabled accounts or implement automatic account recovery. The existing controlled recovery process still applies if someone has already lost their authenticator and codes.

## Charts and accessible feedback

Chart headings and the 3/7/14/30-day selector remain available while loading, on errors and with no plotted records. Empty-state content replaces only the chart area.

Settings-save and export failures stay on the page with retry controls. Export retry retains the requested format. Toast announcements have stable polite/assertive regions and localized close labels; errors remain until dismissed by default. The stack scrolls within a bounded height and clears on login changes; late callbacks from an old session cannot add notifications to a new session. Settings and toast cards use native elements without their previous Framer Motion movement, allowing the existing CSS motion preferences to cover their remaining transitions.

## Rollout and pending acceptance

These frontend changes use existing owner-operation and two-factor endpoints. No schema migration, new dependency or backend permission change is introduced. Deploy with the current matching API.

When execution is authorized, check:

1. For all three creation surfaces: lost POST response, subsequent edits/deletion from another page, GET failures including 4xx, initially offline saves, repeated clicks, optional draft restoration and sign-out. Verify unchanged records resolve, different records retain input, checks send no care writes and retries keep the same key.
2. Unknown/zero quantities, null fields, UTC/JST dates, interval durations, private/shared subjects and older pending operations without attribution fields. Verify legitimate unchanged records are accepted without mixing different records.
3. Two-factor setup, clipboard permission denial, manual copying, missing save confirmation, invalid code, cancellation, slow responses and activation/sign-out. Confirm the saved recovery codes work through the existing login flow.
4. Charts with records only 8–30 days ago, an empty three-day range, failed loads and fast range changes.
5. Keyboard and screen-reader feedback for failed saves/exports and repeated notifications, small phone screens, large text, high contrast, and both system/application reduced motion.
