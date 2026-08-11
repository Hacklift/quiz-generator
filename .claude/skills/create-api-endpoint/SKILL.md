---
name: create-api-endpoint
description: Workflow for adding a new FastAPI endpoint, Pydantic schema, CRUD/repository handler, service function, and router registration in server/.
---

# Create API Endpoint Skill

Follow this workflow when adding or extending an API endpoint in the FastAPI backend (`server/`).

## Step 1: Define Pydantic Request & Response Schemas
Create or update models in `server/app/db/models/` or `server/app/schemas/`:
- Use Pydantic v2 syntax.
- Ensure all MongoDB `ObjectId` fields are serialized to string `id: str` in responses.
- Define explicit field types, defaults, and field validations.

```python
from pydantic import BaseModel, Field
from typing import Optional

class ItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class ItemResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    user_id: str
```

## Step 2: Implement CRUD / Repository Function
Add raw database operations in `server/app/db/crud/` or `server/app/quiz/repositories/v2/`:
- Keep CRUD operations isolated from HTTP requests.
- Filter operations by `user_id` when handling user-owned data to enforce tenancy.
- Handle database exceptions cleanly.

## Step 3: Implement Service Layer Logic
Add business logic and authorization in `server/app/db/services/` or `server/app/services/`:
- Enforce business validation rules (e.g. check resource existence, admin roles).
- Raise `HTTPException` with appropriate status codes (`400`, `401`, `403`, `404`).

## Step 4: Add FastAPI Route Handler
Create or update routes in `server/app/db/routes/` or appropriate domain route file under `server/app/`:
- Protect authenticated endpoints with `Depends(get_current_user)`.
- Decorate with `@limiter.limit(...)` if the endpoint is public or resource-intensive.
- Use explicit `response_model=...` parameters.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from server.app.dependancies import get_current_user

router = APIRouter()

@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: ItemCreate,
    current_user: dict = Depends(get_current_user)
):
    return await item_service.create_item_for_user(current_user["id"], payload)
```

## Step 5: Register Route in Main API Router
Mount the router inside `server/app/api/router.py`:
```python
router.include_router(new_feature_router, prefix="/api/new-feature", tags=["NewFeature"])
```

## Step 6: Add Unit Test
Add a corresponding test file under `server/tests/` using `pytest` and `httpx.AsyncClient` to verify success and authorization failure cases.
