# Care-flow publication review

The publication review covers the care-flow implementation, its four follow-up
fixes, publishable repository files, the Git index, reachable history and commit
metadata. Only source inspection, read-only privacy scans and Git diff checks
were used. No application/worker, dependency installation, build, lint, tests,
database setup, browser or real-data workflow was run.

## Findings and preparation

- The initial scan covered 367 working files, 357 staged blobs and 590 reachable
  historical objects. File content had no privacy findings. Four metadata
  findings came from the author and committer email on two recent commits. The
  actual address is deliberately omitted here. Ordinary pushes cannot remove it.
- A clean publication candidate must replace only those private identities with
  the repository owner's GitHub noreply identity, preserve the historical file
  trees and messages, and add the reviewed care-flow changes. Publishing rewritten
  history requires explicit approval and a lease on the inspected remote head.
- Automatic browser diagnostics previously captured the complete page URL before
  React could remove an invitation fragment. Diagnostics now collect only a fixed
  page category, error category and numeric source position, known action names,
  or finite numeric Web Vitals. They exclude complete URLs, query/fragment values,
  host/IP addresses, browser user-agent, arbitrary details, raw error messages and
  stack traces. No monitoring endpoint or external analytics service was added.
- New family endpoints require active membership; handover writes are scoped to
  the author and reviewed membership revision. Home overview excludes parent
  records and tracking free text. Sharing remains an explicit choice.
- Help progress is filtered by the authenticated account. Its unsaved editors
  remain in account-session memory and never enter browser storage. Removed
  contacts retain input without becoming current contact recommendations.
- Invitation secrets are returned once, hashed in the database and transported
  in authenticated POST bodies. QR generation stays in the browser. Joining is an
  explicit action; account changes clear the pending invitation.
- Account handling references are administrator-only. Public receipt lookup
  returns only the deliberately public response, next step and receipt, and
  excludes contact email, account ID and private processing references. Account
  recovery/deletion execution remains an attested manual process.
- Private API responses bypass service-worker caching. Legacy offline writes are
  not replayed. Local environments, databases, logs and private reports remain
  excluded from publication.

Static checks do not establish runtime correctness or guarantee that all forms
of personal information can be detected. History rewriting cannot retract copies
that were already downloaded or retained outside the published branch.
