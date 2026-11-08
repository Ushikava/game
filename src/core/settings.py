from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str
    secret_key: str = Field(min_length=32)
    algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=30, gt=0)
    password_hash_concurrency: int = Field(default=2, gt=0)
    password_hash_wait_seconds: float = Field(default=10, gt=0)
    login_rate_limit: int = Field(default=5, gt=0)
    login_rate_window_seconds: float = Field(default=60, gt=0)
    register_rate_limit: int = Field(default=5, gt=0)
    register_rate_window_seconds: float = Field(default=600, gt=0)


settings = Settings()
