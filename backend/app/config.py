from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Bitlance AI Agent"
    debug: bool = False
    version: str = "1.0.0"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/bitlance"
    database_url_sync: str = "postgresql://postgres:password@localhost:5432/bitlance"

    # JWT
    secret_key: str = "supersecretkey-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # AI
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    grok_api_key: str = ""
    ai_model: str = "llama-3.3-70b-versatile"

    # Escrow
    platform_fee_percent: float = 5.0

    # Docker sandbox
    sandbox_image: str = "bitlance-sandbox:latest"
    sandbox_timeout_seconds: int = 30

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
