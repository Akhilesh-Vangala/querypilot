from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_environment: Literal["development", "test", "production"] = "development"
    database_url: str = (
        "postgresql+psycopg://querypilot:querypilot@localhost:5437/querypilot"
    )
    warehouse_database_url: str = ""
    jwt_secret: str = "local-development-secret-change-before-hosting-0000000000"
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_minutes: int = Field(default=60, ge=5, le=720)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    allow_live_ai: bool = False
    statement_timeout_ms: int = Field(default=8000, ge=100, le=30000)
    max_sql_attempts: int = Field(default=3, ge=1, le=4)
    max_result_rows: int = Field(default=500, ge=1, le=500)
    max_model_rounds: int = Field(default=8, ge=2, le=12)
    max_prompt_chars: int = Field(default=48000, ge=4000, le=80000)
    max_output_tokens: int = Field(default=1024, ge=128, le=2048)
    max_run_tokens: int = Field(default=24000, ge=1000, le=40000)
    allowed_origins: str = "http://localhost:3007,http://127.0.0.1:3007,http://localhost:5173,http://127.0.0.1:5173"
    public_demo: bool = False
    embedded_worker: bool = False
    seed_demo: bool = False
    demo_accounts: bool = False
    auto_create_schema: bool = True

    @model_validator(mode="after")
    def production_boundary(self):
        if self.app_environment == "production":
            if len(self.jwt_secret) < 48 or any(
                marker in self.jwt_secret.lower()
                for marker in ("development", "change", "replace", "placeholder")
            ):
                raise ValueError(
                    "Production requires a private JWT_SECRET of at least 48 characters"
                )
            if not self.database_url.startswith(
                "postgresql"
            ) or not self.warehouse_database_url.startswith("postgresql"):
                raise ValueError(
                    "Production requires persistent PostgreSQL and a separate read-only warehouse URL"
                )
            if (
                self.seed_demo
                or self.demo_accounts
                or self.public_demo
                or self.embedded_worker
                or self.auto_create_schema
            ):
                raise ValueError(
                    "Production requires separate migration/worker processes and no public demo accounts"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
