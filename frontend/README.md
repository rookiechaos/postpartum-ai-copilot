# Frontend · 家庭と小さな支援機関の入口

React 18 / Vite / i18next web app for small Japanese postpartum-care pilots.
See the [main README](../README.md) for the product scope and complete backend/worker setup.

## Entrances

| URL | Experience |
| --- | --- |
| `/` | Public entrance selection, national support contacts and operator-maintained local directory |
| `/family` | Personal sign-in, optional two-step welcome, care records, guided questions and consultation summary preview |
| `/organization` | Staff sign-in and separately authorized public directory editor |
| `/operator` | Administrator-only manual account requests and operational statistics |

The browser path selects an interface; it does not grant permissions. The backend checks `INSTITUTION_USER_IDS` for every management request.
Organization editors cannot read other users' private records through that role. Each deployment maintains one public directory.
Production hosting must serve `index.html` for `/family`, `/organization` and `/operator`. Operator access uses `ADMIN_USER_IDS`, separately from institution editing.

## Family experience

- Home directly saves explicitly labeled diaper/feeding events with an eight-second undo, shows recent own records and links to detailed/backdated forms. The first-use demonstration never writes real records.
- A shared token palette controls surfaces, actions, links, focus and high contrast. Explicit combined-mode rules keep help-card surfaces, headings and links consistent when high contrast and night mode are both selected. Mobile navigation uses five visible bottom buttons; entrance switching/sign-out live in Settings. Login/welcome use document scrolling, and home avoids nested page padding.
- Parent mood/recovery records remain separate categories. Fields are optional and failed saves preserve form input.
- Records can use a chosen JST time within today and the previous 364 Japan calendar days, be corrected, or deleted with an 8-second screen-memory undo. Type changes retain the time/general note. Corrections/deletions include immutable identity and revision preconditions to reject stale changes.
- Visited family pages preserve drafts, answers and AI progress in the login session. Reload/entrance changes/logout clear screen drafts; saved records remain on the server.
- Optional account-bound recovery is off by default and supports record input/pending saves, question drafts/selected context and working consultation sheets/questions. Pending detailed records retain their request key and timestamp even with empty optional fields. Restoring requires confirmation; chat consent is reset and recovered sheets need fresh review. It does not resume running AI tasks or provide offline saving.
- Continue this question previews one previous question/answer pair and attaches it only after explicit selection. The actual current question and attachment choice are visible before sending.
- Chat preserves answer line breaks, uses a growing multiline input, and groups context/attachment/consent controls in one composer. Its thread scrolls independently; asynchronous replies do not scroll the whole document or pull readers away from earlier messages. A submitted snapshot remains visible while waiting.
- Situation cards prepare editable questions without sending them automatically.
- AI features require acknowledgement of external processing. Normal record loading and saving do not trigger AI summaries.
- Per-request profile, parent-record and note attachment choices default off. Current input and optional attachments are described before sending.
- AI output is labeled. The interface does not present heuristic confidence percentages, medical verification badges or clinical risk scores.
- Consultation summaries are generated without AI. Parent records and free text have separate opt-ins and are excluded by default.
- Users review/edit the actual text downloaded; the app does not send it to an institution or revoke shared copies.
- Record/option changes preserve consultation edits and block stale print/download. Regeneration presents a separate candidate when edits exist, and accepted replacements keep prior edits for copying. CSV backups preserve all supported fields independently of consultation formatting.
- Japanese and English are supported, with Japan-specific help contacts in either language. Dates and calendar-day statistics use JST.
- Header and Settings language controls share the active i18next display choice. Loading account data does not change it; explicitly saving profile settings writes the current language to the account. Chat has one persistent live region for waiting/answer status, with a separate visual reminder in the composer.
- Human-help contacts can be filtered by purpose. Editable phone scripts can be copied or placed in a selected consultation-question slot after review.
- Contacts and consultation sheets have separate views which preserve their mounted state. Home/Settings actions labeled as finding human help explicitly open contacts; a plain menu return preserves the last view. View requests are consumed once, and opening contacts does not reapply or erase an earlier incoming question. Preparing a script or handing it to the sheet reveals the appropriate review heading without choosing or replacing a question slot automatically. Applying the incoming question focuses the selected question textarea; dismissing it or deleting the working sheet returns focus to the sheet heading.
- Family handoff uses separate existing accounts, invitations and independently selected baby/parent/notes sharing. Membership alone shares nothing. Members record/correct their own data; revocation/leave restrict later shared reads. The backend enforces the seven-day shared-record limit. Sharing writes carry the reviewed member revision; conflicts pause saving until an explicit reload of the latest settings.

## Organization experience

Authorized editors maintain public business contacts, hours, retention/deletion-request information and up to ten local source links.
Each source has a description, optional hours and a manually entered checked date. The backend validates HTTPS URLs and dates.
The family link is navigation only; it does not enroll a household or share health data.
Contacts are edited individually. A shared staff draft is saved separately from publication and may be incomplete. History shows publication changes; restoring stages an earlier version as draft. Publication still needs a preview. Revisions prevent concurrent overwrites, and maintainer/next-review fields support the review queue. Reloading the server draft disables editing, save, preview and restoration until the request completes or fails.
Contact fields are grouped into basic, service-detail and review sections. A sticky action bar keeps draft save, preview and publication available. Validation includes contacts that are not currently selected; linked, localized errors select the contact, expand its section and focus the field. Saving/previewing normalizes phone digits/dashes and URL whitespace. API validation metadata retained by the client contains paths/codes only, not submitted values.
Successful publication replaces the preview with a result section and an explicit control to open the published information. Focus moves to the result after rendering if it was still on the submitting control or returned to the document body; a deliberate move to another control is preserved.
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
| `src/i18n/locales/` | Japanese and English UI text |
| `public/offline.html` | National contact information when the app cannot load online |

## Verification

The current product improvements were edited without running the app, installing packages, building, testing, scanning or browser/print/QR verification, as requested. The earlier `qrcode` 1.5.4 dependency is declared but was not installed. This UI phase adds no dependencies. See [the first change guide](../docs/product/PRODUCT_IMPROVEMENTS.md), [the seven-item polish guide](../docs/product/PRODUCT_POLISH.md), and [UI architecture and pending acceptance](../docs/product/UI_REFINEMENT.md) for implementation limits and migration contracts. Commands below are for later verification.

From the repository root:

```bash
node --test tests/regression/frontend_security.test.cjs tests/regression/frontend_tasks.test.cjs tests/regression/frontend_review.test.cjs tests/regression/japan_pilot.test.cjs
```

The component regressions execute real transpiled JSX with controlled React hooks and API fixtures. They require an installed TypeScript module;
set `REVIEW_TYPESCRIPT_PATH` if it is outside normal module resolution. These checks do not replace a production build or real-browser acceptance.
See the [Japan pilot guide](../docs/product/JAPAN_PILOT.md) for phone-based acceptance scenarios and privacy limits.
