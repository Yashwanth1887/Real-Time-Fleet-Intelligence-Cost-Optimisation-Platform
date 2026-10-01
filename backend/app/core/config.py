"""Environment-backed application settings."""

from decimal import Decimal
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FleetGuard API"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", validation_alias="APP_ENV")
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://fleetguard:fleetguard@localhost:5432/fleetguard"
    mongo_url: str = "mongodb://fleetguard:fleetguard@localhost:27017/?authSource=admin"
    redis_url: str = "redis://:fleetguard@localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:19092"
    idle_threshold_seconds: int = Field(default=120, gt=0)
    fuel_price_per_litre: Decimal = Field(default=Decimal("1.50"), gt=0)
    savings_assumption: Decimal = Field(default=Decimal("0.75"), ge=0, le=1)
    jwt_secret_key: str | None = Field(default=None, min_length=32)
    cors_origins: str = "http://localhost:4173,http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
