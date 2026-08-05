# Claude PR Review

Claude PR Review is enabled for this repository through GitHub Actions. It gives
each pull request an automated first-pass review so the team can catch common
correctness, security, data and regression risks earlier.

Claude is advisory only. It does not replace human review, approval, product
judgement, QA or ownership of the final change.

## How It Works

The workflow has two review modes:

- Automatic review when a pull request is opened or updated.
- On-demand review when a trusted team member comments `@claude ...` on a pull
  request.

Claude posts its feedback directly on the pull request. Treat the feedback like
another reviewer comment: verify it, fix real issues, and ignore false positives
with a clear reason when appropriate.

## Automatic Reviews

Claude automatically reviews pull requests when they are:

- opened
- reopened
- marked ready for review
- updated with new commits

Automatic reviews are skipped for:

- draft pull requests
- Dependabot pull requests
- pull requests from forks
- documentation-only changes matched by the workflow `paths-ignore`

When a PR receives new commits, the previous in-progress automatic review is
cancelled and Claude reviews the latest PR state.

## On-Demand Reviews

Trusted team members can request a review by commenting on a pull request with:

```text
@claude review this PR
```

You can also ask a targeted question:

```text
@claude focus on auth/session security and database migration risk
```

On-demand reviews only run when the commenter is a repository `OWNER`, `MEMBER`,
or `COLLABORATOR`. Comments from bots, public external users, plain issues and
fork pull requests are ignored.

Use on-demand reviews when:

- a PR changed materially after the automatic review
- you want Claude to focus on one area, such as auth, MongoDB migrations,
  frontend/backend contracts, exports or live quiz behavior
- you want a second pass before requesting human approval

Avoid using on-demand reviews for formatting-only questions or issues already
covered by CI, linting or type checks.

## What Claude Checks

The workflow prompt asks Claude to prioritize:

- correctness bugs and faulty business logic
- security, authentication and authorization issues
- runtime errors and unhandled failure cases
- breaking API or database changes
- data validation and error-handling gaps
- missing or inadequate tests
- materially relevant performance or concurrency problems

For this quiz app, Claude is also instructed to pay close attention to MongoDB
ObjectId handling, null/missing values, session and authorization boundaries,
and backend/frontend contract consistency.

## Security Boundaries

The workflow is intentionally guarded:

- `pull_request` reviews only run for branches in this repository.
- `issue_comment` reviews resolve PR metadata first and skip cross-repository
  pull requests before checkout or Claude execution.
- Manual `@claude` triggers are limited to trusted repository actors.
- Repository secrets are never exposed to fork PR code.
- Claude has read-only repository access plus permission to write PR/issue
  comments.

The repository setup is already completed. Maintainers should keep
`CLAUDE_CODE_OAUTH_TOKEN` configured in GitHub Actions secrets and must not move
Claude tokens into workflow files, `.env` files, comments or commits.

If Claude stops running, first check the GitHub Actions run logs and confirm the
repository secret still exists.

## Workflow File

The workflow lives at:

```text
.github/workflows/claude-pr-review.yml
```

Any change to this workflow should be reviewed as security-sensitive because it
controls how repository secrets are exposed to PR automation.
