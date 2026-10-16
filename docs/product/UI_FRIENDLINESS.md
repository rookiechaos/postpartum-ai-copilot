# UI refinement for first-time family and community use

The subsequent [Japanese family and local-service revision](JAPANESE_EXPERIENCE.md) refines wording, branding, operator identity, feeding fields, save states and local eligibility guidance. Its optional public directory field requires a matching backend/frontend deployment; the source-only acceptance restriction continues.

This revision implements the product UI review for small Japanese family and community pilots. Work is **source only**: no application, worker, dependency installation, build, lint/parser, tests, browser, migration, print/QR check or real-data workflow was run. Source inspection and `git diff --check` do not verify rendering, accessibility or runtime behavior.

## Family flow

Home prioritizes quick records, recent personal records, then optional family handoff. Saving a quick event shows its category, recorder and JST time, with correction and the existing eight-second undo. Recent rows also offer correction. Relative event time is shown alongside the exact JST date/time, never instead of it; the clock refreshes once a minute per visible list. Future timestamps do not receive a misleading past-time label. These times do not suggest when care should happen next.

Home correction sends an owner-read record snapshot to the existing record form. It retains the immutable record key and revision, so an intervening modification/deletion still produces a conflict instead of being overwritten. New navigation requests are consumed once. An existing input, pending write or recovery candidate remains in place; a separate request allows the user to resolve the write/recovery choice and confirm replacement. A first navigation may open after draft preferences finish loading only when there is no candidate, pending save or edited input. Opening an editor does not save a record.

Family handoff is a disclosure after recent records. No family is selected automatically. Shared records refresh only while that disclosure and Home are visible; hiding it clears the fetched shared snapshot so reopening waits for a fresh read. An unreceived snapshot is not presented as an unknown event. The private/shareable note editor is a separate disclosure; collapsing either disclosure keeps its local input. Sharing still requires the explicit checkbox and save, membership revisions and the existing seven-day access boundary.

The mobile menu is Home → Records → Ask AI → Help → Settings, with the Japanese AI label 「AIに聞く」 distinct from 「相談先」. Welcome offers Start recording now as its primary action; supplying a profile is a secondary, optional path. The simulated record/find/correct exercise has one persistent entry on Home, rather than being repeated in sign-in and welcome. It never writes real records.

## Asking AI and contacting people

An AI answer keeps warnings before the full answer. Suggestions, extracted questions, the opening excerpt, supplied context and actual retrieved source links are available in an additional-information disclosure. The excerpt remains labeled as an excerpt, not a complete clinical summary. Continue this question and Prepare a consultation question stay outside the disclosure. Moving to the latest generated answer positions the conversation at its opening/warnings without scrolling the document; reading earlier messages keeps the existing new-message action. Returning to the page without new messages preserves its reading position and does not create a new-message notification.

One send area groups the current question, optional previous exchange, profile choice, outgoing-content preview, processing information and explicit consent. Editing a question, picking a prepared question or changing an attachment resets consent. Successful sends reset profile/previous-exchange selection and consent; a failed send preserves the input for a deliberate retry. No new automatic context, send, sharing or AI analysis is introduced.

Human-help cards initially show name, area, published contact hours and call/booking actions. Audience, cost, application steps and preparation expand on demand. Pause notices and available alternative-contact instructions remain visible, and paused services still hide booking links. Emergency 119 stays above the local directory; an adjacent disclosure identifies #8000, #7119 and official local-directory guidance, including when the local API fails. Public contact hours are not represented as live availability.

Progress summaries explicitly say Your own note. Waiting/booked states do not imply confirmation from a service; phone/booking actions never update them. Purpose filters and details keep editors mounted; the parent editor map still protects unsaved progress when a contact disappears or moves to the archive. Reload actions say when unsaved input will be discarded, and still require confirmation if edited. Phone scripts and sheet handoff retain the existing edit/review/selected-slot flow.

## Institution maintenance

The maintenance overview counts contacts needing review, contacts with unpublished changes (including removals), and contacts paused in the draft. Each contact shows its own review/change badges; paused draft and published states have different labels. Change detection uses immutable resource keys, so equally named services are not confused. Business information changes continue to appear in the full publication diff/status rather than the contact count.

Change phone and Edit pause or reopening select a small field group in the same draft. Switching tasks or contacts retains other edits in the parent profile. Validation/error links open the full editor and focus the requested field. Every edit invalidates preview. Saving a draft still saves the whole workspace; publication still requires the existing explicit preview and revision check. These shortcuts do not immediately publish a pause, book a contact or change a household record. Unsaved-navigation guards and publication-history restoration remain in place.

## Presentation and privacy

The existing green palette, text resizing, focus outlines, high contrast, reduced motion and mobile safe-area navigation remain. New primary actions and disclosures have a minimum 44px touch-target goal in CSS; selected filters carry text/pressed state rather than color alone. Subordinate information uses spacing/disclosures instead of more nested cards. Japanese and English text live in the `friendly` translation group.

No dependency, backend endpoint, schema, migration, health-text browser storage or telemetry field is added. Existing optional server drafts, account teardown, API response-generation checks and private sharing permissions remain authoritative. This edit does not repeat or extend the earlier Git-history privacy audit, and it is not a deployment.

## Pending acceptance after execution is authorized

1. At 320/375/768px and desktop, with Japanese/English, larger text, high contrast and night mode, inspect all primary actions, disclosures, five navigation labels and the mobile keyboard. Verify keyboard/screen-reader labels and focus, including the newly revealed record form and institution field groups.
2. Without instructions, complete record → find → correct; check receipt content, eight-second undo expiry, original request-key retry after lost responses, exact JST/relative time, midnight and device-clock changes. Delay draft loading; restore/discard a candidate, return with edited input or a pending write and confirm nothing is replaced automatically. Race a home snapshot against edit/delete on another screen and verify revision rejection.
3. Select a family, expand/edit/share a note, collapse/reopen both disclosures and switch pages. Verify inputs and explicit sharing choices survive, polling stops while hidden, and lost membership never reveals inaccessible data.
4. Read a long AI answer with warnings, expand sources/context and continue one selected exchange. Change question/profile/previous selection after consent, inspect outgoing content during waiting and verify deliberate retry. Read earlier messages while a response arrives; there must be no document scrolling or focus theft. Confirm the latest-answer action reveals the warning/opening and private consent resets after success.
5. Filter services, edit progress, collapse its card, pause/remove a service and return through archived progress. Verify unsaved editors survive and cannot create a new progress record for a removed service. Check emergency/national guidance during API failure, manual status labels, call-script editing and explicit sheet review.
6. For two equally named contacts, change a phone in the compact editor, switch task/contact, save the workspace draft and inspect the before/after preview. Check counts for added/changed/removed contacts and distinguish draft/published pause. Trigger validation on an absent field/contact and verify the complete editor opens. Repeat revision conflict, publication, restore and leave-guard scenarios from [UI architecture](UI_REFINEMENT.md).

The scenarios above are outstanding, not passing test results.
