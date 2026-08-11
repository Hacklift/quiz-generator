---
name: debug-and-test
description: Workflow for running test suites (pytest, Jest), checking TypeScript types, diagnosing runtime exceptions, and verifying bug fixes across the stack.
---

# Debug and Test Skill

Follow this systematic workflow when executing tests, checking types, or diagnosing runtime errors.

## 1. Running Test Suites & Verification Checks

### Backend Pytest Suite (`server/`)
```bash
# Run all backend tests
cd server && pytest

# Run a specific test file
cd server && pytest tests/test_auth.py

# Run with verbose output and print statements
cd server && pytest -s -v tests/test_notifications.py
```

### Frontend Jest Suite & Type Checks (`client/`)
```bash
# Run Jest unit tests
cd client && pnpm test

# Run TypeScript type check (no code generation)
cd client && pnpm exec tsc --noEmit

# Run ESLint check
cd client && pnpm lint
```

---

## 2. Systematic Error Diagnosis Procedure

When diagnosing an error or bug report:

### Step 1: Inspect Full, Un-truncated Logs
- Never diagnose without reading actual tracebacks.
- Check backend container logs: `docker logs --tail 100 quiz-generator-server-1`.
- Check Celery worker logs: `docker logs --tail 100 quiz-generator-celery-1`.
- Check Next.js container logs: `docker logs --tail 100 quiz-generator-client-1`.

### Step 2: Identify Root Cause Layer
- **Config / Environment**: Check Pydantic settings in `server/app/core/config.py` vs `.env`.
- **Database / Query**: Check MongoDB connection, index options, or `ObjectId` parsing.
- **Async Task**: Check Redis connection or Celery task definitions in `server/celery_config.py`.
- **Frontend / Client**: Check browser console for network 401/403/500 failures or Next.js hydration issues.

### Step 3: Apply & Verify Fix
1. Modify code following repository conventions.
2. Run relevant unit tests (`pytest` / `pnpm test`).
3. Execute live health check: `curl.exe http://localhost:8000/api/readyz`.
