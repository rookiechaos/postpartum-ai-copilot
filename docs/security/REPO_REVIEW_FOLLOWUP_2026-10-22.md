# Follow-up repository review fixes — 2026-10-22

This update addresses the four findings from the review of commit `1d1614a`: account-ID invitations after issuer removal, record restoration after the Undo offer expires, consultation-list pagination races and the keyboard entry to record organization.

The changes have only been reviewed as source. No application, build, tests, parser checks, migrations or database operations have been run. Publication checks use Git diffs and the repository privacy scanner; they do not establish runtime correctness.

## Account-ID invitation authority

New pending invitations store a server-generated invitation format version and the issuer's membership revision in the existing permissions JSON. Acceptance verifies that the issuer is still an active creator or administrator and still has the invitation's permission version. Only the creator may issue an administrator invitation. Acceptance clears invitation metadata and leaves all sharing choices disabled.

Issuing, accepting, removing and leaving use a family transaction lock. Existing member rows are locked in a consistent user-ID order before authority and version checks, matching the order used by handover acknowledgements. Link creation, revocation and acceptance use the same family-first order; acceptance reloads the token and issuer after acquiring locks so a previously read permission or token cannot bypass a revocation. A removed or departing member's outstanding account-ID invitations are cancelled in the same transaction. A concurrent change returns a conflict instead of granting stale authority or becoming a generic server error.

**Old pending account-ID invitations have no trustworthy issuer revision and must be issued again by a current manager.** They are hidden from the recipient's invitation list and cannot be accepted. Managers can still see the pending membership and revoke or reissue it through the existing account-ID form. Active memberships are retained. No new table, column or migration is introduced. Invitation links retain their existing 24-hour expiry, single-use, explicit-confirmation and default-private behavior.

## Restoring a deleted record

The eight-second limit now governs only the offer to start Undo. Once the person chooses Undo, the original record snapshot and its original creation request key move into a separate pending restoration. A slow request or lost response does not remove that information when the offer expires.

The pending operation supports an owner-only result check and a deliberate resend with the same content and request key. A retry checks the creation receipt first. A current, unchanged restored record resolves the operation; a subsequently edited or deleted record stops resending rather than overwriting or duplicating it. A missing receipt is a point-in-time observation, so any explicit resend retains the original key in case an earlier request finishes late. A failed read retains the pending operation.

The screen distinguishes an unsent offline attempt, restoration in progress, result checking and an unconfirmed result. The operation is included in the continuation cards, blocks conflicting writes in this panel and warns before leaving. It stays in the current login session's memory only. Reloading or signing out clears it. Explicitly ending the check warns that an already dispatched request is not cancelled; this ends the retained snapshot and request-key recovery path. No new health data is stored in browser storage.

## Consultation material pagination

First-page refresh and additional pages share a request generation, request identity and expected cursor. Refresh, hiding the view and packet operations invalidate earlier reads. A stale response cannot replace a refreshed list or append a page selected using an older cursor. Additional-page controls are disabled until the current first page is ready and while a list request is in flight.

Rows are merged by consultation ID, retaining the newer revision. List loading and errors are separate from packet write status, so loading a list does not lock the working consultation sheet or overwrite a save error. Packet operations refresh the first page when they finish; earlier page positions are not retained across that refresh. These changes do not alter saved consultation contents or their owner-only API access.

## Keyboard entry to record organization

The organizer's native `summary` no longer has `tabIndex=-1`. It keeps its normal Tab, Enter and Space behavior and can still be focused by the existing continuation navigation helper. Non-interactive headings retain their separate programmatic focus behavior.

## Pending execution checks

When running the application and tests is authorized, verify:

1. Fresh and historical ID invitations, issuer removal/exit/re-invitation, concurrent sharing changes, acceptance/revocation races and handover acknowledgements in both PostgreSQL and SQLite. Verify pending invitations never enable sharing and revision conflicts remain 409 responses.
2. Undo near the end of the eight-second offer, delayed and lost restoration responses, an initially offline attempt, repeated checks/resends, a subsequently edited/deleted restoration, navigation, explicit abandonment and sign-out. Confirm checking never performs a write and retries create at most one record.
3. More than two consultation pages with refresh and additional-page responses arriving in either order, hiding/returning, opening/updating/deleting packets, failed reads and duplicate IDs. Verify intermediate pages are not skipped and list reads do not lock the working sheet.
4. Keyboard-only entry to the closed organizer and its continuation path, including opening, interacting, closing and reopening it.
