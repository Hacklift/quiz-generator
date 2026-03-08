from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class QuizEventRecord(BaseModel):
    quiz_id: str
    event_type: Literal["generated", "viewed", "shared", "downloaded", "saved", "attempted"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
