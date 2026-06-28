"""AIHOT backend configuration.

All sensitive values MUST be set via environment variables or .env file.
No secrets should ever live in this file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ===== app =====
    app_name: str = "AIHOT"
    app_version: str = "0.1.0"
    debug: bool = False

    # ===== database (reuse existing postgresql container in 1panel-network) =====
    database_url: str = ""

    # ===== redis =====
    redis_url: str = ""

    # ===== LLM endpoints =====
    qwenpaw_base_url: str = ""
    qwenpaw_api_key: str = ""
    litellm_base_url: str = ""
    litellm_api_key: str = ""
    agnes_base_url: str = "https://apihub.agnes-ai.com/v1"
    agnes_api_key: str = ""
    agnes_model: str = "agnes-2.0-flash"
    default_model: str = "agnes-2.0-flash"

    # ===== scoring/clustering =====
    embedding_dim: int = 1024
    similarity_threshold: float = 0.82

    # ===== scheduler =====
    scraper_interval_minutes: int = 30
    digest_send_hour: int = 8
    digest_timezone: str = "Asia/Shanghai"

    # ===== admin auth (basic auth for /admin) =====
    admin_user: str = "aihot"
    admin_pass: str = ""
    session_secret: str = ""

    # ===== push channels =====
    feishu_webhook_url: str = ""
    feishu_webhook_secret: str = ""
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = ""

    @property
    def is_production(self) -> bool:
        return bool(self.admin_pass) and self.admin_pass != "changeme"


@lru_cache
def get_settings() -> Settings:
    return Settings()
