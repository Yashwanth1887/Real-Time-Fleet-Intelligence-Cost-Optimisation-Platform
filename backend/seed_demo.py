"""Create an idempotent synthetic dashboard dataset and demo manager."""

import os
from datetime import datetime, time, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from app.core.config import get_settings
from app.db.models import (
    Alert,
    CostEvent,
    Driver,
    Fleet,
    FleetMetric,
    Recommendation,
    TelemetrySummary,
    Trip,
    User,
    Vehicle,
    VehicleDriverAssignment,
)
from app.db.session import SessionLocal
from app.repositories.telemetry import TelemetryStore
from app.schemas.telemetry import TelemetryEvent
from app.security.auth import hash_password
from sqlalchemy import select

FLEET_ID = uuid5(NAMESPACE_URL, "fleetguard/fleet/synthetic-demo")


def main() -> None:
    email = os.environ.get("DEMO_ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("DEMO_ADMIN_PASSWORD", "")
    if not email or not password:
        raise SystemExit("Set DEMO_ADMIN_EMAIL and DEMO_ADMIN_PASSWORD before running this script.")
    now = datetime.now(timezone.utc)
    day = datetime.combine(now.date(), time.min, timezone.utc)
    codes = [f"FG-{900000001 + i:09d}" for i in range(8)]
    with SessionLocal() as session:
        fleet = session.get(Fleet, FLEET_ID)
        if fleet is None:
            session.add(Fleet(id=FLEET_ID, name="Synthetic demo fleet", timezone="UTC"))
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            session.add(User(fleet_id=FLEET_ID, email=email, password_hash=hash_password(password), role="FLEET_MANAGER"))
        else:
            user.password_hash, user.role, user.fleet_id = hash_password(password), "FLEET_MANAGER", FLEET_ID
        vehicles = {}
        for i, code in enumerate(codes):
            vehicle_id = uuid5(NAMESPACE_URL, f"fleetguard/vehicle/{code}")
            vehicle = session.get(Vehicle, vehicle_id)
            if vehicle is None:
                vehicle = Vehicle(id=vehicle_id, fleet_id=FLEET_ID, vehicle_code=code,
                                  make="Synthetic", model=("Cargo Van" if i % 2 == 0 else "Service Truck"), status="active")
                session.add(vehicle)
            vehicles[code] = vehicle
        drivers = []
        for i in range(2):
            driver_id = uuid5(NAMESPACE_URL, f"fleetguard/demo-driver/{i+1}")
            driver = session.get(Driver, driver_id)
            if driver is None:
                driver = Driver(id=driver_id, fleet_id=FLEET_ID, driver_code=f"SYN-{i+1:03d}",
                                display_name=f"Synthetic Driver {i+1:02d}")
                session.add(driver)
            drivers.append(driver)
        session.flush()
        for i, code in enumerate(codes):
            vehicle = vehicles[code]
            driver = drivers[i % len(drivers)]
            assignment_id = uuid5(NAMESPACE_URL, f"fleetguard/demo-assignment/{code}")
            if session.get(VehicleDriverAssignment, assignment_id) is None:
                session.add(VehicleDriverAssignment(id=assignment_id, vehicle_id=vehicle.id,
                    driver_id=driver.id, started_at=day))
            trip_id = uuid5(NAMESPACE_URL, f"fleetguard/demo-trip/{code}/{now.date().isoformat()}")
            if session.get(Trip, trip_id) is None:
                session.add(Trip(id=trip_id, vehicle_id=vehicle.id, driver_id=driver.id,
                    started_at=now - timedelta(hours=2+i), ended_at=now - timedelta(hours=1+i),
                    distance_km=20.0 + i*7, fuel_litres=2.5 + i*.4))
            summary = session.scalar(select(TelemetrySummary).where(
                TelemetrySummary.vehicle_id == vehicle.id, TelemetrySummary.window_start == day))
            if summary is None:
                session.add(TelemetrySummary(vehicle_id=vehicle.id, window_start=day,
                    distance_km=20.0+i*7, idle_minutes=15.0 if i == 1 else float(i*2),
                    fuel_litres=2.5+i*.4, event_count=12+i*3))
        # Two transparent sample findings, with stable event keys for reruns.
        for index, (kind, severity, desc, code) in enumerate([
            ("excessive_idling", "high", "Synthetic 15-minute idle episode; estimated fuel waste 0.800 L ($1.20).", codes[1]),
            ("harsh_braking", "medium", "Synthetic harsh-braking event; review following distance and braking pattern.", codes[3]),
        ]):
            event_key = f"demo:{kind}:v1"
            alert = session.scalar(select(Alert).where(Alert.event_key == event_key))
            if alert is None:
                alert = Alert(event_key=event_key, fleet_id=FLEET_ID, vehicle_id=vehicles[code].id,
                    alert_type=kind, severity=severity, description=desc, status="open")
                session.add(alert)
                session.flush()
            if kind == "excessive_idling":
                if session.scalar(select(CostEvent).where(CostEvent.event_key == event_key)) is None:
                    session.add(CostEvent(fleet_id=FLEET_ID, vehicle_id=vehicles[code].id,
                        event_key=event_key, category="idle_fuel", amount=1.20, currency="USD",
                        calculation="3.2 L/h × 900 s ÷ 3600 × $1.50/L = 0.800 L × $1.50/L = $1.20"))
            rec_key = f"{event_key}:recommendation"
            if session.scalar(select(Recommendation).where(Recommendation.event_key == rec_key)) is None:
                session.add(Recommendation(alert_id=alert.id, event_key=rec_key,
                    vehicle_id=vehicles[code].id,
                    action=("Coach the operator to switch off the engine during extended stops." if kind == "excessive_idling"
                            else "Review the synthetic braking event and reinforce safe following distance."),
                    potential_savings=.90 if kind == "excessive_idling" else 0.0, status="open"))
        for name, value in (("distance_km", 188.0), ("idle_minutes", 29.0), ("fuel_litres", 31.6)):
            metric = session.scalar(select(FleetMetric).where(FleetMetric.fleet_id == FLEET_ID,
                FleetMetric.metric_name == name, FleetMetric.window_start == day))
            if metric is None:
                session.add(FleetMetric(fleet_id=FLEET_ID, metric_name=name, metric_value=value, window_start=day))
        session.commit()

    settings = get_settings()
    store = TelemetryStore(settings.mongo_url, settings.redis_url)
    try:
        for i, code in enumerate(codes):
            event = TelemetryEvent(event_id=uuid5(NAMESPACE_URL, f"fleetguard/demo-live/{code}/{now.date()}"),
                vehicle_id=code, timestamp=now-timedelta(seconds=i), latitude=37.7+i*.03,
                longitude=-122.4+i*.04, speed_kph=(0 if i == 1 else 24.0+i*5), engine_on=True,
                engine_rpm=(800 if i == 1 else 1300+i*100), fuel_level_litres=82.0-i*4,
                fuel_rate_lph=(2.4 if i == 1 else 4.5+i*.4), odometer_km=12000.0+i*360,
                harsh_braking=(i == 3), battery_voltage=13.8, ambient_temperature_c=20.0,
                trip_id=uuid5(NAMESPACE_URL, f"fleetguard/demo-trip/{code}/{now.date().isoformat()}"), sequence_number=100+i)
            store.persist(event.model_dump(mode="json"))
    finally:
        store.close()
    print(f"Synthetic demo data ready: {email}; {len(codes)} vehicles, 2 sample alerts, 1 cost event.")


if __name__ == "__main__":
    main()
