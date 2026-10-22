# Repository review fixes — 2026-10-22

These changes address the five findings from the source review after the shared UI foundation update. They have not been executed, built, tested or migrated. The checks performed for publication are source inspection, Git whitespace checks and the repository privacy scanner; these do not establish runtime correctness.

## Password verification and legacy compatibility

The active password algorithm is PBKDF2-SHA256, not bcrypt. The defect was an obsolete application rule: if UTF-8 input exceeded 72 bytes, it hashed only the first 72 **characters**. For passwords longer than 72 characters, the remaining characters did not affect authentication.

New hashes use the complete password, including its Unicode characters, and carry a `full-v1:` format marker in the existing `hashed_password` field. Verification of a marked hash never falls back to truncation. Registration retains the existing 8–128 character validation and strength requirements. The unused optional bcrypt dependency is removed; Passlib remains pinned.

Unmarked hashes retain the exact old verification rule so existing accounts can still sign in. **Previously discarded password tails cannot be recovered. Legacy hashes still need an explicit, identity-verified credential reset to eliminate their old prefix equivalence.** A login does not silently choose a new tail or rewrite credentials. The responsible operator's controlled reset procedure must call `AuthService.get_password_hash()` for the replacement password and perform the required session revocation before attesting completion. Do not add the marker to an existing hash: that would change verification semantics without creating a full-password hash.

No schema change is needed for the marker. All authentication instances and controlled reset tooling must understand the new format before accepting new registrations or password changes. An older application version cannot verify marked hashes; a rollback must retain support for this format. No stored credential has been changed by this source update.

## Unconfirmed record deletion

The tracking screen keeps the originally confirmed record snapshot when a deletion response is lost. It shows an unconfirmed result rather than asserting that the record remains saved. The snapshot stays in current-session memory, with a continuation card and a page-leave warning; no health content is newly stored in browser storage.

“Check deletion result” performs an owner-only read using the original numeric ID and immutable record key. Absence offers the existing eight-second Undo window from confirmation. Finding the same version is only a point-in-time observation: a timed-out write may still complete later. Finding a different version ends the old deletion attempt and asks the user to reload, without deleting the changed record.

A deliberate retry asks for confirmation again, reads that same identity first, and sends the original revision guard only if necessary. If the original deletion has already committed, it resolves to Undo instead of a false conflict. Checking or returning to a page never automatically deletes or restores a record. Other record writes in this panel wait until the deletion is resolved or the user explicitly stops checking; stopping the check does not cancel a request already sent. Refreshing or signing out clears this in-memory check. Undo restores the confirmed snapshot as a new record through the existing creation request key; the UI does not claim to know which device removed a record found absent.

## Record organization pagination

Fetched pages are keyed by cursor. Reopening the organizer or returning to the tab replaces the fetched page, then merges records by immutable record key, keeping the newest revision when a record appears in multiple pages. The loaded count and React keys therefore describe distinct records. A filter change or explicit refresh resets the page cache. Other cached pages retain their snapshot until refresh.

Selected records retain the revision the user chose. A later edit is not silently adopted into a batch operation; the existing atomic revision checks still reject a stale selection before changing records.

## Recovery data in exports

Backend JSON tracking records and the CSV `Value` payload now use one field contract. Both include weight, breast condition and recovery notes, alongside record identity, revision, owner, subject, sharing choice, start/end times and all existing care fields. Zero values and nulls are retained. Japanese text remains readable in CSV JSON payloads; the four-column CSV layout is unchanged.

Queries still export only records owned by the requesting account. This does not expand exports to family members' records. It also does not turn the existing export service into an archive of every application table or change the separate Settings export implementation.

## Fixed-time reminders in Japan

Default mood reminders are calculated at 09:00, 14:00 or 20:00 Japan time, then converted to naive UTC for the existing database contract. Weight (09:00), recovery (20:00), daily summaries (21:00) and Sunday summaries (21:00) share the same calculation. A time already reached rolls to the next eligible Japanese day or week. A weekly reminder uses the Japanese weekday even while UTC is on the preceding day.

Explicitly supplied schedules and interval-based feeding reminders retain their existing contracts. Existing reminders are not rewritten by this change; an operator must review any old incorrectly timed reminders before recreating them with the user's agreement.

## Pending runtime acceptance

When execution is authorized, verify:

1. Full-length ASCII and Japanese passwords, different tails after character 72, incorrect passwords, old short and truncated hashes, and a controlled legacy credential reset. Confirm new-format hashes work across every authentication instance.
2. Deletion success, a lost response after commit, a delayed commit while checking, a changed revision, an offline attempt, repeated confirmation, explicit abandonment, page switching, reload/sign-out and deliberate Undo. A read must never dispatch a write by itself.
3. Several organization pages, close/reopen and tab return, cursor overlap, changing filters, refresh after removals and a stale selected revision. Confirm unique rows and atomic conflict handling.
4. Both backend export endpoints with recovery-only records, all care kinds, empty and zero fields, Japanese notes, overnight records and a separate account's records that must remain excluded.
5. Japanese midnight, exact scheduled times, month/year boundaries and Sunday before/at/after 21:00, with a server configured outside Japan. Confirm UTC storage and Japanese display agree, and explicit schedules are unchanged.
