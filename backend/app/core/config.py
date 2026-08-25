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

    # Anthropic (Claude) — kept optional in case we switch back later
    anthropic_api_key: str | None = None
    #OpenRouter 
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://gorouter.app/v1"
    openrouter_model: str = "claude-3-5-sonnet-20241022"

    # Google Gemini — multiple keys (one per teammate) rotated to
    # spread out free-tier rate limits.
    gemini_api_key: str | None = None
    gemini_api_key_2: str | None = None
    gemini_api_key_3: str | None = None
    gemini_api_key_4: str | None = None

    # Voyage AI — same rotation idea
    voyage_api_key: str | None = None
    voyage_api_key_2: str | None = None
    voyage_api_key_3: str | None = None

    # Tavily — same rotation idea
    tavily_api_key: str | None = None
    tavily_api_key_2: str | None = None

   

   

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