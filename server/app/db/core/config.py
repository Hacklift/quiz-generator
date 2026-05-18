from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    JWT_SECRET: str = "test-secret"
    JWT_ALGORITHM: str = "HS256"
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 2
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENABLE_TEST_USER_ROUTES: bool = False
    ENABLE_PUBLIC_USER_LIST: bool = False

    email_sender: str = Field(
        default="test-sender@example.com",
        validation_alias="SENDER_EMAIL",
    )
    email_password: str = Field(
        default="test-password",
        validation_alias="SENDER_PASSWORD",
    )
    email_host: str = "localhost"
    email_port: int = 1025
    share_url: str = "http://localhost:3000"
    db_name: str = "quiz_generator"
    mongo_url: str = "mongodb://localhost:27017"
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
