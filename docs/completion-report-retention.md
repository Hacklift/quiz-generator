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
- Capture and interpretation are separate: an unfamiliar record state or invalid
  timestamp cannot prevent closure. Its raw retained fields are preserved with
  `outcome: "unknown"` and an interpretation-error marker. Strict report reads
  remain unavailable until evidence can be interpreted safely. Closure failure
  from unrelated storage/operational errors still uses the existing recovery.
- Closed list summaries also use retained evidence, not live participant rows.
  A missing or uninterpretable snapshot is explicitly labelled **Final evidence
  unavailable** (`summary_availability: "unavailable"`), not a zero-completion
  claim, and does not hide other runs from the list.
- Existing runs/snapshots without a recorded threshold remain readable, but
  completed outcomes are **unknown / Not recorded**, not retroactively failed
  or evaluated against today's default. Non-starters are included as not started.
  This is an intentional release behavior requiring product/reviewer sign-off;
  the implementation does not claim that historic passing rules can be recovered.
- Compliance runs remain assigned-only and require verified recipient access.
  Business shared-link participants are labelled separately: their supplied
  names/emails are not verified staff identity.

## Interactive reporting limits and diagnostics

Interactive registers and synchronous CSV downloads support up to **10,000 rows**.
Bounded, projected Mongo reads retrieve only the report fields and at most one
extra row to detect overflow. Larger runs remain viewable and manageable: detail
returns **200** with `register_availability: "limit_exceeded"`, full summary
counts, and no participant rows. The UI displays that distinction, disables CSV,
and keeps the irreversible Close control available. Its warning uses the full
participant count, not the absent register. CSV requests return **413**, never a
partial export labelled complete.

The run list batches count/score aggregation across the owner's selected run IDs:
two aggregations for open runs and one for closed snapshots, at most three total,
not queries per run. The assignment compound index starts with `training_run_id`;
live sessions have a `training_run_id` index. Bounded sentinel reads are retained
instead of a separate count-first query, which adds round-trips and does not
eliminate races with new participants. Detail and summary calculations treat
`submitting` as in progress and apply the same nonnegative whole-number raw-score
rule (including integral floats, excluding booleans, fractions and non-finite
values). Large closed-run summary counts are aggregated from the immutable audit
register, not current assignments or sessions. No Redis cache or additional
polling schedule is introduced.

This is a limit on interactive reporting, not a participant admission limit.
Run closure still captures all evidence without silently truncating it. For a
larger run, a maintainer must arrange a controlled full export; no background
large-export service is included in #136. The existing single-document audit
snapshot remains subject to MongoDB's BSON document-size limit; unbounded-scale
audit storage is not claimed by this PR.

Missing or malformed final evidence returns **503** and logs the event
`training_completion_report_unavailable` with the run ID, without participant
PII. The evidence parsing stack is retained with a sanitized exception rather
than validation input values. Unexpected implementation/DB failures are not
reclassified as malformed evidence; the standard error handler retains their
tracebacks. Oversized requests log `training_completion_report_limit_exceeded`.
Operators should alert on the unavailable-record event/503 rate in deployment
logs and investigate the retained audit document and closure-worker logs.
The application does not install a hosted monitoring/alerting integration or
reconstruct missing final evidence from mutable data.

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
The CSV is a **display-safe representation, not a byte-exact record**: names,
titles and even legitimate email addresses beginning with `+` or `-` receive
a leading apostrophe. Source documents and retained snapshots are not modified.
Plain `|` and `%` are not treated as formula triggers in
[OWASP's CSV injection guidance](https://owasp.org/www-community/attacks/CSV_Injection);
the documented formula/control-character prefixes and CSV cell boundaries
are handled. Exported CSV must not be used as a lossless identity interchange.
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
7. Confirm missing/malformed final evidence produces 503 and a diagnostic event,
   not a reconstructed or partial report. The automated database tests exercise
   the report ceiling separately from complete closure capture. For oversized
   runs, detail and Close remain usable while the CSV endpoint returns 413.
