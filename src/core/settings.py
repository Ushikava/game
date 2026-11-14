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
    login_failures_per_account_ip: int = Field(default=10, gt=0)
    login_failures_per_account_ip_window_seconds: float = Field(default=900, gt=0)
    login_failures_per_account: int = Field(default=50, gt=0)
    login_failures_per_account_window_seconds: float = Field(default=3600, gt=0)
    login_failures_per_ip: int = Field(default=100, gt=0)
    login_failures_per_ip_window_seconds: float = Field(default=900, gt=0)
    register_per_ip: int = Field(default=20, gt=0)
    register_per_ip_window_seconds: float = Field(default=3600, gt=0)
    password_confirm_failures: int = Field(default=10, gt=0)
    password_confirm_failures_window_seconds: float = Field(default=900, gt=0)
    ws_max_connections: int = Field(default=500, gt=0)
    ws_max_pending: int = Field(default=256, gt=0)
    ws_max_pending_per_ip: int = Field(default=32, gt=0)
    ws_messages_per_second: float = Field(default=20, gt=0)
    ws_message_burst: int = Field(default=40, gt=0)


settings = Settings()
