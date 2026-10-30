# Cohort delivery (#184, #185, #186)

This feature builds on the organization tenancy policy cutover. The tenancy
migration gates remain prerequisites; no owner-only or persona-based access
fallback is introduced.

## Invariants

- All records and queries carry the active organization ID.
- Cohorts have one optional parent level, without inherited membership.
- Cohort participants must be active organization members. Archival preserves
  assignment evidence. Guardian membership alone grants no attempt access.
- Recipients are snapshotted when assigned. Later roster additions do not
  silently receive old assignments. Organization suspension revokes access.
- Cohort facilitator delegation has independent `can_assign` and `can_report`
  flags, set by organization administrators; these do not promote an org role.
- Delivery reuses training runs, recipient records, sessions, retry reservation,
  outbox notifications, and closure evidence rather than a parallel engine.
- Assigned content has an immutable quiz revision identifier and snapshot.
- Completion counts each snapshotted recipient once; average percentage uses
  the latest submitted result per completed recipient, never raw score totals.
- Existing training endpoints, public links, and closed reports remain valid.
- No new Redis polling or Celery Beat schedule is required.
- New UI mutations carry `X-Organization-ID` from the issuing form. The
  shared tenancy dependency rejects a changed workspace with 409; the header
  cannot select a tenant or replace membership authorization. Auth retries
  preserve this intent fence.

## HTTP contract

All endpoints require authenticated, verified users and a server-resolved active
organization. Cross-tenant identifiers return 404; in-tenant denials return 403.
Paginated lists use `{items, next_cursor}` with a maximum page size of 100.

### Cohorts: `/api/cohorts`

- GET/POST collection; GET/PATCH `/{id}`; DELETE `/{id}` archives.
- Cohort: `id`, `organization_id`, `kind`, `name`, `parent_cohort_id`,
  `status` (`active|archived`), `created_by_user_id`, timestamps.
- GET/POST `/{id}/members`; DELETE `/{id}/members/{user_id}` removes membership.
- Member input: `user_id`, `role` (`facilitator|member|guardian`),
  `can_assign` and `can_report` (facilitator only, default true).
- Member output adds `name` and the delegation flags, without exposing email
  to ordinary cohort members. Membership changes require org admin policy.
- GET `/api/cohorts/member-options` returns paginated organization users for
  admin-managed membership. Direct assignment has a separate, name-only
  `/api/v1/assignments/recipient-options` endpoint governed by assignment policy.
- GET `/{id}/progress` returns cohort assignment summaries (paged): assignment
  ID/title, participant/completed/outstanding counts, completion percentage,
  average percentage. This is separately report-authorized.

### Assignments: `/api/v1/assignments`

- GET/POST collection; GET `/mine` for a recipient's assignments.
- GET `/quizzes` lists assignable quiz IDs/titles, respecting content policy.
- POST input: `quiz_id`, optional `cohort_id` OR `recipient_user_ids`, `title`,
  `available_from` (optional, defaults now), `due_at` (optional), `closes_at`,
  `max_attempts` (1, 2, or null for unlimited), `time_limit_minutes` (default 20),
  `passing_threshold_percentage` (default 80), `send_email_invitations`.
- Creation requires `Idempotency-Key`. Recipients must be active org members.
- GET `/{id}` returns run detail plus `cohort_id`, `available_from`,
  `quiz_revision_id`, and independent `can_manage`/`can_report` capabilities.
- POST `/{id}/start` starts or resumes the authenticated recipient's session
  using the existing start-session response. Resume rotates the participant
  token, preserving the timer, saved answers and attempt reservation. Existing
  live-session screens, grading and stored session results are reused.
- POST `/{id}/close` requires `{confirm:true}` and management authorization.
- GET `/{id}/recipients/{user_id}/attempts` returns paginated attempt summaries
  under independent reporting policy; never other practice attempts.
- GET `/{id}/recipients/{user_id}/attempts/{session_id}` returns the authorized
  assigned attempt detail (questions/results), never unrelated private attempts.
- Summaries include `id`, `title`, `quiz_id`, `quiz_revision_id`, `cohort_id`,
  availability, retry/progress fields and report availability as appropriate.

## Architecture and authorization

- New persisted collections are `cohorts`, `cohort_memberships` and
  `quiz_revisions`, initialized through the existing database startup hook with
  validators and organization-leading indexes. Empty collections need no new
  historical backfill. Existing tenancy Protocols A/B remain prerequisites.
- A generic assignment is an existing `training_runs` record with
  `delivery_kind="quiz"`. Its obligations reuse `training_assignments` and its
  attempts reuse `live_quiz_sessions`. `assignment_id`, `training_assignment_id`
  and `quiz_revision_id` link those records. Practice `quiz_attempts_v2` history
  is not a second delivery engine and is not repurposed.
- A revision is an append-only, content-addressed delivery snapshot, not a
  separate authoring/version-management system. Active public seed templates
  from the platform library may be copied into a tenant-local revision; private
  quizzes in other organizations cannot be assigned.
- Organization owners/admins manage cohorts and all assignments in their
  organization. Auditors can report, not assign. Ordinary cohort members can
  see their roster and their own assigned work, not classmates' results.
- A cohort facilitator's `can_assign` and `can_report` are independent, even
  when their organization role is learner. Delegation does not permit editing
  the organization roster or reading unrelated private quiz content. A direct
  named-recipient assignment uses the existing facilitator creator boundary.
- Removing someone from a cohort does not rewrite already-issued assignments.
  Removing/suspending their organization membership revokes private session
  access, as does disabling their account or revoking its authentication
  session. A workspace switch requires returning to the assignment's workspace.
- Generic assignment sessions are excluded from legacy quiz-level analytics,
  attempt-detail routes and websocket events. Otherwise a creator could bypass
  the independent cohort reporting permission through those older routes.
- Completion notifications to creators also re-check reporting policy.
  Assignment/invitation delivery uses the existing outbox and worker cadence.
- Manual closure stops unfinished attempts and retains them as incomplete;
  automatic closure retains eligible expired submissions through the existing
  finalization path. Closed summaries and recipient registers read retained
  evidence, not subsequently changed live rows. Missing/malformed evidence is
  unavailable (503), never silently fabricated as zero completion.

## Bounds and statistics

Assignments snapshot at most 1,000 active recipients; an oversized cohort fails
explicitly rather than truncating. UI/API lists are cursor-paginated to 100 rows.
Delegated assignment browsing supports 1,000 cohorts before requiring a cohort
filter. Hierarchy/roster mutations use a short Mongo-only lease to preserve the
one-parent-level invariant across API processes.

Progress is shown per assignment within its cohort, using that assignment's
frozen roster. Completion means a submitted attempt, not a passing score;
pass/fail remains a separate outcome. A completed recipient remains completed
while retrying. The average is the latest submitted **percentage** per completed
recipient. Different question counts are therefore comparable without averaging
incompatible raw scores. The recipient register identifies outstanding members
and links their assigned attempts where reporting policy allows.

## Manual Test: Two Accounts

1. Start the normal local stack with `docker compose up --build -d`. Complete
   the existing tenancy startup migrations. Use two verified accounts in
   separate browser profiles: A (organization owner) and B (learner).
2. In organization settings, A creates a School organization, invites B as a
   learner, and selects it. B accepts the invitation and selects the same
   organization. Persona changes must not change these permissions.
3. As A, open `/cohorts`, create a class, edit its name, then add B as a member.
   Create a root and child if testing hierarchy; creating a grandchild or
   archiving a parent with active children must fail with a clear message.
4. Create a quiz in this workspace, or use a curated public template. From the
   class, choose Assign, select the quiz, set a title, future closing date,
   time limit, optional due/opening dates and two attempts. Submit. Verify the
   assignment detail records a revision ID and B in its completion register.
5. As B, `/assignments/mine` shows the work. A future opening prevents starting.
   For an open assignment, start, answer and leave the live page; returning via
   Resume must preserve saved answers/time and keep attempts used at one.
   Submit and verify both the result and A's class progress/register.
6. Retry as B. No parallel second session may be reserved from two tabs. The
   previous completed result stays visible while retrying; after submission,
   the latest percentage is used. Once both attempts are used, start is denied.
7. Edit the source quiz after assigning. Assigned questions/revision remain
   unchanged. Add or remove a cohort member: existing recipients stay frozen;
   a new assignment uses the current roster.
8. As A, close an assignment through its confirmation dialog. B can no longer
   start/save/submit unfinished work. Closed progress stays fixed. Archive the
   class and find it using the Archived filter; retained reports remain readable.
9. To test delegation with the same two accounts, add A as an ordinary cohort
   member so there is still a recipient, then set B's cohort role to
   facilitator with Can assign enabled and Can report disabled. B can assign
   readable/self-authored content or a public template, but cannot read results
   or assigned attempts. Reverse those flags: B can report, but cannot create
   or close assignments. Guardian role alone must grant neither capability.
10. Switch A or B back to their personal organization and try copied cohort,
    assignment and report URLs from the School workspace: they must return 404.
    A stale form submitted after a switch must not create anything in the new
    workspace. Suspension/removal of B's School membership must revoke an
    already-issued participant token. Restore membership explicitly afterward.
11. Repeat the relevant screens in a Corporate organization/persona and check
    `useTerms()` wording follows the active workspace rather than granting
    permissions from the persona.

## Navigation Layout Check

- At desktop widths (1280px and above), verify the navbar fits on one row,
  including a long username and the organization switcher. Quiz creation is a
  compact, borderless navigation action; the rest of the visual language stays
  unchanged.
- Below 1280px, use the compact menu. Cohorts, live quizzes, organization
  switching, account actions and the existing upgrade action remain available.
- Open the desktop sidebar in a short window and scroll to its final action.
  The panel starts below the navbar, and closing it removes its controls from
  keyboard navigation.

## Automated Validation

The existing backend CI job discovers the new tests under `server/tests`,
including real-Mongo tests under `v2_database_tests`. Docker is required for
those integration tests; they deliberately use disposable databases rather
than Atlas or a developer's working data. Frontend tests are discovered by the
existing Jest job; the production build also type-checks all new page routes.

Coverage includes tenant guessing, revoked membership/account/session access,
independent delegation, hierarchy races, idempotent provisioning, availability,
retry concurrency, resume, frozen templates/rosters, retained progress,
malformed evidence and stale-workspace writes. Reused live-screen regressions
cover ordered/coalesced answer saves, final-answer flushing, expiry during a
stalled save, stale navigation callbacks and authenticated versus guest results.
Manual browser acceptance is
still necessary before merge; passing automated tests is not a guarantee of
absence of defects.
