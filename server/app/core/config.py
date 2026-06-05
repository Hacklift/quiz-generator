from functools import lru_cache
from typing import Literal, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 2
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENABLE_TEST_USER_ROUTES: bool = False
    ENABLE_PUBLIC_USER_LIST: bool = False

    email_sender: str
    email_password: str
    email_host: str
    email_port: int
    share_url: str
    db_name: str = "quizApp_db"
    mongo_url: str = Field(
        validation_alias=AliasChoices("mongo_url", "MONGO_URI"),
    )
    HF_QUIZ_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    HF_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    DOCUMENT_UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024
    DOCUMENT_RAG_MAX_CHUNKS: int = 24
    DOCUMENT_RAG_TOP_K: int = 8
    DOCUMENT_CHUNK_SIZE_CHARS: int = 1600
    DOCUMENT_CHUNK_OVERLAP_CHARS: int = 220
    QUIZ_V2_WRITE_MODE: Literal["legacy_only", "dual_write", "v2_only"] = "v2_only"
    QUIZ_V2_FAIL_OPEN: bool = True
    QUIZ_V2_STRUCTURED_LOGGING: bool = True
    V2_BACKFILL_BATCH_SIZE: int = 200
    V2_BACKFILL_DRY_RUN: bool = True
    V2_BACKFILL_START_AFTER_ID: Optional[str] = None
    V2_BACKFILL_LIMIT: Optional[int] = None
    V2_BACKFILL_COLLECTIONS: str = "quizzes,saved,history,folders"
    V2_BACKFILL_RUN_ID: Optional[str] = None
    V2_BACKFILL_LOCK_LEASE_SECONDS: int = 600

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
