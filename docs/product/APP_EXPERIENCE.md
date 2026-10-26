# アプリ全体の使いやすさと復帰の改善

Source revision: 2026-10-22. Implementation and source review only; application, build and runtime acceptance have not been executed.

The 2026-10-25 [interruption-recovery revision](INTERRUPTION_RECOVERY.md) extends draft coverage, new-answer review and save-result handling. Coverage limitations below describe this document's original revision; use the newer guide for the current scope.

## Plan and implemented scope

The next improvement is to connect the existing features: help a family resume an interrupted task, find a relevant contact, and recover from a page failure. This revision changes the frontend without adding dependencies, APIs, database tables or migrations.

| Direction | Implemented behavior | Main source |
| --- | --- | --- |
| Continue an interrupted task | A collapsed pending-work strip follows the five family pages. It opens registered record work, timers, chat work and unconfirmed consultation-material saves. Important pending results appear first. | `PendingCare.jsx`, `CareSession.jsx`, `App.jsx` |
| Preserve control over chat | Chat registers only generic status metadata. Its continue action focuses the existing thread, composer or consultation-question editor. It does not replace text, select attachments, recover a draft or send a request. | `ChatInterface.jsx` |
| Make navigation predictable | A skip link moves to the active page. Family handover and emotional check-in have an explicit Home return. `/` searches only the active visible page; `?` opens Settings → Help. Typing, composition, modifier keys and dialogs take precedence. | `App.jsx`, `Settings.jsx` |
| Find local help | Search public service names, areas and descriptions alongside the existing purpose filter. Show matching count, a clear action and useful empty states. Japanese fullwidth text is normalized for matching. | `SupportDirectory.jsx`, `SupportDirectorySearch.css` |
| Recover from a broken page | Each mounted family page has an independent Japanese/English error boundary. Other family pages stay mounted. Entry, sign-in, institution, operator, onboarding, invitation and night screens also have recovery controls. | `ErrorBoundary.jsx`, `App.jsx` |

## Interruption and leave behavior

The shared strip reads the in-memory `CareSession.work` registry; it is not a new draft store. It shows translated task labels and destinations, without care notes, questions, names or timestamps. Home retains its existing detailed ContinueCare view. The new strip starts collapsed to avoid repeating those cards on the first screen.

Active timers and local record/chat drafts mark `protectLeave`; uncertain writes already mark `critical`. Pending or unresolved consultation-material writes are also critical. Switching away from the family entrance or intentionally logging out asks for confirmation while this work is registered. A browser refresh/close requests the browser's standard leave warning. Browser support for this warning varies, especially on mobile.

Changing a family tab does not ask for confirmation because visited pages remain mounted. Expired sessions, account changes and logout from another tab still clear private screens immediately. A request already submitted to the server may finish after leaving; the leave prompt says so. Leaving does not cancel a save or AI request.

Recovery candidates already stored on the server can appear in the strip without triggering a leave prompt by themselves. The existing opt-in draft preference, account ownership and explicit restore/discard choices remain in effect.

This is deliberately bounded coverage. Settings edits, unsaved family handover edits, phone scripts, contact-progress edits and unsaved consultation-sheet text are not all registered in this strip. It must not be described as protecting every form. Full conversation restoration, offline saving and cross-device task synchronization are not provided by this change.

## Search and privacy

The search text is limited to 100 characters and remains in component memory. It is not sent to the API, analytics or browser storage. Matching uses a whitelist of already public service-card fields, NFKC normalization, lowercase conversion and whitespace-separated terms; every term must match. This is substring matching, not Japanese morphological or kana-equivalence search.

Filtering hides service cards without unmounting their controls. The operator contact, emergency/national entries, prepared phone explanation and contact-progress editors remain outside the result filter. Choosing a contact does not call it, book it or change its progress. Compact support omits search; institution directory preview uses the same public-card filtering.

Error fallbacks do not display or retain raw exception messages, stacks, component props or health text. Reporting uses the existing fixed React-error diagnostic type; affected API/tracker catch logs also use fixed messages. Changing language updates fallback copy. No real contact details, patient examples, credentials or addresses are introduced by this revision.

## What page recovery means

Reopening a failed page remounts only the boundary's subtree; it does not reload the browser. That page's in-memory inputs may already have been lost when it failed, and the fallback says so. The user should check saved records before trying another write. The boundary does not replay a save, accept an invitation or resend AI input. An invitation fallback can leave the invitation review without accepting it.

Root recovery is broader and can lose all in-memory page state. These boundaries handle React render/lifecycle failures; asynchronous operations still need their existing inline error and retry handling. The boundary supports a separately confirmed full browser reload, but current application integrations do not enable that option.

## Pending acceptance

No app/server startup, dependency install, build, lint, parser/compile checks, automated tests, browser interaction, migration or live AI call was performed. Source review, Git whitespace checks and publication privacy scanning are the verification scope for this change.

When runtime validation is authorized:

1. Enter a record, start a timer and draft a question; switch between all five pages, return through the pending strip, and verify text, selected subject and sharing choices. A chat return must produce no network write or new attachment consent.
2. Start a save or AI request, switch pages, and verify status updates without repeated submission. Cancel an entrance switch/logout and confirm the working view remains; confirm it and verify session cleanup. Repeat with an unresolved consultation-material save.
3. Exercise account expiration and cross-tab account changes with pending work. No leave prompt should prevent private-state cleanup or expose the prior account's content.
4. Use a keyboard with hidden retained tabs, closed details, a select, editable text, Japanese composition and an open modal. Verify `/`, `?`, skip navigation and explicit subpage returns; Escape must follow the modal's own behavior.
5. Search using fullwidth letters, mixed case, multiple words and no-match terms. Combine purpose filters, clear them, switch support steps and open the institution preview. Emergency/national contacts, current scripts and progress must remain available.
6. Introduce a controlled render failure in one family page, including a hidden tab. Verify other pages retain input, the fallback uses the selected language, hidden failures do not steal focus, and reopening never writes automatically. Check invitation exit, night-mode exit and account switching after a failure.
7. Review narrow phone layout, enlarged text, high contrast and screen-reader result announcements. Confirm the strip stays compact and all controls remain reachable above the bottom navigation.

After acceptance, the next product work should extend interruption coverage to the remaining edited forms using explicit ownership and state contracts, then use small-family and institution pilot observations to prioritize further changes. This document does not claim those later features are implemented.
