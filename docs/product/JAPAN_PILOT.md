# Japan family and small-organization pilot

## Scope

The first deployment supports a small number of Japanese households and one local service directory.
Use `/family` for personal care records and guided questions; use `/organization` for public information management.
Both entrances share account authentication. Entrance selection does not grant privileges.

This release replaces the old nine-step tutorial with a two-step welcome flow. Optional profile information can be skipped.
Skipped or unfilled welcome fields preserve existing profile data, including when returning from a new browser.
Profile updates merge supplied fields. Settings can be edited and saved only after loading succeeds; failed loading offers a retry.
The home page keeps recording, guided questions and human support visible even when records are empty or a request fails.
Record loading and saving do not invoke external moderation or AI summaries. AI actions require an explicit UI acknowledgement of external processing.
This acknowledgement is an interaction safeguard, not a server-side legal consent ledger.
Sleep charts show the total recorded minutes per Japan calendar day. Mood charts use the latest record for each day; a missing value stays blank.
Saving a record refreshes open charts without resetting the selected time range. Night resources honor the current interface language, including regional tags such as `ja-JP`.

## Organization access

Configure `INSTITUTION_USER_IDS` using verified staff account IDs, not email addresses. It is independent of `ADMIN_USER_IDS`.
The permission grants only GET/POST access to the deployment's public directory. Existing owner checks continue to protect private APIs.
Organization editors do not receive family lists, chat histories, mood information or alerts.
The family entrance link is a navigation link, not an invitation token, enrollment mechanism or consent to sharing.

All directory editors manage one shared profile. Deploy separate instances for separate organizations until tenant isolation is implemented.
Public fields must contain business contacts and public source information only. URLs require HTTPS without embedded credentials.
Dates reflect when an operator actually checked a source; they are not generated claims of professional review.

## Information and safety

- Display Japan's 119 and #8000 independently of API/model availability. Explain #8000's regional opening hours.
- Link to official #7119 coverage information, including applicable ages and service times; do not imply universal coverage.
- The pre-cached offline page includes national contacts. It does not promise offline record saving or access to cached health data.
- Label AI-generated text. Do not display heuristic confidence percentages, medical verification badges or a reassuring clinical risk score.
- Emotional reflection uses the request language. Legacy API risk fields remain compatibility metadata, not validated clinical assessments.
- Display local contacts and hours without implying the organization monitors users or receives messages through the app.
- Do not let AI invent local eligibility, subsidy amounts, prices or opening hours. Register links to actual municipality/provider sources.

Official sources checked for the product review on 2026-10-11:

- [MHLW: child medical telephone advice #8000](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/newpage_55223.html).
- [FDMA: #7119 coverage and use](https://www.fdma.go.jp/mission/enrichment/appropriate/appropriate007.html).
- [Children and Families Agency: maternal and child health](https://www.cfa.go.jp/policies/boshihoken).
- [PPC: generative AI and personal information](https://www.ppc.go.jp/news/careful_information/230602_AI_utilize_alert/).

## Sharing and retention

The consultation summary is generated from the signed-in user's own recent tracking entries, without AI.
By default, it includes feeding, diapers, baby sleep and pumping only. Parent mood/recovery and free text have separate opt-ins.
Identity fields, chat content and unknown record types are excluded. Users preview and can edit the actual text downloaded.
Nothing is automatically posted to an institution. Downloaded copies cannot be revoked through the app.

Records remain server-side. External AI features transmit the relevant input/context to the configured provider.
Sign-out and account changes clear private state in other open tabs and invalidate old responses. Same-account token refresh preserves the mounted page and active tasks.
Operators must describe actual retention, processing and deletion-request handling in the public profile.
The description does not implement automatic deletion. Self-service account erasure, password reset, granular institutional teams and institution messaging are not part of this release.
Do not treat a text notice or a local deployment as proof that information stays on the device.

## Pilot acceptance

Try one organization with 5–10 households. Ask people unfamiliar with AI to complete these tasks using a phone:

1. Choose the family entrance, create an account and skip all optional profile fields. Later, return from a new browser and skip again; existing profile information must remain intact.
2. Save a feeding record, then use the home diaper button to open the correct form. Keep a chart open while saving another record; its values should update and its selected range should stay unchanged.
3. Cause a failed save; confirm the entered information is preserved for retry. Delay or fail settings loading; confirm editing and saving are blocked until a successful retry.
4. Choose a situation, edit the proposed question, acknowledge external processing and send it once.
5. Locate national help without signing in and when the local directory cannot load.
6. Prepare a consultation summary. Confirm mood, recovery and free text are absent until selected; inspect the downloaded content.
7. Open two tabs, then sign out or sign in as another person in one tab; no previous person's private screen state should remain in either tab, including after delayed requests finish.
8. Try the organization URL with an ordinary account; confirm editing is denied and private family records are not exposed.
9. As authorized staff, publish a business contact and a checked source link. Confirm the family view shows the saved information.
10. Check records on both sides of Japan's midnight, mobile labels, keyboard focus and low-light readability. Switch interface language and confirm night resources use the selected language.

Observe whether people can finish without prompting, understand the AI label, find human help and control shared content.
Measure the staff effort required to maintain contacts and respond through existing real-world channels.
Have Japanese-speaking care professionals review public-facing wording and local information before inviting real households.

## Automated verification scope

`tests/regression/japan_pilot_checks.py` exercises actual HTTP routes and SQLite persistence with controlled authentication and provider fixtures.
`tests/regression/japan_pilot.test.cjs` exercises actual transpiled components and pure summary/time utilities with controlled React hooks.
`tests/regression/review_3961c93.test.cjs` covers shared browser storage with separate API modules, queued cross-tab events, profile loading/skip behavior and chart refresh races.
Existing security, task/session and privacy suites remain part of verification.
HTTP regressions also verify that validation logs exclude passwords and health notes and that private record saving never calls external moderation.
These tests do not establish clinical accuracy, a live provider integration, PostgreSQL compatibility or browser usability.

### Validation of this change

- 95 backend regression checks passed: 24 Japan pilot checks plus the existing 33 + 17 + 21 checks.
- 72 frontend regression checks passed, including 20 Japan pilot and 14 follow-up review scenarios.
- 14 privacy-scanner tests passed; the repository privacy scan passed for publishable worktree files, the current index, reachable history and commit metadata.
- Python fatal-error checks and syntax checks passed. Frontend syntax, application undefined-name checks, local documentation links and active-flow translation keys passed.
- No new dependencies were downloaded. Project frontend dependencies are not installed in this workspace, so a production frontend build and real-browser acceptance were not run.
