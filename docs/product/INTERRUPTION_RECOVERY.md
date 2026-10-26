# 中断した操作を安心して続ける

Source revision: 2026-10-25. This revision was implemented and reviewed in source only. App startup, builds, automated tests and browser acceptance were not performed.

## Improvement plan

The application already has recording, chat, family handover, local support, institution and operator entrances. The next step is to make those features reliable when a caregiver is interrupted. Extend the existing session-work registry, show the difference between an edited draft and an uncertain save, and require explicit choices when new content would replace an existing question.

| Priority | Problem | Implemented improvement |
| --- | --- | --- |
| First | Profile edits are absent from the shared continuation entry. | Track changed profile fields and account language, show save state, return directly to Profile, and allow a confirmed discard. |
| First | An AI answer loses its waiting cue once processing finishes. | Keep a separate new-answer cue until the user explicitly reads it or acts on that answer. Return to the answer's opening, including its warnings. |
| First | A suggested question can overwrite a working question. | Preview incoming and example questions with explicit apply/dismiss actions. Existing input, previous exchange and attachment choices remain until apply. |
| First | Handover notes can be lost when leaving, or repeated after an unknown save. | Register changed notes, preserve the submitted snapshot, block another write while uncertain, and provide a read-only current-note check. |
| Next | Phone explanations, edited contact progress and consultation-sheet edits are missing from continuation. | Register them with destinations that reveal their existing editors. Compare against confirmed baselines so unchanged values and opened saved sheets do not appear edited. |
| Next | State labels and recovery choices differ across pages. | Add Japanese/English copy for unsaved, saving, uncertain and checked states; extend the shared continuation/leave copy and document exact coverage. |

All rows above are implemented in this revision. They reuse existing APIs. There are no new dependencies, backend endpoints, tables, migrations, offline stores or provider calls.

## What a family sees

The collapsed **続き・確認が必要なこと** strip follows family pages. It contains generic status labels and explicit return actions. Returning does not save a record, change a sharing choice, restore a server draft, call a contact or send an AI request.

- **Profile:** the baseline is the loaded or confirmed profile and its account language. Saving captures the submitted values, so changing display language while it is pending stays an unsaved change. A network result that cannot be confirmed requires a read-only check. A different result is shown in a comparison before the user chooses to continue editing. Discard restores the confirmed fields and display language after confirmation; it does not write to the account.
- **Chat:** completed answers keep a cue even after switching pages. Reading the latest answer explicitly, following up on that answer or preparing a consultation question from it clears that answer's cue. Merely opening the page does not mark it read. Incoming/example question proposals have explicit apply and dismiss controls. Applying replaces the current question and previous exchange, resets attachment choices and still requires the normal send confirmation. Recovering a saved draft also asks before replacing local text.
- **Handover:** changing text or the sharing checkbox registers the note. Reverting both to their confirmed values clears ordinary dirtiness. The save captures one family, note revision and membership revision. An uncertain result keeps input and prevents another save. Checking reads the current note; only the expected next revision, matching membership, text and sharing values confirm that submitted result. Otherwise the user can review the read and explicitly replace local input with it. A submitted operation may still finish after leaving; no read or discard cancels it.
- **Phone memo:** the prepared public template can be reopened; actual text edits additionally protect leaving the family area. An intentionally blank edited memo is preserved. Closing or replacing an edited memo asks for confirmation.
- **Contact progress:** edited, saving and unresolved results remain discoverable, including progress for contacts no longer listed publicly. Returning opens the existing contact editor. A separate uncertainty flag prevents validation messages or later edits from hiding an unknown result. An ordinary edit restored to the baseline is no longer treated as dirty.
- **Consultation sheet:** selected options, questions, preview edits and unapplied incoming content can be resumed without being applied automatically. Opening an existing saved material establishes its baseline; a confirmed save uses the returned material's content. Changes to fetched contact labels or the current date do not by themselves mark that material edited. Earlier edited versions kept in session memory continue to protect leaving; they can be explicitly discarded without changing the current sheet or saved material.

## Ownership, privacy and limits

Continuation metadata stays in the authenticated family session. It contains translated status keys, counters and routing identifiers, not questions, health text, profile fields or contact names. Existing opt-in server drafts are separate and still require explicit recovery. Public and institution directory previews can render the shared components without a family provider; work registration is a no-op there. The chat and support directory have distinct work identities so their phone memos do not overwrite each other.

Entrance switching, intentional logout and browser refresh/close use the existing leave protection for registered drafts, unread answers and unresolved operations. Browser warnings depend on platform support. Session expiry and cross-tab account changes still clear private UI immediately. Late chat callbacks do not clear a server draft after their page unmounts; handover callbacks are invalidated after their selected family is lost or changed.

This is session continuity, not full restoration after a refresh or device change. Not every editable control is registered: family-sharing permission edits, institution invitation inputs, notification/security settings, emotional check-in and night-mode forms retain their existing behavior. Institution/operator pages retain their own existing draft and leave handling. Completed work does not establish that every form is protected, that an unknown write was cancelled, or that runtime acceptance passed.

## Pending acceptance

Source reading, cross-review, Git whitespace checks and the publication privacy scanner are the verification scope. No app/server, build, lint/parser/compile check, automated test, database migration, browser interaction or real AI call was executed.

When runtime validation is authorized:

1. Edit Profile, switch family pages, return through the strip, and discard with both confirmation choices. Change language while saving and verify it remains dirty. Simulate a lost response and compare the read-only result without another POST.
2. Leave Chat during processing. Confirm the new-answer cue persists, then explicitly read it and verify focus/scroll begins at the warnings. Repeat with a newer user/error message below the unread answer.
3. Keep a question and selected attachments, open a different suggested question, then apply/dismiss it. Repeat during an AI request and with a server draft awaiting recovery. No proposal or navigation action should send AI input.
4. Edit or deliberately clear a phone memo, change support steps, filter services and return from both chat and support. Verify the two memo instances remain independent and the right editor receives focus.
5. Edit contact progress, revert its fields, simulate an unknown save, then trigger time validation. Uncertainty must remain visible. Resume an archived contact and verify no automatic call, appointment or write.
6. Open an existing saved consultation sheet without edits; confirm it is not dirty. Edit options/text, save and lose the response, check the existing packet flow, and verify continuation reflects the correct input baseline. Print/download actions must not imply a server save.
7. Edit a handover note, collapse/reopen it, switch pages and return. Simulate save success, lost response, another device changing the note and membership revocation. Unknown writes must not be automatically repeated, and a late response must not overwrite another family's form.
8. Cancel and accept entrance switches/logout with pending work; check refresh warnings, account expiration and cross-tab logout. Review phone widths, long Japanese text, high contrast, keyboard focus and screen-reader announcements.
