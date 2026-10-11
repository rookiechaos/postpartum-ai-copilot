# Frontend · 家庭と小さな支援機関の入口

React 18 / Vite / i18next web app for small Japanese postpartum-care pilots.
See the [main README](../README.md) for the product scope and complete backend/worker setup.

## Entrances

| URL | Experience |
| --- | --- |
| `/` | Public entrance selection, national support contacts and operator-maintained local directory |
| `/family` | Personal sign-in, optional two-step welcome, care records, guided questions and consultation summary preview |
| `/organization` | Staff sign-in and separately authorized public directory editor |

The browser path selects an interface; it does not grant permissions. The backend checks `INSTITUTION_USER_IDS` for every management request.
Organization editors cannot read other users' private records through that role. Each deployment maintains one public directory.
Production hosting must serve `index.html` for both entrance paths.

## Family experience

- Home actions open the corresponding recording form, including feeding, diaper, baby sleep and pumping.
- Parent mood/recovery records remain separate categories. Fields are optional and failed saves preserve form input.
- Situation cards prepare editable questions without sending them automatically.
- AI features require acknowledgement of external processing. Normal record loading and saving do not trigger AI summaries.
- AI output is labeled. The interface does not present heuristic confidence percentages, medical verification badges or clinical risk scores.
- Consultation summaries are generated without AI. Parent records and free text have separate opt-ins and are excluded by default.
- Users review/edit the actual text downloaded; the app does not send it to an institution or revoke shared copies.
- Japanese and English are supported, with Japan-specific help contacts in either language. Dates and calendar-day statistics use JST.

## Organization experience

Authorized editors maintain public business contacts, hours, retention/deletion-request information and up to ten local source links.
Each source has a description, optional hours and a manually entered checked date. The backend validates HTTPS URLs and dates.
The family link is navigation only; it does not enroll a household or share health data.

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
| `src/components/Dashboard.jsx` | Three main family actions and today's recorded activity |
| `src/components/TrackingPanel.jsx` | Care recording and optional analysis |
| `src/components/AIUseNotice.jsx` | External AI processing acknowledgement |
| `src/components/SupportDirectory.jsx` | Static national contacts plus public local directory |
| `src/components/ShareSummary.jsx` | Opt-in consultation summary and editable preview |
| `src/utils/careSummary.js` | Summary field allowlist |
| `src/utils/japanTime.js` | UTC timestamp normalization and JST display |
| `src/i18n/locales/` | Japanese and English UI text |
| `public/offline.html` | National contact information when the app cannot load online |

## Verification

From the repository root:

```bash
node --test tests/regression/frontend_security.test.cjs tests/regression/frontend_tasks.test.cjs tests/regression/frontend_review.test.cjs tests/regression/japan_pilot.test.cjs
```

The component regressions execute real transpiled JSX with controlled React hooks and API fixtures. They require an installed TypeScript module;
set `REVIEW_TYPESCRIPT_PATH` if it is outside normal module resolution. These checks do not replace a production build or real-browser acceptance.
See the [Japan pilot guide](../docs/product/JAPAN_PILOT.md) for phone-based acceptance scenarios and privacy limits.
