# Shared UI foundation and a quieter Home

This change is source only. No application, build, dependency installation, lint, parser, test, browser or migration was run. Source inspection and Git whitespace checks do not establish that the interface renders or operates correctly.

## Home

The main flow is now **current baby → quick record → recent records**. The selected baby's name stays in a labelled selector; a short visibility notice and any applicable sharing choice remain visible before saving. Selecting another baby resets the quick-record sharing choice to private, as before. Without a selected baby, the recent list keeps the existing default of all this account's personal records, clearly labelled as such. The filter also offers unassigned baby-care records. This avoids hiding existing assigned records on a fresh login before the user has selected a baby.

The recent list initially shows up to three matching records. Its date/owner/baby/type controls are inside an explicitly labelled disclosure. The current viewing scope, period, and any selected record type stay visible when the controls are closed. Opening family records still requires explicitly selecting a family. Selecting another baby on Home returns the list to personal records for that baby. Viewing filters never change the baby or sharing scope used by the quick-record buttons.

The full matching list and the dedicated records page remain available. Record details and corrections still use the existing record sheet and revision guards. Following a saved-record link opens that record without being restricted to the three visible rows.

Timers, baby management, family handovers, daily totals, self-care and the practice example are grouped below the main flow. Each has its own disclosure; opening a timer or following a management link reveals the correct section. These components stay mounted so closing a section does not erase a timer or an unfinished edit. Baby management only loads the family choices while expanded and on the visible Home page.

Continuation cards remain outside the disclosures. Unresolved save cards retain their existing non-dismissible behavior. Saving/retry/recovery/undo feedback stays beside the relevant record operation. Stopping a quick-record retry clears its optional recovery draft successfully before removing the pending operation from the screen; failure leaves it available for review.

## Design tokens

`frontend/src/styles/tokens.css` owns:

- Colors for surfaces, text, links and info/success/warning/error messages.
- A spacing scale from `--space-1` to `--space-12`.
- Body, small and heading font sizes, weights and line heights.
- Control height, padding, radii, panel padding and keyboard focus outline.

New shared controls and existing `.pilot-button`/`.pilot-panel` styles consume the same tokens. High contrast overrides the status palette as well as the original colors. Empty states follow the app palette instead of switching independently with the device color scheme. Loading indicators honor reduced motion.

## Shared components

Import the components from `frontend/src/components/ui`:

| Component | Contract | Current use |
| --- | --- | --- |
| `PageHeader` | `title`, optional `description`/`actions`, semantic `headingLevel`. `titleId` makes the heading focusable; a forwarded ref targets the heading. | Home, records, support views, settings, institution and operator headings. |
| `Button` | Defaults to `type="button"`; use explicit `type="submit"` in forms. Variants: `primary`, `secondary`, `quiet`, `danger`. `busy` disables the button and exposes progress; `busyLabel` is supplied by the caller. | Home actions, baby management, record header, support navigation, settings save and confirmations. |
| `FormField` | One labelled input/select/textarea, with a generated or explicit ID. Hint/error IDs are combined with caller-provided `aria-describedby`. Required/optional badges are localized. Errors set `aria-invalid` and expose an alert. | Baby selection and management, recent-record filters, record date range and profile fields. |
| `ConfirmDialog` | Controlled `open`, explicit `onConfirm` and `onClose`. Native modal dialog, labelled title/description, initial focus on Cancel. Escape/backdrop cancel without confirming; confirmation is guarded while running. Return `false` to stay open after a handled failure; thrown failures show a generic error. | Stop retrying a quick record, discard a timer and delete a record. |
| `EmptyState` | Existing public import/props remain supported. `compact`, `icon={false}`, `suggestions={[]}` and an explicit title/description provide a short contextual state. | Recent records, records list, baby management and existing charts. |
| `StatusMessage` / `ErrorMessage` | Explicit tone plus text, optional actions and retry. Error messages expose `role="alert"`; other states use `role="status"`. Labels accompany colors. | Record saving, connectivity, baby loading/permission errors, records, settings and institution loading errors. |

For example:

```jsx
import { Button, FormField, PageHeader } from './ui'

<PageHeader title={t('settings.title')} description={t('settings.subtitle')} />
<FormField as="select" label={t('continuity.subject.recordFor')}
  value={subjectId} onChange={event => setSubjectId(event.target.value)}>
  {options}
</FormField>
<Button type="submit" busy={saving} busyLabel={t('settings.saving')}>
  {t('work.saveChanges')}
</Button>
```

Keep checkbox/radio groups in their own fieldset and legend. `FormField` is for a single input, select or textarea. Keep validation and save requests in the owning feature; the UI components do not choose care subjects, grant consent, persist data or retry requests automatically.

Confirmation dialogs restore focus only to a connected trigger outside hidden panels. Owners pass their view visibility to `open`, so a modal closes when its private view is hidden. Delete and timer failures keep their target available for retry. Existing revision/idempotency checks and explicit AI/profile/sharing controls remain in the feature code. No new browser storage or backend schema is introduced.

The migration covers the main Home flow and shared patterns listed above. Other feature-specific forms retain their existing controls and may adopt these primitives when edited; this is not a full replacement of every legacy component.

## Pending acceptance

When runtime verification is authorized, check narrow phones, larger text, Japanese line wrapping and high contrast; all three quick-record steps; filter expansion and personal/family scope labels; quick-save receipts and corrections; timer continuation after hiding/reopening; and keyboard focus, Escape, retry failures and double-click prevention in confirmation dialogs. None of these checks was executed for this change.
