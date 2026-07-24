# Quiz Generator — Principal Engineer Review

**Date:** 2026-07-24
**Scope:** Full-stack review of the FastAPI backend (`server/`), Next.js client (`client/`), and infrastructure (`Dockerfile`, compose files, `deploy/`) against five criteria: robustness, UI/UX, efficiency, reliability, and security.

## Scorecard

| Criterion | Score | Summary |
|---|---|---|
| Security | 3 / 5 | Strong session/token architecture undermined by an open email-relay endpoint, unrestricted quiz reads, OTP weaknesses, and missing proxy-header handling |
| Robustness | 3.5 / 5 | Good Pydantic validation and a disciplined v2 repository layer; some swallowed exceptions and memory-unbounded upload reads |
| Efficiency | 3 / 5 | Sensible RAG caching and indexing; per-request write amplification, single-worker serving, and a cache-everything service worker |
| Reliability | 2.5 / 5 | Solid test suite exists (36 backend test files) but **no CI runs it**; shallow health checks; no error tracking or backups |
| UI/UX | 3.5 / 5 | Feature-rich and polished flows (PWA, live quiz, assistant); weak accessibility, oversized components, hard redirects |
| **Overall** | **3 / 5** | A capable, feature-complete product that needs a security hardening pass and an operational maturity pass to reach 5/5 |

The rest of this document lists findings ranked by priority, each with file references.

---

## P0 — Fix before further feature work

### 1. `/share/share-email` is an unauthenticated email relay with a client-controlled link
[server/app/share/routes.py:91](server/app/share/routes.py#L91) accepts any `recipient_email` and embeds the **client-supplied** `shareableLink` into the outgoing email, with no authentication and no per-route rate limit (only the global 200/hour/IP default). Anyone can use your Mailgun/SMTP identity to send phishing links to arbitrary addresses.
**Fix:** require an authenticated, verified user; build the link server-side from `share_url` + a validated quiz id; add a strict rate limit (e.g., `5/hour`).

### 2. Every quiz is publicly readable, including correct answers
`SharedQuizReadService.resolve_shared_quiz` ([server/app/share/services.py:73](server/app/share/services.py#L73)) fetches any quiz by id with no owner or "is shared" check and returns `correct_answer` for every question. There is no sharing opt-in flag, so any quiz id that leaks (logs, history, invitations) exposes private content. Similarly, `/share/get-quiz-id` ([server/app/share/routes.py:36](server/app/share/routes.py#L36)) hands out random quizzes — including user-generated ones — to anonymous callers. Compare with [canonical_quizzes.py:68](server/app/quiz/routes/canonical_quizzes.py#L68), which does enforce ownership.
**Fix:** add an explicit `is_shared` / `share_token` field set when a user shares; filter `get-quiz-id` to curated/public quizzes only; consider omitting `correct_answer` until submission for shared quizzes.

### 3. Proxy headers are ignored in production — rate limiting and cookie security are broken
Uvicorn is started without `--proxy-headers` ([docker-compose.prod.yml](docker-compose.prod.yml), server command), while nginx terminates TLS and proxies from 127.0.0.1 ([deploy/nginx-quiz-campilot.conf](deploy/nginx-quiz-campilot.conf)). Consequences:
- `get_remote_address` sees `127.0.0.1` for **every** request, so all per-IP rate limits ([server/app/core/rate_limiter.py:27](server/app/core/rate_limiter.py#L27)) are shared globally. One abusive client exhausts `AUTH_LOGIN = 5/minute` for every user on the platform — simultaneously a DoS vector and a useless brute-force control.
- `request.url.scheme` is always `http`, so the refresh-token cookie is set **without the `Secure` flag** ([server/app/auth/routes.py:102](server/app/auth/routes.py#L102)).
- Auth event logs record `127.0.0.1` as every login IP ([server/app/auth/routes.py:93](server/app/auth/routes.py#L93)), gutting the audit trail.
**Fix:** add `--proxy-headers --forwarded-allow-ips=<docker bridge>` to the uvicorn command (or set `FORWARDED_ALLOW_IPS`), and prefer `X-Forwarded-For` in the rate-limit key function.

### 4. No CI pipeline
There is no `.github/workflows` (or any CI config) in the repo. The backend has 36 test files under [server/tests](server/tests) and the client has Jest tests, but nothing runs them automatically; the root `package.json` test script is a no-op (`"echo \"No tests specified\""`). Husky/lint-staged only covers staged-file linting. Everything currently rests on developers remembering to run pytest locally before merging to `master`, which auto-deploys via [deploy/deploy.sh](deploy/deploy.sh).
**Fix:** add a CI workflow running `pytest` (with Mongo/Redis services or testcontainers), `pnpm test`, `next build`, and lint on every PR; make it required for merge.

---

## P1 — Security hardening

### 5. OTP generation and verification weaknesses
- OTPs come from `random.randint` ([server/app/auth/utils.py:29](server/app/auth/utils.py#L29)) — the Mersenne Twister is not cryptographically secure. Use `secrets.randbelow`. (Live-quiz access codes correctly use `secrets` — [live_session_service.py:541](server/app/quiz/services/live_session_service.py#L541).)
- The **password-reset OTP path has no attempt counter**: `reset_password_service` ([server/app/auth/services.py:464](server/app/auth/services.py#L464)) checks the OTP with a plain `!=` and never increments `password_reset_attempts` (the key is deleted in the request service but never enforced). Email verification does enforce 4 attempts ([services.py:163](server/app/auth/services.py#L163)); mirror that here.
- OTP comparisons use `!=` instead of `hmac.compare_digest` (used correctly for tokens on lines 215 and 475).

### 6. Verification credentials travel in URL query strings
`/auth/verify-otp/` and `/auth/verify-link/` take `email`, `otp`, and `token` as query parameters ([server/app/auth/routes.py:57](server/app/auth/routes.py#L57), [routes.py:64](server/app/auth/routes.py#L64); client: [authApi.ts:33](client/src/features/auth/api/authApi.ts#L33)). Query strings end up in nginx access logs, proxies, and browser history.
**Fix:** move to JSON request bodies.

### 7. Account enumeration inconsistencies
`request_password_reset_service` correctly returns a neutral message, but `reset_password_service` returns 404 "User not found" ([services.py:462](server/app/auth/services.py#L462)), `resend-verification` returns 404 ([services.py:130](server/app/auth/services.py#L130)), and registration returns "Email already registered" ([services.py:76](server/app/auth/services.py#L76)). Pick one policy (neutral responses) and apply it everywhere.

### 8. Frontend ships with zero security headers
[client/next.config.mjs](client/next.config.mjs) is empty: no CSP, `X-Frame-Options`/`frame-ancestors`, `Referrer-Policy`, or HSTS (nginx doesn't add them either). Given tokens live in `sessionStorage` ([client/src/shared/auth/tokenService.ts](client/src/shared/auth/tokenService.ts)) and the user's HuggingFace API token is also stored there in plaintext ([QuizForm.tsx:146](client/src/features/quiz/components/QuizForm.tsx#L146)), XSS is the primary client-side risk and a CSP is your main mitigation.
**Fix:** add a `headers()` block in next.config (CSP, HSTS, nosniff, frame-ancestors 'none') or set them in nginx.

### 9. Service worker caches authenticated API responses
[client/public/sw.js](client/public/sw.js) caches **every** successful GET — including cross-origin, `Authorization`-bearing API responses — into Cache Storage. Private quiz data, profile data, and history persist unencrypted on disk after logout, and stale API data can be served on network failure.
**Fix:** restrict the fetch handler to same-origin navigation/static assets; never cache requests with an `Authorization` header; clear caches on logout.

### 10. Miscellaneous backend security cleanups
- Rate-limit key uses Python's builtin `hash(token)` ([rate_limiter.py:25](server/app/core/rate_limiter.py#L25)) — hash randomization makes the key differ per process, so token-keyed limits silently fragment across workers/restarts. Use `hashlib.sha256`.
- `logout_service` decodes any JWT without checking `type` ([services.py:518](server/app/auth/services.py#L518)) — a refresh token works as a logout credential. Minor, but check `type == "access"`.
- `decode_token` ([utils.py:178](server/app/auth/utils.py#L178)) passes `algorithm=` (singular) to `jwt.decode`, so it always returns `None`. It's dead code — delete it before someone uses it.
- MongoDB runs without authentication in both compose files. It's on the internal Docker network, but one SSRF or container compromise away from full data access. Enable auth or at least document the accepted risk.
- `/ping-redis` ([router.py:40](server/app/api/router.py#L40)) creates an unpooled sync Redis client per call and is public; gate it or remove it.

---

## P2 — Robustness

### 11. Upload size is checked only after the full body is in memory
[document_quiz.py:83](server/app/quiz/routes/document_quiz.py#L83) does `await document_file.read()` and *then* compares against `DOCUMENT_UPLOAD_MAX_BYTES`. nginx's `client_max_body_size 25m` bounds production, but the app itself will buffer whatever it's given (and dev/docker-compose has no nginx). Stream to a spooled file with an incremental cap, or reject on `Content-Length` first.

### 12. Swallowed exceptions hide data loss
- [document_quiz.py:185](server/app/quiz/routes/document_quiz.py#L185): `except Exception: quiz_id = None` silently discards persistence failures — the user gets a quiz response but it was never saved, with no log line.
- File-type detection is extension-based only ([extract_text.py:84](server/app/quiz/utils/extract_text.py#L84)); a renamed file produces a confusing parser error rather than a clean 400. Consider magic-byte sniffing.
- Validation on the generation form is client-mirrored and server-enforced (good), and Pydantic schemas are used consistently — this is a genuine strength of the codebase, as is the v2 repository layer with schema validators and index management ([server/app/quiz/repositories/v2](server/app/quiz/repositories/v2)).

### 13. Expensive AI endpoints lack dedicated rate limits
`/api/get-questions` ([generation.py:19](server/app/quiz/routes/generation.py#L19)) and `/api/document-quizzes/generate` have no `@limiter.limit` decorator and allow anonymous use (`QUIZ_GENERATION_REQUIRES_AUTH` defaults to `False`, [config.py:66](server/app/core/config.py#L66)). The defined `RateLimits.QUIZ_GENERATE` constant is never applied to them. These are your most expensive endpoints (LLM calls, embeddings); they deserve the strictest anonymous limits.

---

## P2 — Efficiency

### 14. `last_seen_at` write on every authenticated request
`resolve_user_from_access_token` issues an `update_one` per request ([authentication.py:69](server/app/core/authentication.py#L69)). At any real traffic level this doubles Mongo write load for zero product value at that granularity. Debounce it (e.g., only write if >5 minutes stale) or move it to the refresh path.

### 15. Single-process serving
Production uvicorn runs one worker with no `--workers` flag ([docker-compose.prod.yml](docker-compose.prod.yml)). One CPU-bound task (PDF parsing, DOCX generation, embedding calls) stalls all requests. Run `--workers 2..4` (this will also surface the `hash(token)` fragmentation in #10) or front with gunicorn+uvicorn workers.

### 16. Small wins
- `/share/get-quiz-id` loads 50 full quiz documents to pick one at random ([share/routes.py:41](server/app/share/routes.py#L41)); use `$sample`.
- [ProfilePage.tsx](client/src/features/profile/pages/ProfilePage.tsx) is 1,047 lines and QuizForm 575 — split for maintainability and bundle size.
- Startup runs every index-ensure plus a backfill on each boot ([connection.py:131](server/app/db/core/connection.py#L131)); fine today, but move backfills to explicit migrations before data grows.

---

## P2 — Reliability & operations

### 17. Health checks don't check anything
`/api/healthcheck` returns a static object ([health.py](server/app/api/health.py)); deploy.sh's smoke test hits `/api` and `/`. Neither verifies Mongo or Redis connectivity, so a deploy with a dead database passes "health checks". Add a readiness endpoint that pings both, and use it in compose `healthcheck` blocks for `server`/`client` (currently only mongo/redis have them).

### 18. No observability or backups
- Logging is stdout-only `logging.basicConfig`; there is no error tracker (Sentry or similar) on either the API or the Next.js client, so production exceptions vanish into `docker logs`.
- No Mongo backup job exists on the single Hetzner host — one disk failure loses all user data. Add a nightly `mongodump` shipped off-host (even object storage) before anything else in this section.
- Dependency hygiene: the Docker build runs `pipenv install --skip-lock` ([Dockerfile](Dockerfile)) — the lockfile is copied but **ignored**, so every image build can resolve different versions. Also `node:18` is EOL; move to `node:22`. [server/requirements.txt](server/requirements.txt) is a 9-line subset of the Pipfile and the root `requirements.txt` is empty — delete or reconcile them to avoid split-brain dependency lists.
- Both Docker stages run as root; add a non-root user.

---

## P2 — UI/UX

### 19. Accessibility is minimal
~35 `aria-*` attributes across 14,500 lines of TSX, and almost no `role`/focus management in the many hand-rolled modals (Headless UI is a dependency but most modals are custom). Keyboard-trap and screen-reader behavior in `SignInModal`, `BrowseModal`, and the quiz flow need an audit pass. This is the biggest gap between "looks polished" and "is 5/5 UX".

### 20. Navigation and state rough edges
- Hard redirects via `window.location.assign` in the 403 interceptor ([http.ts:40](client/src/shared/api/http.ts#L40)) drop all client state; use the Next router.
- Quiz data is passed between pages via `sessionStorage`/`localStorage` blobs (`saved_quiz_view`, `generated_quiz_view` — [QuizDisplayPage.tsx:220](client/src/features/quiz/pages/QuizDisplayPage.tsx#L220)), which breaks refresh/deep-linking/multi-tab. Prefer id-based routes that fetch.
- Access token in `sessionStorage` means every new tab is logged out until refresh succeeds — acceptable security trade-off, but make sure the silent-refresh-on-load path is fast enough that users don't see logged-out flashes.
- `console.log`/`console.warn` calls ship to production (e.g., SW registration in [_app.tsx:25](client/pages/_app.tsx#L25)); strip via compiler option.

**Genuine UX strengths worth keeping:** consistent toast feedback, verification banner + progressive email verification flow, PWA with offline fallback, the axios refresh-queue implementation ([http.ts](client/src/shared/api/http.ts)) is textbook-correct, and error messages surfaced from API `detail` fields are user-readable.

---

## What's already good (don't break it)

- **Auth architecture** is above average for a project this size: refresh-token rotation with reuse detection and session revocation ([auth/services.py:371-399](server/app/auth/services.py#L371)), bcrypt-hashed refresh tokens at rest, session-backed access tokens, and an auth-events audit collection.
- **Provider tokens encrypted at rest** with Fernet ([connection.py:20](server/app/db/core/connection.py#L20)).
- **Internal MCP surface** is gated by a constant-time shared-secret check ([mcp/middleware.py:30](server/app/mcp/middleware.py#L30)) and has dedicated security tests.
- **CORS** rejects wildcard origins explicitly ([main.py:38](server/main.py#L38)).
- **The v2 data layer** (validators, indexes, dual-write migration staging, backfill tests) shows real engineering discipline.
- **Test breadth**: 36 backend test files covering auth, RAG, live-quiz timing/analytics, MCP security, and email adapters — the missing piece is CI (#4), not tests.

## Suggested order of work

1. **Week 1 (P0):** lock down `/share` endpoints (#1, #2), fix proxy headers (#3), stand up CI (#4).
2. **Week 2 (P1):** OTP hardening (#5), move credentials out of query strings (#6), security headers (#8), service-worker scope fix (#9), misc cleanups (#10, #7).
3. **Week 3+ (P2):** upload streaming (#11), rate limits on AI endpoints (#13), `last_seen_at` debounce (#14), workers (#15), real health checks + backups + Sentry (#17, #18), accessibility pass (#19), navigation state refactor (#20).

Re-scoring after the P0+P1 list lands would put security and reliability at 4+, and the P2 list is the path from 4 to 5.
