# Training completion reports and audit retention

Issue #136 extends the existing HR/business training runs and the Epic 3 HR
audit trail (#132). It does not introduce a second live-quiz run collection.

## Evidence and access

- A new training run records a passing threshold (default 80%, configurable
  from 0 through 100). No update API changes that threshold after creation.
- `/training-runs/{runId}` shows the assignee register, completion timestamp,
  score, percentage and outcome. The register reflects the existing latest
  attempt policy, not a new historical-attempt ledger.
- `GET /api/v1/training-runs/{run_id}/completion-report.csv` downloads the same
  register. It requires the existing verified training-manager authorization
  and run ownership. Guessed, missing and another owner's run IDs return 404.
- Open-run reports are explicitly **provisional**. Manual closure and scheduled
  closure retain the same versioned audit payload, including the quiz snapshot,
  threshold, participant records and outcomes. Closed reports read that payload,
  never current assignments or regenerated quiz content. A missing final audit
  record produces 503 rather than fabricated evidence.
- Existing runs/snapshots without a recorded threshold remain readable, but
  completed outcomes are **unknown / Not recorded**, not retroactively failed
  or evaluated against today's default. Non-starters are included as not started.
- Compliance runs remain assigned-only and require verified recipient access.
  Business shared-link participants are labelled separately: their supplied
  names/emails are not verified staff identity.

## Actual retention behavior

No automatic retention deadline, TTL index, purge job or anonymization job is
introduced for training runs or their audit snapshots. The application currently
retains these records without a scheduled expiry. **Seven years is not an
approved or enforced default.** The organization must approve retention periods,
legal holds and deletion requirements before a separate retention policy is
implemented. Backups and disaster recovery remain deployment responsibilities.

Closure snapshots are immutable through application APIs, not cryptographically
sealed or protected from privileged database operators. CSV downloads contain
personal data; responses disable caching, and recipients must store exports
according to their organization's approved data-handling policy. Text fields
are quoted/escaped for CSV and formula-leading input is prefixed as text.
Spreadsheet behavior differs by application; do not treat downloaded CSV as
tamper-proof evidence or re-import spreadsheet-resaved files as trusted input.

## Rollout before organization tenancy

This backlog PR targets current master's user-owned training architecture.
After it merges, update the tenancy resource-scope and policy-cutover branches
before their rollout: preserve threshold/outcome fields in Protocol B snapshots,
apply organization policy to the new export route, and add cross-organization
export isolation tests. Existing training collections remain the source of truth;
this PR adds no tenant migration, index replacement, Redis polling or Beat job.

## Manual verification

1. Sign in as verified HR/Business personnel. Create an assigned run with a
   non-default threshold and at least two recipients. Confirm both are listed
   as not started and the chosen threshold survives refresh.
2. Complete one recipient's quiz. Verify timestamp, score and the inclusive
   threshold boundary (percentage equal to the threshold passes).
3. Export CSV while open: it must say provisional and retain the non-starter.
4. Close the run (or allow scheduled closure), refresh and export again: the
   page and CSV must say final and agree on outcomes. Repeated exports preserve
   evidence; only the export-generation timestamp changes.
5. Verify another manager cannot view/export the run, and an Employee account
   cannot use the manager export endpoint. Public live quizzes and their
   existing CSV/PDF/text exports must still work unchanged.
6. Open a pre-feature run: a missing historical threshold/outcome must say
   Not recorded, not claim an 80% policy was in force.
