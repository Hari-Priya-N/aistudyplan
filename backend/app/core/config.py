"""
Central application settings.

Everything provider-specific (which LLM, which API key) is read ONLY from
environment variables here — never hardcoded, never imported directly by
business logic. Business logic depends on `Settings`, not on env vars
directly, and the LLM layer depends on `get_llm_provider()`, not on any
single vendor SDK.
"""
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM provider selection (provider-independent switch) ---
    llm_provider: Literal["grok", "openai", "gemini", "ollama", "mock"] = "mock"
    llm_model: str = "grok-2-latest"

    grok_api_key: str | None = None
    openai_api_key: str | None = None
    # Optional: point the OpenAI provider at any OpenAI-compatible server
    # (Groq, Together, a self-hosted vLLM, ...). Leave blank for api.openai.com.
    openai_base_url: str | None = None
    gemini_api_key: str | None = None

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # --- Auth ---
    jwt_secret_key: str = "insecure-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12

    # --- Database ---
    database_url: str = "sqlite:///./tutor.db"

    # --- Redis ---
    redis_url: str | None = "redis://localhost:6379/0"

    # --- Chroma ---
    chroma_mode: Literal["embedded", "http"] = "embedded"
    chroma_persist_dir: str = "./data/chroma"
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # --- App ---
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    app_timezone: str = "Asia/Kolkata"   # "today" for chat quotas / streaks

    # --- Student limits & motivation (mentor review requirements) ---
    allow_student_uploads: bool = False   # students see the upload page greyed out
    chat_daily_quota: int = 20            # Elara messages per student per day
    redeem_cost_points: int = 20          # points spent to unlock extra Elara messages
    redeem_bonus_messages: int = 5        # extra messages per redemption
    default_student_password: str = ""    # used by roster upload when no password/roll no

    # --- Bootstrap / demo ---
    seed_demo: bool = False               # create demo school data on first start
    admin_email: str | None = None        # create a management account on start
    admin_password: str | None = None

    # --- Hosting ---
    # Folder with the built frontend (frontend/dist). When present, the API
    # also serves the web app, so the whole project runs as ONE web service.
    static_dir: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
