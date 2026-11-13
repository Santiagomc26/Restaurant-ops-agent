from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class MessagingChannel(StrEnum):
    # The simulator lets the whole agent run end-to-end without spending
    # WhatsApp messages; switching channels is a config change, not a code change.
    SIMULATOR = "simulator"
    WHATSAPP = "whatsapp"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Restaurant Ops Agent"
    app_version: str = "0.1.0"
    app_env: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
    restaurant_timezone: str = "America/Bogota"

    # SQLAlchemy URL: moving to PostgreSQL only requires changing this value.
    database_url: str = "sqlite:///./data/restaurant.db"

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:14b"
    ollama_timeout_seconds: float = Field(default=120.0, gt=0)

    messaging_channel: MessagingChannel = MessagingChannel.SIMULATOR
    whatsapp_api_version: str = "v23.0"
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_verify_token: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    # Cached so the .env file is parsed once per process (Singleton),
    # while tests can still override it through FastAPI dependency overrides.
    return Settings()
