from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://querypilot:querypilot@localhost:5437/querypilot"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 720
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    statement_timeout_ms: int = 8000
    max_sql_attempts: int = 3
    max_result_rows: int = 500


@lru_cache
def get_settings() -> Settings:
    return Settings()
