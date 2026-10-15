# Frontend · 家庭と小さな支援機関の入口

React 18 / Vite / i18next web app for small Japanese postpartum-care pilots.
See the [main README](../README.md) for the product scope and complete backend/worker setup.

## Entrances

| URL | Experience |
| --- | --- |
| `/` | Public entrance selection, national support contacts and operator-maintained local directory |
| `/family` | Personal sign-in, immediate recording with optional profile setup, care records, guided questions and consultation summary preview |
| `/organization` | Staff sign-in and separately authorized public directory editor |
| `/operator` | Administrator-only manual account requests and operational statistics |

The browser path selects an interface; it does not grant permissions. The backend checks `INSTITUTION_USER_IDS` for every management request.
Organization editors cannot read other users' private records through that role. Each deployment maintains one public directory.
Production hosting must serve `index.html` for `/family`, `/organization` and `/operator`. Operator access uses `ADMIN_USER_IDS`, separately from institution editing.

## Family experience

- Home prioritizes quick records → recent own records → optional family handoff. Quick-save feedback names the event, recorder and JST time, with an eight-second undo and correction action. Recent rows show relative and exact JST times and open the existing revision-guarded editor without replacing an unfinished form. Detailed/backdated recording remains separate. Welcome can proceed directly to recording; the single practice entry stays on Home and never writes real records.
- A shared token palette controls surfaces, actions, links, focus and high contrast. Explicit combined-mode rules keep help-card surfaces, headings and links consistent when high contrast and night mode are both selected. Mobile navigation uses five visible bottom buttons; entrance switching/sign-out live in Settings. Login/welcome use document scrolling, and home avoids nested page padding.
- Parent mood/recovery records remain separate categories. Fields are optional and failed saves preserve form input.
- Records can use a chosen JST time within today and the previous 364 Japan calendar days, be corrected, or deleted with an 8-second screen-memory undo. Type changes retain the time/general note. Corrections/deletions include immutable identity and revision preconditions to reject stale changes.
- Visited family pages preserve drafts, answers and AI progress in the login session. Reload/entrance changes/logout clear screen drafts; saved records remain on the server.
- Optional account-bound recovery is off by default and supports record input/pending saves, question drafts/selected context and working consultation sheets/questions. Pending detailed records retain their request key and timestamp even with empty optional fields. Restoring requires confirmation; chat consent is reset and recovered sheets need fresh review. It does not resume running AI tasks or provide offline saving.
- Continue this question previews one previous question/answer pair and attaches it only after explicit selection. The actual current question and attachment choice are visible before sending.
- Chat puts warnings before the full answer and folds supporting questions/context/sources. Follow-up and consultation-sheet actions stay visible. The growing multiline input, outgoing preview, attachment choices and per-send consent share one area; changing the question resets consent. Its thread scrolls independently and reveals a new answer from its opening; replies do not scroll the document or pull readers away from earlier messages. A submitted snapshot remains available while waiting.
- Situation cards prepare editable questions without sending them automatically.
- AI features require acknowledgement of external processing. Normal record loading and saving do not trigger AI summaries.
- Per-request profile, parent-record and note attachment choices default off. Current input and optional attachments are described before sending.
- AI output is labeled. The interface does not present heuristic confidence percentages, medical verification badges or clinical risk scores.
- Consultation summaries are generated without AI. Parent records and free text have separate opt-ins and are excluded by default.
- Users review/edit the actual text downloaded; the app does not send it to an institution or revoke shared copies.
- Record/option changes preserve consultation edits and block stale print/download. Regeneration presents a separate candidate when edits exist, and accepted replacements keep prior edits for copying. CSV backups preserve all supported fields independently of consultation formatting.
- Japanese and English are supported, with Japan-specific help contacts in either language. Dates and calendar-day statistics use JST.
- Header and Settings language controls share the active i18next display choice. Loading account data does not change it; explicitly saving profile settings writes the current language to the account. Chat has one persistent live region for waiting/answer status, with a separate visual reminder in the composer.
- Human-help cards show area, hours and call/booking actions first, with application/preparation details on demand. Purpose buttons filter contacts without losing their drafts. Progress is explicitly the person's own note, not service confirmation. Emergency/national contacts remain reachable without the local API. Editable phone scripts can be copied or placed in a selected consultation-question slot after review.
- Contacts and consultation sheets have separate views which preserve their mounted state. Home/Settings actions labeled as finding human help explicitly open contacts; a plain menu return preserves the last view. View requests are consumed once, and opening contacts does not reapply or erase an earlier incoming question. Preparing a script or handing it to the sheet reveals the appropriate review heading without choosing or replacing a question slot automatically. Applying the incoming question focuses the selected question textarea; dismissing it or deleting the working sheet returns focus to the sheet heading.
- Family handoff uses separate existing accounts, invitations and independently selected baby/parent/notes sharing. Membership alone shares nothing. Members record/correct their own data; revocation/leave restrict later shared reads. The backend enforces the seven-day shared-record limit. Sharing writes carry the reviewed member revision; conflicts pause saving until an explicit reload of the latest settings.
- Home's family overview requires an explicit household selection. It shows the latest shared baby-care event by category with recorder and retrieval time; missing records mean unknown. Each member saves their own optionally shared handover note with note/membership revision checks.
- Family managers can issue/revoke a one-use, 24-hour invitation link/QR. The link fragment is captured into memory and removed from the URL, then an authenticated review requires explicit joining. Initial sign-in and reauthentication after session expiry preserve the pending invite in this tab. Signing in as a different known account, explicit logout or another tab changing the session clears it. Account-ID invitations remain available.
- The example now demonstrates save → find → correct without any real record/AI write. Connection notices distinguish an unsent recording from an unconfirmed dispatched result; reconnection refreshes reads and never resends. An offline or rejected retry never downgrades a previously unconfirmed save to unsent. Existing optional server draft recovery remains the only persistent draft option.
- The v5 service worker ignores legacy sync tags and no longer reads or replays the old offline queue. Privacy settings offer explicit device-wide clearing of that old data; authentication-boundary cleanup also attempts it. This does not erase server records/drafts or current credentials, and blocked cleanup is reported by the explicit action.
- Human-help cards save private preparing/waiting/booked progress and a next-contact time in JST. Calls/booking clicks do not update it. No reminders or institution intake are implied. Historical progress and unsaved contact drafts remain available when a contact is removed. Contact drafts stay in the current account session's memory; they do not survive reload or logout. A removed contact with no saved progress cannot receive a new server entry, but its input can still be reviewed or explicitly discarded.
- Chat shows a labeled opening excerpt, actual submitted question/selected profile, extracted follow-up questions and actual retrieved-document URL metadata. Its full answer remains visible. A separately edited consultation question enters the existing sheet review only after confirmation.

## Organization experience

Authorized editors maintain public business contacts, hours, retention/deletion-request information and up to ten local source links.
Each source has a description, optional hours and a manually entered checked date. The backend validates HTTPS URLs and dates.
The family link is navigation only; it does not enroll a household or share health data.
Contacts are edited individually. A shared staff draft is saved separately from publication and may be incomplete. History shows publication changes; restoring stages an earlier version as draft. Publication still needs a preview. Revisions prevent concurrent overwrites, and maintainer/next-review fields support the review queue. Reloading the server draft disables editing, save, preview and restoration until the request completes or fails.
Contact fields are grouped into basic, service-detail and review sections. A sticky action bar keeps draft save, preview and publication available. Validation includes contacts that are not currently selected; linked, localized errors select the contact, expand its section and focus the field. Saving/previewing normalizes phone digits/dashes and URL whitespace. API validation metadata retained by the client contains paths/codes only, not submitted values.

The contact list highlights needs-review, unpublished-change and paused states, distinguishing draft from published pause information. Change phone and Edit pause or reopening open a small field group using the same workspace profile. Switching tasks retains other edits; saving still saves the whole workspace draft, and publishing still requires explicit preview and revision checks. Contact-change badges use resource keys rather than display names.
Successful publication replaces the preview with a result section and an explicit control to open the published information. Focus moves to the result after rendering if it was still on the submitting control or returned to the document body; a deliberate move to another control is preserved.
Service fields include application steps, preparation, fallback contact and pause/resume information. Paused services suppress booking links. Maintainer filtering and a field-level before/after publication diff support smaller maintenance tasks. Operators separately attest controlled manual account processing with required steps, next actions, reply times and immutable completion receipts; the UI does not execute password reset or erasure.
Operator request drafts use the same entrance and SPA Back/Forward leave guard as the institution editor. Canceling navigation retains input, and pending saves block navigation. Logout and reload/close are also guarded.
Unsaved local edits require confirmation for entrance navigation and SPA Back/Forward; cancel preserves the edits and restores tracked history. Reload/close has an unload warning. Saved staff drafts survive leaving the editor. Navigation is blocked while a save, restore or publication is pending.

## Development

From this directory:

```bash
npm install
cp -n .env.example .env.local
npm run dev
```

The development address is `http://localhost:3000`. Configure the browser-accessible API URL and async mode in the ignored `.env.local`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_ASYNC_MODE=true
```

`VITE_ASYNC_MODE` must match the backend `ASYNC_MODE`; async chat/analysis requires a running worker.
Vite environment values are applied at build time. Never place server API keys in `VITE_*` variables.

```bash
npm run build
npm run preview
```

## Main files

| File | Purpose |
| --- | --- |
| `src/App.jsx` | Entrance routing, authentication boundaries, account-scoped welcome and private navigation |
| `src/components/EntryScreen.jsx` | Public family / organization selection |
| `src/components/OrganizationPortal.jsx` | Public directory management with server authorization |
| `src/components/Dashboard.jsx` | One-tap recording, undo, recent own records and secondary help actions |
| `src/components/TrackingPanel.jsx` | Care recording and optional analysis |
| `src/components/ChatInterface.jsx` | Questions, explicitly selected follow-up context and session answers |
| `src/components/FamilySharing.jsx` | Separate-account invitations and category-specific sharing |
| `src/components/FamilyCareOverview.jsx`, `src/components/FamilyInviteLinks.jsx` | Explicit home handover and authenticated one-use invitations |
| `src/components/SupportProgress.jsx`, `src/components/ConnectionNotice.jsx` | Private contact progress and connection/save recovery guidance |
| `src/components/AIUseNotice.jsx` | External AI processing acknowledgement |
| `src/components/SupportDirectory.jsx` | Static national contacts plus public local directory |
| `src/components/SupportHub.jsx` | Separate contacts/sheet views with explicit user-initiated navigation |
| `src/components/ShareSummary.jsx` | Opt-in consultation summary and editable preview |
| `src/styles/tokens.css`, `src/styles/ui.css` | Shared visual tokens, contrast, view controls and institution layout |
| `src/utils/focusView.js` | User-initiated focus/scroll and expansion of containing details |
| `src/utils/directoryValidation.js` | Draft/publication field validation and safe API-error mapping |
| `src/utils/careSummary.js` | Summary field allowlist |
| `src/utils/useAccountDraft.js` | Optional account draft recovery, revision checks and save status |
| `src/utils/recordOperations.js` | Stable record request keys for retryable creation |
| `src/utils/japanTime.js` | UTC timestamp normalization and JST display |
| `src/utils/useConnection.js` | Device connection events without automatic writes or persistent input storage |
| `src/i18n/locales/` | Japanese and English UI text |
| `public/offline.html` | National contact information when the app cannot load online |

The care-flow revision is source only; no application, build, parser/lint, tests, QR/browser acceptance or real-data workflow ran. See [care-flow contracts and pending acceptance](../docs/product/CARE_FLOWS.md).

## Verification

This UI revision was edited without running the app, installing packages, building, parsing/linting, testing or browser/print/QR verification, as requested. It adds no dependencies. Source inspection and `git diff --check` do not establish runtime correctness. The earlier `qrcode` 1.5.4 dependency is declared but was not installed during these edits. See [the first change guide](../docs/product/PRODUCT_IMPROVEMENTS.md), [the seven-item polish guide](../docs/product/PRODUCT_POLISH.md), [UI architecture](../docs/product/UI_REFINEMENT.md), and [first-time-use UI changes and pending acceptance](../docs/product/UI_FRIENDLINESS.md) for limits and rollout contracts. Commands below are for later verification.

From the repository root:

```bash
node --test tests/regression/frontend_security.test.cjs tests/regression/frontend_tasks.test.cjs tests/regression/frontend_review.test.cjs tests/regression/japan_pilot.test.cjs
```

The component regressions execute real transpiled JSX with controlled React hooks and API fixtures. They require an installed TypeScript module;
set `REVIEW_TYPESCRIPT_PATH` if it is outside normal module resolution. These checks do not replace a production build or real-browser acceptance.
See the [Japan pilot guide](../docs/product/JAPAN_PILOT.md) for phone-based acceptance scenarios and privacy limits.
