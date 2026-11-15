from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    nasa_api_key: str
    cors_origins: str = "*"
    demo_force_alert: str | None = None


settings = Settings()
