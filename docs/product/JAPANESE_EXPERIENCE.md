# Japanese family and local-service experience

This revision implements the language, presentation and care-flow recommendations for a small Japanese pilot. These are product choices for the intended families and staff, not validated claims about all Japanese users. Work is **source only**: no application/worker, dependency installation, build, lint/parser, tests, browser, migration, print/QR check or real-data workflow ran. Source inspection and `git diff --check` do not establish runtime or visual correctness.

## Language and first use

The public entrance, sign-in and family header share a translated `ProductBrand` with a neutral line icon. Japanese display uses 「産後のくらしサポート」; institution entry uses 「支援者・施設の方へ」. The browser title follows the display language. Japanese installation metadata uses the same product name and entrance wording.

Everyday labels replace terms such as 「記録タイプ」「気分レベル」「おむつの種類」. Quick records use a short category with the separate caption 「今の時刻で記録」. Empty states allow recording when useful rather than demanding a first entry. Sleep/mood labels remain the person's descriptions, not clinical scores or assessments. Japanese/English translations cover all new labels and states.

`OperatorInfo` appears on the public entrance and sign-in, including direct family-entry visits. It reads only the published `/api/pilot` information, shows the actual operator name and exposes contact channels/hours in a disclosure. Missing or failed information is explicitly labeled and can be reloaded; no operator, clinical credential, partnership or supervision is invented. Its guidance distinguishes app questions from care consultations/bookings; the actual contact endpoints may overlap when an institution handles both. Loading this component sends no care record or AI request.

## Care records

The type selector groups baby care separately from the adult's health/feelings. All record fields remain optional except the existing event type/time requirements. Choosing a feeding method changes which fields are prominent:

| Method | Main fields | Additional fields |
| --- | --- | --- |
| Breastfeeding | Duration and side | Amount, only if known |
| Formula | Amount | Duration and breastfeeding side, if applicable |
| Mixed | Duration, breastfeeding side and known amount | None |
| Unspecified | Method choice | Optional duration, side and amount |

Changing the method does not clear earlier measurements or infer new ones. Additional fields open initially when they contain values, including zero, and explain that those values are also saved. Users can review/clear them. Closing the disclosure keeps values; clearing the last value does not automatically close the editor. Generic duration/known-amount labels remain available for legacy and mixed records so their values are not silently reinterpreted as breastfeeding time or formula-only volume.

The existing `side` field is reused without a new tracking schema. The record list and selected consultation details display its translated value. Record identity/revisions, immutable retry content/timestamps, optional account-bound drafts and explicit sharing scopes are retained. Switching feeding method does not alter recorded time. No duration, quantity or quality is inferred from a quick tap.

Save feedback distinguishes saving, deleting, restoring and quick undo. Offline-unsent and dispatched-but-unconfirmed states have separate short headings and accurate explanations. Check records and Resend the same record use the existing original operation; reconnecting does not write automatically. Delete/restore operations use the same immediate in-flight guard as saving. Restoring is blocked while a record save remains pending; deleting the record currently being edited clears its obsolete form/draft, while other unfinished forms remain.

## Local services and staff editing

Need-based buttons such as 「少し休みたい」「話を聞いてほしい」 filter existing service categories. A message identifies the actual category and asks users to confirm available support with the contact. This is navigation, not assessment, eligibility matching or a promise of available appointments. All service/progress editors remain mounted across filters; emergency contacts, pause notices and explicit phone-script/sheet preparation remain accessible.

Expanded service details present eligible users/conditions, family cost, application/booking order and whether someone staying with family or registered in another municipality can use the service. Empty values say the information is unconfirmed; they do not imply free access or eligibility. Staff see corresponding field hints and must verify actual local information before publishing. No residential address, location permission or new household identity field is requested.

### API compatibility and rollout

`LocalResource` adds the optional public string `visiting_note`, up to 500 characters, defaulting to empty. It is included in staff drafts, publication validation, field-linked errors, before/after diffs and existing publication snapshots. Older saved JSON profiles/histories can omit it; missing and empty have the same meaning. The unpublished-status label uses that same field comparison, so adding the empty default alone is not treated as a public change. The directory already stores profile JSON, so this change adds no SQL table/column or migration.

**Deploy the matching backend and frontend together after authorized verification.** An older backend forbids unknown resource fields and can reject the new editor payload with 422. Existing workspace revisions, staff authorization, preview-before-publication and history restoration remain required. The field is public service guidance, not a family's private location or eligibility decision. It is never automatically filled from AI or current time.

## Presentation

The green action color remains, with a warm neutral page background and subtler shadows. Existing Japanese system fonts, text scaling, high contrast, reduced motion, focus outlines and mobile safe-area navigation remain. Japanese text uses normal word breaking and stricter punctuation line breaks; numbers use tabular glyphs in record times. Quick buttons place the action name above its current-time caption, and contact details stack on narrow screens. No external font service, raster asset or dependency is added.

## Pending acceptance after execution is authorized

1. Review the Japanese wording with local parents/caregivers and staff. Walk through first record, correction, identifying the real operator, distinguishing AI from a human contact and finding rest/feeding support. These sessions have not been conducted.
2. Inspect 320/375/768px and desktop in Japanese/English, larger text, high contrast, night mode and mobile keyboard states. Check line breaks, touch targets, brand wrapping, contact disclosures, focus and installation wording.
3. Cover new/restored/legacy feeding records: unspecified, breast, formula and mixed methods; duration/amount zero; left/right/both; method changes with existing values; clearing/closing extra fields; cancellation; pending save retry; conflict rejection and return from Home. Check that saved/list/consultation values agree and no hidden value is silently dropped.
4. Delay save/delete/restore/undo, repeat taps and lose responses/connections. Verify accurate state wording, original request keys/timestamps, restore blocking during a pending save, edited-form cleanup after deletion and retained unrelated input.
5. Load operator information as a visitor and direct sign-in user, including missing fields, API failure/retry and delayed unmount. Confirm only published business data appears and no care data, private operator-account details or unsupported credentials are shown.
6. Save an incomplete directory draft with/without `visiting_note`, reject values over 500 characters, publish after preview, race revisions, restore an old history and inspect the family view. Verify field errors/diffs and unconfirmed empty guidance. Exercise filters/contact removal with unsaved progress. Validate a matching backend/frontend deployment before use.

The earlier [UI acceptance contracts](UI_FRIENDLINESS.md) also remain pending. No test, rendering, accessibility or native-language acceptance result is claimed here.
