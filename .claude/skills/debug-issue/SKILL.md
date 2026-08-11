---
name: debug-issue
description: Workflow for diagnosing and resolving runtime errors across FastAPI, MongoDB, Redis, Celery, and Next.js.
---

# Debug Issue Skill

Follow this systematic diagnostic workflow when investigating bugs, runtime exceptions, or failing container services.

## 1. Diagnostic Step-by-Step Procedure

### Step 1: Check Active Container & Service Status
Run `docker ps` to verify all 6 services are running:
* `quiz-generator-server-1` (FastAPI)
* `quiz-generator-client-1` (Next.js)
* `quiz-generator-celery-1` (Async Worker)
* `quiz-generator-mongodb-1` (Database)
* `quiz-generator-redis-1` (Cache & Celery Broker)

### Step 2: Inspect Un-truncated Error Logs
Check full logs for the failing container:
```bash
# Backend server startup or route exceptions
docker logs --tail 100 quiz-generator-server-1

# Celery email task failures
docker logs --tail 100 quiz-generator-celery-1

# Next.js hydration or dev server errors
docker logs --tail 100 quiz-generator-client-1
```

---

## 2. Common Gotchas & Fixes in This Repository

### 🐛 Backend Crash on Startup (`ValidationError`)
* **Symptom**: `server` container exits immediately with `pydantic_core._pydantic_core.ValidationError: Field required [type=missing]`.
* **Fix**: Ensure all required environment variables in `server/app/core/config.py` (e.g. `ASSISTANT_INTERNAL_MCP_SECRET`, `JWT_SECRET`, `MONGO_URI`) exist in `.env`. Run `docker compose up -d` after updating `.env`.

### 🐛 MongoDB Index Startup Failure (`IndexOptionsConflict`)
* **Symptom**: Startup fails when creating notification or quiz indexes (`expires_at_1` TTL index conflict).
* **Fix**: Check `ensure_notification_indexes` in `server/app/db/core/connection.py`. Ensure index creation specifies `expireAfterSeconds=0` and handles existing index option mismatches idempotently.

### 🐛 Next.js Blank Screen in Development (`Uncaught EvalError`)
* **Symptom**: `localhost:3000` renders a permanent dark splash overlay. Console logs `Uncaught EvalError: Evaluating a string as JavaScript violates Content Security Policy`.
* **Fix**: In `client/next.config.mjs`, ensure `script-src` includes `'unsafe-eval'` in development mode (`isDev ? " 'unsafe-eval'" : ""`). Restart client with `docker compose restart client`.

### 🐛 404 on Healthcheck Endpoint
* **Symptom**: `http://localhost:8000/health` returns `404 Not Found`.
* **Fix**: The backend prefix is `/api`. Use `http://localhost:8000/api/healthcheck` or `http://localhost:8000/api/readyz`.

---

## 3. Verification After Fix
1. Execute backend readiness check: `curl.exe http://localhost:8000/api/readyz`.
2. Execute frontend check: `curl.exe http://localhost:3000`.
3. Run test suites: `pytest` (server) and `pnpm test` (client).
