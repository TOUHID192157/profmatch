from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "ProfMatch"
    environment: str = "development"
    debug: bool = True

    # JWT Auth
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_db_url: str

    # Anthropic (Claude)
    anthropic_api_key: str | None = None

    # Voyage AI
    voyage_api_key: str | None = None

    # Tavily
    tavily_api_key: str | None = None

    # Resend
    resend_api_key: str | None = None
    email_from: str = "noreply@yourdomain.com"

    # CORS
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
