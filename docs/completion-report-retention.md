# Completion-report retention

Live quiz completion reports are compliance evidence for one delivery (a
**run**) of a quiz. A run snapshots its access code, owner, time limit and
passing threshold when it is created. Completed sessions retain their score,
percentage, pass/fail outcome, completion timestamp and auto-submission flag.

## Retention rule

The application retains run and completed-session evidence for **seven years**
from the run creation date. This is a documented product default, not legal
advice; the organisation's legal/compliance owner must approve a different
period before production data is purged or anonymised.

## Access and export

Only the creator of a run can retrieve its CSV completion report. The report
contains personal data (name and, where supplied, email), so exported files
must be stored and shared under the organisation's HR data-handling policy.

The CSV is generated on request rather than stored as a second mutable copy.
Spreadsheet-formula prefixes in text values are escaped to protect users who
open reports in spreadsheet software.

## Operational follow-up

No automatic deletion job is introduced by this feature. Before enabling a
purge job, confirm the approved retention period, legal holds, deletion audit
events and ownership with the Epic 3 HR audit-trail work.
