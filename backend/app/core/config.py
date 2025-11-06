from functools import lru_cache
from pydantic import BaseSettings, AnyUrl
from typing import Optional


class Settings(BaseSettings):
    database_url: AnyUrl
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    redis_url: Optional[AnyUrl] = None
    edit_open_unprotected: bool = False
    timezone: str = "Asia/Seoul"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
