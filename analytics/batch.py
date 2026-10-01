"""Materialize daily fleet cost and operational metrics into PostgreSQL."""

import argparse
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select

from backend.app.db.models import (
    Alert,
    CostEvent,
    FleetMetric,
    Recommendation,
    TelemetrySummary,
    Vehicle,
)
from backend.app.db.session import SessionLocal


def materialize(day: date) -> int:
    start = datetime.combine(day, time.min, timezone.utc)
    end = start + timedelta(days=1)
    values_by_fleet: dict[object, dict[str, float]] = {}
    with SessionLocal() as session:
        fleet_ids = session.scalars(select(Vehicle.fleet_id).distinct()).all()
        for fleet_id in fleet_ids:
            values = {"daily_cost_usd": 0.0, "daily_potential_savings_usd": 0.0,
                      "idle_alert_count": 0.0, "harsh_event_count": 0.0,
                      "daily_distance_km": 0.0, "daily_idle_minutes": 0.0}
            values["daily_cost_usd"] = float(session.scalar(select(func.coalesce(func.sum(CostEvent.amount), 0))
                .where(CostEvent.fleet_id == fleet_id, CostEvent.created_at >= start, CostEvent.created_at < end)) or 0)
            values["daily_potential_savings_usd"] = float(session.scalar(
                select(func.coalesce(func.sum(Recommendation.potential_savings), 0))
                .join(Vehicle, Vehicle.id == Recommendation.vehicle_id)
                .where(Vehicle.fleet_id == fleet_id, Recommendation.created_at >= start,
                       Recommendation.created_at < end)) or 0)
            values["idle_alert_count"] = float(session.scalar(select(func.count(Alert.id))
                .where(Alert.fleet_id == fleet_id, Alert.alert_type == "excessive_idling",
                       Alert.created_at >= start, Alert.created_at < end)) or 0)
            values["harsh_event_count"] = float(session.scalar(select(func.count(Alert.id))
                .where(Alert.fleet_id == fleet_id, Alert.alert_type.in_(["harsh_acceleration", "harsh_braking"]),
                       Alert.created_at >= start, Alert.created_at < end)) or 0)
            values["daily_distance_km"] = float(session.scalar(
                select(func.coalesce(func.sum(TelemetrySummary.distance_km), 0))
                .join(Vehicle, Vehicle.id == TelemetrySummary.vehicle_id)
                .where(Vehicle.fleet_id == fleet_id, TelemetrySummary.window_start >= start,
                       TelemetrySummary.window_start < end)) or 0)
            values["daily_idle_minutes"] = float(session.scalar(
                select(func.coalesce(func.sum(TelemetrySummary.idle_minutes), 0))
                .join(Vehicle, Vehicle.id == TelemetrySummary.vehicle_id)
                .where(Vehicle.fleet_id == fleet_id, TelemetrySummary.window_start >= start,
                       TelemetrySummary.window_start < end)) or 0)
            values_by_fleet[fleet_id] = values

        written = 0
        for fleet_id, values in values_by_fleet.items():
            for name, value in values.items():
                metric = session.scalar(select(FleetMetric).where(
                    FleetMetric.fleet_id == fleet_id,
                    FleetMetric.metric_name == name,
                    FleetMetric.window_start == start,
                ))
                if metric is None:
                    session.add(FleetMetric(fleet_id=fleet_id, metric_name=name,
                                            metric_value=value, window_start=start))
                else:
                    metric.metric_value = value
                written += 1
        session.commit()
        return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    args = parser.parse_args()
    print(f"Materialized {materialize(args.date)} daily fleet metrics for {args.date.isoformat()}")


if __name__ == "__main__":
    main()
