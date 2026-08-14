---
name: codebase-navigation
description: Workflow for mapping domain entities, tracing end-to-end data flows, and locating relevant code across the quiz-generator monorepo.
---

# Codebase Navigation Skill

Follow this workflow when navigating the repository, locating files, or tracing features across the full stack.

## 1. Monorepo Map & Feature Locations

### Backend Domain Boundaries (`server/app/`)
* **Auth & Security**: `server/app/auth/` (`routes.py`, `services.py`, `utils.py`)
* **Database & Core Systems**: `server/app/db/core/` (`connection.py`, `redis.py`); models, schemas, repositories, services, and routes are owned by their domains
* **Quiz Management & Generation**: `server/app/quiz/` (`routes/`, `services/`, `repositories/v2/`, `seed_data/`)
* **Live Quiz Real-time Sessions**: `server/app/quiz/routes/live_sessions.py`, `server/app/quiz/services/live_session_service.py`
* **Notifications**: `server/app/notifications/` (`routes.py`, `services.py`, `repository.py`, `schemas.py`)
* **Internal MCP Server**: `server/app/mcp/` (`server.py`, `middleware.py`, `handlers/`)
* **AI Research Assistant**: `server/app/assistant/` (`routes.py`, `service.py`, `mcp_client.py`)
* **Billing & Stripe**: `server/app/billing/` (`routes.py`, `services.py`)
* **Public Sharing**: `server/app/share/` (`routes.py`, `services.py`)

### Frontend Feature Boundaries (`client/src/features/`)
* **Authentication**: `client/src/features/auth/` (`components/`, `api/`, `context/`, `types/`)
* **Quiz Generation & Forms**: `client/src/features/quiz/` (`components/`, `pages/`, `api/`)
* **Live Quiz Sessions**: `client/src/features/live-quiz/`
* **Notifications**: `client/src/features/notifications/`
* **User Profile & Billing**: `client/src/features/profile/`
* **Folders & Categories**: `client/src/features/folders/`, `client/src/features/categories/`
* **AI Assistant**: `client/src/features/assistant/`
* **Shared UI & Client Config**: `client/src/shared/` (`api/http.ts`, `ui/quizwerk/`, `config/`)

---

## 2. End-to-End Feature Tracing Procedure

When asked to trace how a feature or API endpoint works:

1. **Locate Route Definition**: Find the route handler in the domain's `routes.py` or `routes/` package, starting from its registration in `server/app/api/router.py`.
2. **Inspect Request/Response Schemas**: Check the domain's `schemas.py`, `schemas/`, or `models/` paths (for example, `server/app/notifications/schemas.py` and `server/app/quiz/schemas/`).
3. **Trace Service Logic**: Inspect business logic and authorization checks in the domain's `services.py`, `service.py`, or `services/` package.
4. **Inspect Database Access**: Check the domain repository (for example, `server/app/notifications/repository.py`, `server/app/users/repository.py`, or `server/app/quiz/repositories/`).
5. **Trace Frontend API Call**: Find the corresponding API function under `client/src/features/<feature>/api/`.
6. **Inspect UI Components**: Locate the rendering React components under `client/src/features/<feature>/components/` or `client/pages/`.

---

## 3. Quick File Discovery Strategies
* To find backend routes: Look at `server/app/api/router.py` to see all mounted routers.
* To find frontend pages: Look at `client/pages/` and `client/src/shared/config/patterns/routes.ts`.
* To check database collections: Look at `server/app/db/core/connection.py`.
