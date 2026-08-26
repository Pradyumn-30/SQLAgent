"""
Centralized configuration for the Postgres Query Agent.

All environment variables are loaded and validated here, once, so that
every other module imports a single `settings` object instead of calling
os.getenv() scattered around the codebase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Postgres DB ---
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str
    pg_user: str
    pg_password: str

    # --- Redis ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    # --- Memory TTL ---
    memory_ttl_seconds: int = 604800  # 7 days default

    # --- Groq API (SQL generation & LLM) ---
    groq_api_key: str
    groq_model: str = "gpt-oss-20b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

# Singleton instance — import this everywhere else.
settings = Settings()