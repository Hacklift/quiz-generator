---
name: database-and-models
description: Guide for handling MongoDB models, Pydantic v2 schemas, database collections, index management, and backfill migrations in server/.
---

# Database and Models Skill

Follow this workflow when modifying database schemas, MongoDB collections, indexes, or repository query layers in `server/`.

## 1. MongoDB & PyMongo Connection Context
MongoDB connection handles and database references are defined in `server/app/db/core/connection.py`.
- Primary database name: `quizApp_db` (configured via `DB_NAME` / `MONGO_URI`).
- Connection collections are accessed via helper functions (e.g. `get_users_collection()`, `get_quizzes_collection()`, `get_notifications_collection()`).

---

## 2. ObjectId Conversion Standard

MongoDB uses `BSON ObjectId` for `_id` values, but API contracts MUST expose string IDs.

### In Pydantic Models:
```python
from pydantic import BaseModel, Field
from typing import Optional

class UserOut(BaseModel):
    id: str = Field(alias="_id")
    email: str
    role: str = "user"
```

### In Repository / CRUD functions:
```python
from bson import ObjectId
from fastapi import HTTPException

def parse_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")
```

---

## 3. Creating & Maintaining Database Indexes

Indexes must be registered inside `server/app/db/core/connection.py` during `startUp()` or within repository initialization:
- Ensure compound index order matches query patterns (e.g., `[("user_id", 1), ("created_at", -1)]`).
- Handle TTL indexes (`expireAfterSeconds=0`) idempotently to prevent `IndexOptionsConflict` errors during server restarts.

```python
async def ensure_custom_indexes(collection):
    await collection.create_index(
        [("user_id", 1), ("created_at", -1)],
        name="user_created_idx"
    )
```

---

## 4. Repository v2 Migration Pattern
For quiz data access, prefer the repository v2 abstraction under `server/app/quiz/repositories/v2/`.
- Use schema validators before write operations.
- Maintain dual-write or backfill staging logic when modifying legacy collection shapes.
