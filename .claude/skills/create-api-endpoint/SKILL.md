---
name: create-api-endpoint
description: Complete workflow for creating or modifying FastAPI endpoints, Pydantic v2 schemas, service functions, CRUD/repository handlers, rate limiting, and pytest cases in server/.
---

# Create API Endpoint Skill

Follow this workflow when building or updating endpoints in the FastAPI backend (`server/`).

## Step 1: Define Pydantic Request & Response Schemas
Define Pydantic v2 models in the owning domain's existing `schemas.py`, `schemas/`, or `models/` location. Inspect neighboring routes and models before choosing a file:
- Never leak raw MongoDB `ObjectId` instances in response models. Convert `_id` to `id: str`.
- Specify field descriptions, constraints (`min_length`, `ge`), and defaults.

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class QuizFilterRequest(BaseModel):
    category: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)

class QuizSummaryResponse(BaseModel):
    id: str
    title: str
    category: str
    question_count: int
```

## Step 2: Implement CRUD / Repository Function
Add database operations to the owning domain's repository layer. Examples include `server/app/users/repository.py`, `server/app/notifications/repository.py`, and `server/app/quiz/repositories/` (including `v2/`):
- Ensure queries filter by `user_id` when handling private data to enforce tenancy.
- Handle database execution safely.

## Step 3: Implement Service Layer Logic
Add business validation and authorization in the owning domain's existing `services.py`, `service.py`, or `services/` package:
- Verify caller permissions (e.g. check admin role or resource ownership).
- Raise explicit `HTTPException(status_code=..., detail=...)`.

## Step 4: Add FastAPI Route Handler
Create or update route functions in the owning domain's `routes.py` or `routes/` package:
- Import `UserOut` from `server.app.users.models` and protect private endpoints with `current_user: UserOut = Depends(get_current_user)`.
- Access the authenticated user through attributes such as `current_user.id`; `get_current_user` does not return a dictionary.
- Decorate with `@limiter.limit(...)` if the endpoint is public or CPU-intensive.
- Use explicit `response_model=...` parameters.

```python
from fastapi import APIRouter, Depends, Request
from server.app.core.dependencies import get_current_user
from server.app.core.rate_limiter import limiter
from server.app.users.models import UserOut

router = APIRouter()

@router.post("/search", response_model=List[QuizSummaryResponse])
@limiter.limit("30/minute")
async def search_quizzes(
    request: Request,
    payload: QuizFilterRequest,
    current_user: UserOut = Depends(get_current_user)
):
    return await quiz_service.search_user_quizzes(current_user.id, payload)
```

## Step 5: Mount Router in Main API Router
Ensure the router is registered inside `server/app/api/router.py`:
```python
router.include_router(feature_router, prefix="/api/feature", tags=["Feature"])
```

## Step 6: Write Pytest Test Case
Create a test in `server/tests/` to verify success, validation errors (400), unauthenticated access (401), and unauthorized access (403).
