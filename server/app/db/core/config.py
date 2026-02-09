from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 2
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    email_sender: str
    email_password: str
    email_host: str
    email_port: int
    share_url: str
    db_name: str
    mongo_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()