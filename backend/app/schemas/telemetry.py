"""Synthetic connected vehicle telemetry contract."""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    vehicle_id: str = Field(pattern=r"^FG-[0-9]{9}$")
    timestamp: datetime
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed_kph: float = Field(ge=0, le=250)
    engine_on: bool
    engine_rpm: int = Field(ge=0, le=12000)
    fuel_level_litres: float = Field(ge=0, le=2000)
    fuel_rate_lph: float = Field(ge=0, le=150)
    odometer_km: float = Field(ge=0)
    harsh_acceleration: bool = False
    harsh_braking: bool = False
    battery_voltage: float = Field(ge=0, le=100)
    ambient_temperature_c: float = Field(ge=-80, le=80)
    trip_id: UUID | None = None
    sequence_number: int = Field(ge=0)

    @field_validator("timestamp", "ingestion_timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone")
        return value
