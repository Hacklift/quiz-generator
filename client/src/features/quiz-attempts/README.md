# Graded practice attempts

Authenticated practice submissions are graded against the canonical quiz and saved
in `quiz_attempts_v2`. Guests can grade without an account; their attempts are not
saved. Generated quiz history stays at `/quiz_history`, with its existing actions.
Graded results have separate list and detail pages at `/quiz_attempts`.

## Grading contract

`POST /api/quizzes/{quiz_id}/grade` keeps its array response. All callers must
submit exactly one answer for each stored question. Missing, extra, or unknown
questions return `400`; this is a deliberate tightening of guest submissions too.
Correct answers always come from the server. Deleted quizzes and another user's
private quizzes return `404`. Public/unlisted and ownerless guest quizzes remain
available for practice.

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
History reads, details, and soft deletion are scoped to the authenticated user.
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
6. Sign out. Generate a guest quiz or open a public quiz, complete it, and grade.
   Scores must display without a login redirect or an attempt being saved.
7. Inspect the grading response header in browser Network tools. Confirm `saved`
   for authenticated submissions and `not-requested` for guests. Repeat with
   true/false and short-answer quizzes.

## Tenancy rollout

This PR is intended to merge into the current user-scoped master before the
organization-tenancy rollout. Its authorization boundary is the authenticated
user: attempt list, detail, and deletion queries require the caller's `user_id`.
Organization-based authorization is delivered by the tenancy PRs, which must be
updated against master after this feature merges. This sequencing keeps the
attempt feature usable under the current architecture while giving the tenancy
cutover the final resource schema to migrate and enforce.

Protocol B already includes `quiz_attempts_v2` and resolves existing attempts
through `user_id` into each user's personal organization. That collection-level
coverage must be verified against the complete attempt documents introduced by
this PR, including question results, scores, options, and soft-deleted records.

Before deploying tenancy enforcement, the tenancy resource-scope and policy
cutover PRs must complete these integration steps under #181, #182, and #183:

1. Merge the updated master and reconcile attempt collection setup with the
   tenancy models, Mongo validators, and indexes.
2. Add `organization_id` and `created_by_user_id` to attempt documents, and resolve
   the authenticated organization context for every new attempt write.
3. Scope list, detail, deletion, and quiz lookups through organization policy and
   repositories, retaining the user-level privacy checks on personal results.
4. Add indexes beginning with `organization_id`, followed by the user, quiz, and
   ordering fields used by the queries.
5. Run migration reconciliation and cross-organization isolation tests using
   actual persisted attempts. Verify that backfill preserves grades and deletion
   state and that subsequent writes remain scoped after cutover.
6. Complete the controlled Protocol B backfill and its verification before
   enabling strict tenant enforcement in the target environment.

These are release prerequisites for the tenancy rollout. Merging this PR alone
does not enable tenancy or claim organization isolation for attempts. Backfill
handles historical records; the integrated writers and readers must maintain
the boundary for all records created afterward.
