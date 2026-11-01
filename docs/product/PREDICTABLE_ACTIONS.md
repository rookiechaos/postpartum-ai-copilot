# 送る内容と次の操作が分かる画面

Source revision: 2026-10-31. Implementation and source review only; app startup, builds, tests and browser acceptance have not been performed.

## Plan

The application already supports interrupted records, questions and consultation materials. This revision extends that consistency to emotional check-in, night support and family-sharing preferences, and makes a growing continuation list easier to scan.

| Priority | Gap | Implementation |
| --- | --- | --- |
| First | Emotional measures begin at 5 even when the user has not answered. | Each measure starts unanswered. All three are explicitly selected before the existing AI check-in request can be sent. Notes remain optional. |
| First | Editing check-in or night input does not reliably require new AI agreement; Enter or switching a night tab can start a request. | Show the current input and attachment choices, bind agreement to the payload and language, and require a labelled button for each AI request. Tab changes only change the view. |
| First | Night support disappears when closed; failures and new answers are difficult to resume. | Keep the visited night screen in the authenticated session, preserve input and results, show inline failures, and provide explicit return/read controls. |
| Next | Family-sharing edits are absent from continuation and unknown writes lack a clear result check. | Compare against confirmed preferences, register edited/pending work, offer explicit discard and read-only result comparison, and retain revision/access checks. |
| Next | More registered tasks make the shared list harder to scan. | Surface the first processing/review task outside the disclosure and allow filtering the full list by page. Counts come from the same registry as the rows. |

All changes use the existing React components and APIs. No dependencies, backend endpoints, database tables, migrations or browser stores are added.

## Emotional check-in

Unanswered is distinct from a selected value of 5. The numeric questions keep the existing 1–10 range and service contract; the interface does not treat the controls as a diagnosis or infer unanswered values. The existing non-clinical notice and direct support directory remain available.

The send review describes the current values, optional notes, language and history choice. Agreement is scoped to that input. Editing it or starting a new request requires agreement again. A synchronous request lock prevents repeated clicks; a form submission or Enter key does not trigger an AI call. Input remains available after failure, and retry is a new explicit action.

The result stays associated with the submitted snapshot even if the current form changes. A new request that would replace an unread answer requires confirmation. Known failure, service unavailability and an unknown request outcome have separate messages; retry creates a new AI request and does not cancel or recover the old one. Generic draft, processing and result metadata enters the existing session-work registry; private answers and notes stay inside the component. Returning only focuses the current form or result. No previous mood history is attached unless the user chooses it.

## Night support

The night screen stays mounted after its first visit until the authenticated family session ends. Closing it returns to the family page; reopening preserves its query, previous answer and fetched guides. This is in-memory continuity, not restoration after refresh or a device change.

Night Help uses the existing AI crisis endpoint. Its review names the question, language, optional profile and night-response mode; care records are explicitly excluded. The user chooses profile attachment and confirms the current input. Editing, changing language, changing the section or submitting clears agreement. An explicit send button is the only send trigger. A failed request keeps input and displays a persistent message; retry requires a fresh choice. Previously unread answers are not silently replaced.

Relaxation, breathing and safety content are **prepared service guides**, as shown by the existing backend implementations. They are fetched by explicit read/load controls and cached in memory by language; switching a tab does not call the service. These guide requests do not send the user's question or profile to AI. Cached content can be reopened without another request, and a failed refresh preserves the last fetched guide. Source review establishes this distinction; no live endpoint was called during implementation.

New night answers appear in continuation. Only an explicit result-view action clears that cue. The compact human-support directory remains available, and important answer warnings precede the answer text.

## Family sharing

The baseline is the last confirmed preference set for the selected family. Returning fields to that baseline clears ordinary unsaved state. Discard is explicit and resets local inputs only; it is not a save or a permission change.

Saving captures the family, account, membership revision and chosen preferences. Input and family changes cannot silently redirect that operation. An uncertain response keeps its snapshot and blocks a fresh preference write. Checking reads current membership preferences; an exact matching next revision confirms the result. A different read is shown for review, and adopting it requires a separate confirmation. Reading or returning to the editor does not enable sharing.

The existing conflict, membership/access and family-switch confirmations remain in force. Invitation-link controls are disabled while the parent preference write is busy or unconfirmed, since changing sharing also changes the issuer's membership revision. Ending an uncheckable pending result is an explicit decision and does not cancel an already submitted request. Account/session cleanup continues to take priority over leave warnings.

## Continuation and interface direction

The strip's visible processing/review count covers all pages, even while its expanded list is filtered. Its shortcut only returns to an existing task. It never retries a write, selects sharing, restores a draft or sends AI input. Unread chat, night and check-in results can be included alongside critical processing/unknown-result work. A page filter with no rows keeps its controls and a clear return to all pages.

This revision follows the repository's existing palette, typography and mobile navigation. The `design-taste-frontend` skill's app-screen guidance informs quiet form groups, honest empty states, touch targets, scoped colour and a visible primary job. The product question is “what will I send, and what still needs my attention?” Native labelled controls and actual task counts carry that answer; no sample family data or invented metrics are added. No direction-draw, lint, browser inspector, screenshots or visual score was produced because the user requested source-only work.

## Limits and pending acceptance

The new work entries contain generic translation keys, counters and navigation destinations, without health text, profile values or family names. Attachment previews show the profile/history choice; stored profile and history values are read by the existing backend and are not frozen or fully previewed by this change. Existing opt-in server drafts and sharing permissions are unchanged. Session expiry, logout and cross-tab account changes still clear private UI. This revision does not provide offline storage, cross-device restoration, automatic clinical triage or protection for every editable form. Notification/security settings and invitation inputs retain their existing behavior.

Source review, cross-review, Git whitespace checks and publication privacy scanning are the verification scope. The following scenarios remain unexecuted:

1. Leave check-in questions unanswered, explicitly choose each value, change language/history/notes after agreement and verify the button is disabled until renewed agreement. Enter, form submit and repeated clicks must not create extra requests.
2. Submit check-in, switch pages and return through continuation. Verify the result names the submitted input, edits do not rewrite it, failures retain input and only explicit review clears its cue.
3. Open each night section, confirm tabs make no request, read a guide, switch away and return to its cached version. Change language and simulate a guide failure without losing the last fetched content for that language.
4. Send a night question with and without profile attachment. Check the actual request excludes care records, changing input invalidates agreement, failure keeps the question and a hidden result never steals focus. Close/reopen the night screen and review a new answer through continuation.
5. Edit/revert/discard sharing preferences, save successfully, lose a response and compare a read-only result. Repeat with an external membership change and revoked family access. No read, resume or discard may issue a preference write.
6. Register work in multiple pages, filter by each page, and verify counts, empty state, shortcut scope and navigation. Confirm unknown-result work remains discoverable regardless of the filter.
7. Check phone/tablet layout, long Japanese copy, high contrast, keyboard focus and screen-reader announcements. Repeat account expiry and cross-tab logout during requests; no prior account input or callback should reappear.
