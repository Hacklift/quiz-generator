from typing import List, Optional

from pydantic import BaseModel, Field

from server.app.quiz.models.quiz_models import QuizQuestion


class DocumentQuizResponse(BaseModel):
    source: str
    questions: List[QuizQuestion]
    title: str
    description: str
    ai_down: Optional[bool] = False
    notification_message: Optional[str] = None
    quiz_id: Optional[str] = None
    live_quiz_enabled: Optional[bool] = False
    access_code: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    access_code_expires_at: Optional[str] = None
    category: Optional[str] = None
    category_slug: Optional[str] = None
    subcategory: Optional[str] = None
    subcategory_slug: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    classification: Optional[dict] = None
    source_document_type: str
    source_document_name: str
    source_characters: int
    total_source_chunks: int
    retrieved_chunks: int
    retrieval_query: str
    rag_strategy: str = "embedding_mmr"
    embedding_cache_hit: Optional[bool] = False
