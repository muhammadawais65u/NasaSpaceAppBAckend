from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_db_url: str | None = None
    nasa_api_key: str = "DEMO_KEY"
    cors_origins: str = "*"
    demo_force_alert: Literal["calm", "watch", "storm"] | None = None
    local_db_path: str = "local_dev.db"

    @field_validator("supabase_url", "supabase_anon_key", "supabase_service_role_key",
                     "supabase_db_url", "demo_force_alert", mode="before")
    @classmethod
    def _blank_is_none(cls, v):
        return v.strip() or None if isinstance(v, str) else v

    @model_validator(mode="after")
    def _supabase_all_or_nothing(self):
        keys = (self.supabase_url, self.supabase_anon_key, self.supabase_service_role_key)
        if any(keys) and not all(keys):
            raise ValueError(
                "Set all of SUPABASE_URL, SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY, "
                "or none of them (local development mode).")
        return self

    @property
    def use_supabase(self) -> bool:
        return bool(self.supabase_url)


settings = Settings()
