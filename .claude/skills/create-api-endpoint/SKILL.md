---
name: create-api-endpoint
description: Complete workflow for creating or modifying FastAPI endpoints, Pydantic v2 schemas, service functions, CRUD/repository handlers, rate limiting, and pytest cases in server/.
---

# Create API Endpoint Skill

Follow this workflow when building or updating endpoints in the FastAPI backend (`server/`).

## Step 1: Define Pydantic Request & Response Schemas
Define Pydantic v2 models in `server/app/db/models/` or domain schema files:
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
Add database operations in `server/app/db/crud/` or `server/app/quiz/repositories/v2/`:
- Ensure queries filter by `user_id` when handling private data to enforce tenancy.
- Handle database execution safely.

## Step 3: Implement Service Layer Logic
Add business validation and authorization in `server/app/<domain>/services/`:
- Verify caller permissions (e.g. check admin role or resource ownership).
- Raise explicit `HTTPException(status_code=..., detail=...)`.

## Step 4: Add FastAPI Route Handler
Create or update route functions in `server/app/<domain>/routes/` or `server/app/db/routes/`:
- Protect private endpoints using `current_user: dict = Depends(get_current_user)`.
- Decorate with `@limiter.limit(...)` if the endpoint is public or CPU-intensive.
- Use explicit `response_model=...` parameters.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from server.app.dependancies import get_current_user
from server.app.core.rate_limiter import limiter

router = APIRouter()

@router.post("/search", response_model=List[QuizSummaryResponse])
@limiter.limit("30/minute")
async def search_quizzes(
    request: Request,
    payload: QuizFilterRequest,
    current_user: dict = Depends(get_current_user)
):
    return await quiz_service.search_user_quizzes(current_user["id"], payload)
```

## Step 5: Mount Router in Main API Router
Ensure the router is registered inside `server/app/api/router.py`:
```python
router.include_router(feature_router, prefix="/api/feature", tags=["Feature"])
```

## Step 6: Write Pytest Test Case
Create a test in `server/tests/` to verify success, validation errors (400), unauthenticated access (401), and unauthorized access (403).
