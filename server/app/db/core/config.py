import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class Settings(BaseModel):
    JWT_SECRET: str = "test-secret"
    JWT_ALGORITHM: str = "HS256"
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 2
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENABLE_TEST_USER_ROUTES: bool = False
    ENABLE_PUBLIC_USER_LIST: bool = False
    email_sender: str = "test-sender@example.com"
    email_password: str = "test-password"
    email_host: str = "localhost"
    email_port: int = 1025
    share_url: str = "http://localhost:3000"
    db_name: str = "quiz_generator"
    mongo_url: str = "mongodb://localhost:27017"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            JWT_SECRET=os.getenv("JWT_SECRET", "test-secret"),
            JWT_ALGORITHM=os.getenv("JWT_ALGORITHM", "HS256"),
            VERIFICATION_TOKEN_EXPIRE_HOURS=_get_int(
                "VERIFICATION_TOKEN_EXPIRE_HOURS", 2
            ),
            ACCESS_TOKEN_EXPIRE_MINUTES=_get_int(
                "ACCESS_TOKEN_EXPIRE_MINUTES", 30
            ),
            REFRESH_TOKEN_EXPIRE_DAYS=_get_int("REFRESH_TOKEN_EXPIRE_DAYS", 7),
            ENABLE_TEST_USER_ROUTES=_get_bool("ENABLE_TEST_USER_ROUTES", False),
            ENABLE_PUBLIC_USER_LIST=_get_bool("ENABLE_PUBLIC_USER_LIST", False),
            email_sender=os.getenv("SENDER_EMAIL", "test-sender@example.com"),
            email_password=os.getenv("SENDER_PASSWORD", "test-password"),
            email_host=os.getenv("EMAIL_HOST", "localhost"),
            email_port=_get_int("EMAIL_PORT", 1025),
            share_url=os.getenv("SHARE_URL", "http://localhost:3000"),
            db_name=os.getenv("DB_NAME", "quiz_generator"),
            mongo_url=os.getenv("MONGO_URL", "mongodb://localhost:27017"),
        )


@lru_cache()
def get_settings():
    return Settings.from_env()


settings = get_settings()
