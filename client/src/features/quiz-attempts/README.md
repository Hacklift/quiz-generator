# Graded practice attempts

Authenticated practice submissions are graded against the canonical quiz and saved
in `quiz_attempts_v2`. Guests can grade without an account; their attempts are not
saved. Generated quiz history stays at `/quiz_history`, with its existing actions.
Graded results have separate list and detail pages at `/quiz_attempts`.

## Grading contract

`POST /api/quizzes/{quiz_id}/grade` keeps its array response. All callers must
submit exactly one answer for each stored question. Missing, extra, or unknown
questions return `400`; this is a deliberate tightening of guest submissions too.
Correct answers always come from the server. Deleted quizzes and inaccessible
private quizzes return `404`. Public/unlisted quizzes remain available for guest
practice; an ownerless private record is not a public capability.

`X-Quiz-Attempt-Status` describes persistence separately from grading:

- `saved`: the authenticated user's attempt was stored.
- `failed`: grading succeeded, but the attempt write failed. Scores remain visible
  and the frontend displays a warning. Delivery is best effort, with no automatic
  retry or history recovery guarantee.
- `not-requested`: the request resolved to a guest, including an invalid or expired
  optional token. No attempt is stored. The UI warns if it expected a signed-in
  submission.

The header is exposed through CORS. Guests use the public HTTP client; signed-in
users use the authenticated client. Duplicate clicks are blocked while grading.
History reads, details, and soft deletion require both the authenticated user and
the server-resolved active organization. Organization failures on authenticated
grading return an error rather than silently discarding persistence as a guest.
The list currently shows the latest 100 attempts, newest first.

## Manual testing

1. Start the Docker services and sign in with a verified account. Generate or open a saved quiz, answer
   every question, and submit. Confirm scores display and answers lock.
2. Open `/quiz_history`: generated history, retake, details, and deletion must
   still work. Select **View graded attempts** to open the separate attempt list.
3. Confirm the new attempt shows its score and percentage. Open its detail and
   verify answers and correctness. Retake the quiz and confirm a second attempt
   appears independently.
4. Delete one attempt. Refresh and confirm it stays deleted while the generated
   quiz and other attempts remain.
5. Sign in with a second account. The first account's attempts must be absent;
   requesting its attempt identifier must return `404` for read and delete.
6. Sign out. Open a public quiz, complete it, and grade.
   Scores must display without a login redirect or an attempt being saved.
7. Inspect the grading response header in browser Network tools. Confirm `saved`
   for authenticated submissions and `not-requested` for guests. Repeat with
   true/false and short-answer quizzes.

## Tenancy rollout

The resource-scope integration writes `organization_id` and `created_by_user_id`
on new attempts, adds organization-first indexes, and scopes reads and deletes
by organization plus user. Personal results do not become organization-wide
reports. A public quiz's source organization does not become the learner's
attempt organization: results belong to the active context at submission time.

Protocol B already includes `quiz_attempts_v2` and resolves existing attempts
through `user_id` into each user's personal organization. That collection-level
coverage is tested against complete attempt documents, preserving question
results, scores, options, and soft-deleted records.

The resource-scope PR temporarily reads legacy unscoped attempts only for their
user in a personal organization. This policy-cutover branch removes that fallback
and requires organization scope on persisted attempt models and Mongo validators.
Private grading and history source enrichment follow the central content-read
policy. Public/unlisted practice requires an active source organization. Results
remain readable from their own snapshots when the source is no longer accessible.

Complete the controlled Protocol B backfill and its verification before enabling
strict enforcement. Local Docker's existing migration gate handles the development
database separately.
