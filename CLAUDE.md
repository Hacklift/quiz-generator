# CLAUDE.md — Quiz Generator Repository Guide

This guide equips Claude (CLI and AI agents) to navigate, understand, build, test, and refactor code across the `quiz-generator` monorepo autonomously.

---

## 0. Inspect Before Acting

Repository code is the source of truth. Before proposing or making a change:

1. Inspect the relevant directory and neighboring implementation; do not infer a path, module, symbol, schema, command, or API contract from this guide alone.
2. Trace registrations and consumers before editing: start backend routes at `server/app/api/router.py`, frontend routes at `client/pages/`, database access at `server/app/db/core/connection.py`, and feature API calls under `client/src/features/`.
3. Search for the current convention and copy a working nearby pattern. Domain layouts vary between singular files (`routes.py`, `services.py`, `repository.py`) and packages (`routes/`, `services/`, `repositories/`).
4. Read the relevant tests and configuration before changing behavior. Preserve public API and stored-data contracts unless the task explicitly requires a coordinated change.
5. Verify every referenced path and imported/exported symbol exists, then run the narrowest relevant checks. If documentation and implementation disagree, follow the implementation and update the documentation when it is in scope.

---

## 1. Repository Architecture & Domain Map

`quiz-generator` is a full-stack, AI-powered quiz platform. It provides automated quiz generation (via LLMs & RAG), live quiz sessions with real-time scoring, folder/category organization, user notifications, and role-based access control.

```text
quiz-generator/
├── server/                         # FastAPI (Python 3.12) Backend
│   ├── main.py                     # App entry point, CORS, lifespan & MCP mounting
│   ├── celery_config.py            # Celery async worker & Redis broker config
│   └── app/
│       ├── api/                    # Central APIRouter & route mounting (router.py)
│       ├── auth/                   # JWT Auth, OTP, verification, services & routes
│       ├── db/core/                # MongoDB/Redis connections and collection getters
│       ├── quiz/                   # Quiz generation, document RAG, live sessions, repositories (v2)
│       ├── mcp/                    # Internal FastMCP server & auth middleware
│       ├── email_platform/         # Email sending policy engine & Celery tasks
│       ├── billing/                # Stripe checkout & subscription management
│       ├── assistant/              # AI research assistant service & routes
│       ├── users/                  # User profile & management routes
│       └── share/                  # Public quiz sharing routes & services
├── client/                         # Next.js 14 (TypeScript, Pages Router) Frontend
│   ├── pages/                      # Top-level page routes re-exporting feature views
│   ├── public/                     # Static assets (images, PWA manifest, service worker)
│   └── src/
│       ├── features/               # Feature-first modules (auth, quiz, live-quiz, notifications, etc.)
│       └── shared/                 # Axios client, shared config, and quizwerk UI system
├── deploy/                         # Nginx configs & production deployment scripts
└── .github/workflows/               # CI pipelines & automated Claude PR review workflows
```

---

## 2. Core Engineering Commands

### Environment & Containers
```bash
# Start all 6 orchestrated services (Recommended)
docker compose up -d

# View container logs
docker logs -f quiz-generator-server-1
docker logs -f quiz-generator-client-1

# Restart backend or client after config changes
docker compose restart server celery client
```

### Local Execution (Without Docker)
```bash
# 1. Backend Server (run from /server; uses the Pipfile environment)
cd server && pipenv run fastapi dev main.py

# 2. Celery Async Worker (run from the repository root)
celery -A server.celery_config.celery_app worker -Q email,celery --loglevel=info --pool=solo --concurrency=1

# 3. Next.js Frontend (run from /client)
cd client && pnpm dev
```

### Testing, Types & Linting
```bash
# Backend Test Suite (Pytest)
cd server && pytest

# Frontend Unit Tests (Jest)
cd client && pnpm test

# Frontend Type Check & Linting
cd client && pnpm exec tsc --noEmit
cd client && pnpm lint
```

---

## 3. End-to-End Data Flow Pattern

When implementing or modifying a feature across the stack, follow this data flow:

```text
[Frontend View Component] 
       ↓ (uses typed helper)
[client/src/features/<feature>/api/] 
       ↓ (Axios HTTP request with Bearer token & auto-refresh)
[client/src/shared/api/http.ts] 
       ↓ (HTTP REST / JSON)
[server/app/api/router.py] ➔ [FastAPI Route Handler in server/app/<domain>/routes.py or routes/]
       ↓ (validates request via Pydantic model & Depends(get_current_user))
[Service Layer in server/app/<domain>/services.py or services/]
       ↓ (executes business logic & authorization checks)
[Domain Repository in server/app/<domain>/repository.py or repositories/]
       ↓ (PyMongo / Motor queries)
[MongoDB Database (quizApp_db)]
```

---

## 4. Key Coding Conventions & Guidelines

### Backend (`server/`)
1. **Model Validation**: Use Pydantic v2 schemas for request and response models.
2. **MongoDB ObjectId Handling**: Never leak raw `ObjectId` instances in API responses. Serialize `_id` to string `id: str` in Pydantic response models.
3. **Authentication**: Protect user endpoints using `Depends(get_current_user)`.
4. **Error Handling**: Raise explicit `HTTPException(status_code=..., detail=...)`.
5. **Rate Limiting**: Apply `@limiter.limit(...)` to public or heavy AI generation endpoints.

### Frontend (`client/`)
1. **Feature-First Organization**: Place code under `client/src/features/<feature>/` (`components/`, `api/`, `types/`, `pages/`).
2. **Pages Router Integration**: Top-level routes in `client/pages/` must re-export page components from `client/src/features/`.
3. **Design System & Styling**: Use Tailwind CSS and the shared Quizwerk exports under `client/src/shared/ui/quizwerk/`.
4. **Route Constants**: Reuse existing route paths from `ROUTES` in `client/src/shared/config/patterns/routes.ts` (`@shared/config/patterns/routes`) and add a constant there when a reusable route is introduced.

---

## 5. Security & Architecture References

Before making architectural or security-sensitive changes, consult:
* [`ENGINEERING_REVIEW.md`](ENGINEERING_REVIEW.md): Principal engineer scorecard, P0/P1 security risks, rate limits, proxy headers.
* [`auth_architecture_review.txt`](auth_architecture_review.txt): JWT token rotation mechanics, OTP expiration windows, Redis key schemas.
* [`notification-ui-implementation.md`](notification-ui-implementation.md): Notification backend CRUD, indexes, and UI bell/inbox patterns.

---

## 6. Available Claude Skills

Structured engineering workflows are available in `.claude/skills/`:
* `codebase-navigation`: Map domain entities and trace full-stack data flows.
* `create-api-endpoint`: Build/modify FastAPI endpoints, Pydantic schemas, service logic, and pytest cases.
* `create-frontend-feature`: Build/modify Next.js feature modules, Axios helpers, UI tokens, and pages.
* `database-and-models`: Handle MongoDB schemas, Pydantic v2 validations, indexes, and ObjectId conversions.
* `debug-and-test`: Execute test suites (`pytest`, `pnpm test`, `tsc`) and trace cross-stack errors.
* `code-review-and-refactor`: Audit code against security rules, refactor large files, and verify zero broken contracts.
