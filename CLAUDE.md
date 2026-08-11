# CLAUDE.md — Quiz Generator Repository Guide

This document provides repository-specific guidelines, architecture maps, developer commands, and coding conventions for Claude working in the `quiz-generator` codebase.

---

## 1. Project Overview & Architecture

`quiz-generator` is an AI-powered full-stack quiz platform. It enables AI quiz generation, live quiz sessions with real-time scoring, folder/category management, and user notifications.

### Monorepo Structure:
* **`server/`**: FastAPI (Python 3.12) backend server.
  * **Database & Caching**: MongoDB (Motor / PyMongo / Beanie / v2 Repositories) + Redis.
  * **Async Tasks**: Celery worker for email delivery (`server.celery_config`).
  * **AI Integrations**: LangChain, OpenAI, Google Gemini, Groq, FastMCP (`server/app/mcp/`).
  * **Authentication**: JWT Access (30m) & Refresh token (7d) rotation with JTI blacklisting.
* **`client/`**: Next.js 14 (TypeScript, Pages Router) frontend.
  * **Styling**: Tailwind CSS, shared UI tokens in `client/src/shared/ui/quizwerk.ts`.
  * **Feature Modules**: Organized under `client/src/features/<feature_name>/`.
  * **API Client**: Axios instance (`client/lib/functions/auth.ts` / `client/src/shared/api/http.ts`) with token auto-refresh interceptors.
* **`deploy/`**: Infrastructure, Nginx configurations, and deployment scripts.

---

## 2. Essential Commands

### Environment Setup & Container Management
```bash
# Start all 6 services via Docker Compose (Recommended)
docker compose up -d

# View container logs
docker logs -f quiz-generator-server-1
docker logs -f quiz-generator-client-1

# Restart specific service after config change
docker compose restart server celery client

# Stop all containers
docker compose down
```

### Local Development (Without Docker)
```bash
# 1. Backend Server (from /server)
cd server
pipenv shell
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000

# 2. Celery Worker (from /server)
celery -A server.celery_config.celery_app worker -Q email,celery --loglevel=info --pool=solo --concurrency=1

# 3. Next.js Frontend (from /client)
cd client
pnpm dev
```

### Testing & Linting
```bash
# Run Backend Pytest Suite
cd server
pytest

# Run Client Unit Tests
cd client
pnpm test

# Run Type Checking & Linting
cd client
pnpm lint
pnpm exec tsc --noEmit
```

---

## 3. Code Conventions & Architectural Rules

### Backend (`server/`)
1. **Layer Separation**: Route (`routes/`) ➔ Service (`services/`) ➔ CRUD/Repository (`crud/` / `repositories/v2`).
2. **Pydantic Schemas**: Use Pydantic v2 models for request/response bodies. Never leak raw MongoDB `ObjectId` instances to the client; convert `_id` to `id: str`.
3. **Authentication**: Enforce authentication using `get_current_user` from `server.app.dependancies` or `server.app.core.authentication`.
4. **Error Handling**: Raise explicit `HTTPException(status_code=..., detail=...)`. Avoid swallowing exceptions in silent `try/except` blocks.
5. **Rate Limiting**: Apply `@limiter.limit(...)` to public or resource-intensive endpoints (e.g. AI quiz generation, password reset, email dispatches).

### Frontend (`client/`)
1. **Feature-First Architecture**: Group code by feature under `client/src/features/<feature>/`:
   * `components/`: UI components specific to the feature.
   * `api/` or `lib/`: Feature API call helpers.
   * `types/` or `interfaces/`: TypeScript interfaces and models.
2. **Pages Router Alignment**: Top-level routes reside in `client/pages/` and re-export page components from `client/src/features/`.
3. **Route Constants**: Use `ROUTES` from `client/constants/patterns/routes.ts` or `client/src/shared/config/patterns/routes.ts` instead of hardcoded route strings.
4. **State Management**: Keep transient UI state in React components/contexts. Use the central Axios client for API communications.

---

## 4. Key References & Security Guardrails

* **Principal Security Scorecard**: Refer to [`ENGINEERING_REVIEW.md`](file:///c:/Users/hp/Desktop/Hacklift/quiz-generator/ENGINEERING_REVIEW.md) before making security-sensitive changes (Auth, `/share` endpoints, Rate Limits, Proxy headers).
* **Auth Mechanics**: Refer to [`auth_architecture_review.txt`](file:///c:/Users/hp/Desktop/Hacklift/quiz-generator/auth_architecture_review.txt) for token rotation, OTP expirations, and Redis keys.
* **Notification Subsystem**: Refer to [`notification-ui-implementation.md`](file:///c:/Users/hp/Desktop/Hacklift/quiz-generator/notification-ui-implementation.md) for notification types and MongoDB index structures.

---

## 5. Claude Skills in This Repository

Structured workflows for common tasks are located in `.claude/skills/`:
* `create-api-endpoint`: Adding FastAPI routes, schemas, services, and tests.
* `create-frontend-feature`: Building feature components, API clients, and Next.js pages.
* `run-tests`: Executing backend `pytest` and frontend `Jest` suites.
* `security-audit`: Reviewing changes against project security checklists.
* `debug-issue`: Diagnosing backend, database, Celery, and frontend errors.
