"""Normalized FleetGuard relational entities."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IdMixin:
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Fleet(IdMixin, Base):
    __tablename__ = "fleets"
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)


class User(IdMixin, Base):
    __tablename__ = "users"
    fleet_id: Mapped[UUID] = mapped_column(ForeignKey("fleets.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="viewer", nullable=False)


class Vehicle(IdMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (UniqueConstraint("fleet_id", "vehicle_code"), Index("ix_vehicles_fleet_status", "fleet_id", "status"))
    fleet_id: Mapped[UUID] = mapped_column(ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False)
    vehicle_code: Mapped[str] = mapped_column(String(32), nullable=False)
    make: Mapped[str] = mapped_column(String(60), default="Synthetic", nullable=False)
    model: Mapped[str] = mapped_column(String(60), default="Fleet Vehicle", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)


class Driver(IdMixin, Base):
    __tablename__ = "drivers"
    fleet_id: Mapped[UUID] = mapped_column(ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False, index=True)
    driver_code: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)


class VehicleDriverAssignment(IdMixin, Base):
    __tablename__ = "vehicle_driver_assignments"
    __table_args__ = (Index("ix_assignment_vehicle_period", "vehicle_id", "started_at", "ended_at"),)
    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    driver_id: Mapped[UUID] = mapped_column(ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Trip(IdMixin, Base):
    __tablename__ = "trips"
    __table_args__ = (Index("ix_trips_vehicle_started", "vehicle_id", "started_at"),)
    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    driver_id: Mapped[UUID | None] = mapped_column(ForeignKey("drivers.id", ondelete="SET NULL"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_km: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    fuel_litres: Mapped[float] = mapped_column(Float, default=0, nullable=False)


class TelemetrySummary(IdMixin, Base):
    __tablename__ = "telemetry_summaries"
    __table_args__ = (UniqueConstraint("vehicle_id", "window_start"), Index("ix_summary_window", "window_start"))
    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    idle_minutes: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    fuel_litres: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Alert(IdMixin, Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_fleet_created", "fleet_id", "created_at"),)
    event_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    fleet_id: Mapped[UUID] = mapped_column(ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False)
    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)


class Recommendation(IdMixin, Base):
    __tablename__ = "recommendations"
    alert_id: Mapped[UUID | None] = mapped_column(ForeignKey("alerts.id", ondelete="SET NULL"))
    event_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    potential_savings: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)


class CostEvent(IdMixin, Base):
    __tablename__ = "cost_events"
    __table_args__ = (Index("ix_cost_events_fleet_created", "fleet_id", "created_at"),)
    fleet_id: Mapped[UUID] = mapped_column(ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False)
    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    event_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    calculation: Mapped[str] = mapped_column(Text, nullable=False)


class FleetMetric(IdMixin, Base):
    __tablename__ = "fleet_metrics"
    __table_args__ = (UniqueConstraint("fleet_id", "metric_name", "window_start"), Index("ix_metrics_window", "window_start"))
    fleet_id: Mapped[UUID] = mapped_column(ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(60), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLog(IdMixin, Base):
    __tablename__ = "audit_logs"
    fleet_id: Mapped[UUID] = mapped_column(ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    succeeded: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
