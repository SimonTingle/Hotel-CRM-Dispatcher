from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    wa_verify_token: SecretStr
    wa_phone_number_id: str
    wa_access_token: SecretStr
    wa_app_secret: SecretStr

    gemini_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")

    redis_url: str = "redis://localhost:6379/0"
    redis_session_ttl_hours: int = 24

    supabase_url: str
    supabase_service_role_key: SecretStr
    db_encryption_key: SecretStr = SecretStr("changeme-32-chars-exactly-padded!")

    ops_whatsapp_group_id: str
    admin_api_key: SecretStr

    test_mode: bool = False
    ai_provider: Literal["gemini", "openai"] = "gemini"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        secrets_strip_whitespace=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
