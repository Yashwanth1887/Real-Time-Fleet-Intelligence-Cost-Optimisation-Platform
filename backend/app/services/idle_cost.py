"""Explainable idle-event detection and fuel-cost calculations."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from app.db.models import Alert, CostEvent, Fleet, Recommendation, Vehicle
from app.db.session import SessionLocal
from app.schemas.telemetry import TelemetryEvent

CENT = Decimal("0.01")


@dataclass(frozen=True)
class IdleCost:
    duration_seconds: int
    fuel_wasted_litres: Decimal
    cost: Decimal
    calculation: str


def calculate_idle_cost(duration_seconds: int, fuel_rate_lph: float,
                        fuel_price_per_litre: Decimal = Decimal("1.50")) -> IdleCost:
    if duration_seconds < 0 or fuel_rate_lph < 0 or fuel_price_per_litre < 0:
        raise ValueError("duration, fuel rate, and fuel price must be non-negative")
    hours = Decimal(duration_seconds) / Decimal(3600)
    fuel = (Decimal(str(fuel_rate_lph)) * hours).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    cost = (fuel * fuel_price_per_litre).quantize(CENT, rounding=ROUND_HALF_UP)
    calculation = (
        f"{fuel_rate_lph:.2f} L/h × {duration_seconds} s ÷ 3600 × "
        f"${fuel_price_per_litre}/L = ${cost:.2f}"
    )
    return IdleCost(duration_seconds, fuel, cost, calculation)


def persist_idle_impact(event: TelemetryEvent, impact: IdleCost,
                        savings_assumption: Decimal = Decimal("0.75")) -> dict[str, object]:
    """Persist one idempotent alert, cost event, and recommendation per idle episode."""
    episode_start = int(event.timestamp.timestamp()) - impact.duration_seconds
    event_key = f"idle:{event.vehicle_id}:{episode_start}"
    fleet_id = uuid5(NAMESPACE_URL, "fleetguard/fleet/synthetic-demo")
    vehicle_id = uuid5(NAMESPACE_URL, f"fleetguard/vehicle/{event.vehicle_id}")
    alert_id = uuid5(NAMESPACE_URL, f"fleetguard/alert/{event_key}")
    cost_id = uuid5(NAMESPACE_URL, f"fleetguard/cost/{event_key}")
    recommendation_id = uuid5(NAMESPACE_URL, f"fleetguard/recommendation/{event_key}")

    with SessionLocal() as session:
        fleet = session.get(Fleet, fleet_id)
        if fleet is None:
            fleet = Fleet(id=fleet_id, name="Synthetic demo fleet", timezone="UTC")
            session.add(fleet)
            session.flush()
        vehicle = session.get(Vehicle, vehicle_id)
        if vehicle is None:
            session.add(Vehicle(id=vehicle_id, fleet_id=fleet_id, vehicle_code=event.vehicle_id,
                                make="Synthetic", model="Fleet Vehicle", status="active"))
            session.flush()

        alert = session.scalar(select(Alert).where(Alert.event_key == event_key))
        if alert is None:
            alert = Alert(id=alert_id, fleet_id=fleet_id, vehicle_id=vehicle_id,
                          event_key=event_key, alert_type="excessive_idling", severity="medium",
                          description=(f"{event.vehicle_id} idled for {impact.duration_seconds} seconds; "
                                       f"estimated {impact.fuel_wasted_litres} L fuel waste."))
            session.add(alert)
            session.flush()
        cost = session.scalar(select(CostEvent).where(CostEvent.event_key == event_key))
        if cost is None:
            session.add(CostEvent(id=cost_id, fleet_id=fleet_id, vehicle_id=vehicle_id,
                                  event_key=event_key, category="idle_fuel_waste", amount=float(impact.cost),
                                  currency="USD", calculation=impact.calculation))
        recommendation = session.scalar(select(Recommendation).where(Recommendation.event_key == event_key))
        if recommendation is None:
            savings = (impact.cost * savings_assumption).quantize(CENT, rounding=ROUND_HALF_UP)
            session.add(Recommendation(id=recommendation_id, alert_id=alert.id, vehicle_id=vehicle_id,
                                       event_key=event_key,
                                       action="Coach the driver to switch off the engine during extended stops; "
                                              "review recurring idle locations.",
                                       potential_savings=float(savings), status="open"))
        session.commit()
        savings = (impact.cost * savings_assumption).quantize(CENT, rounding=ROUND_HALF_UP)
        return {
            "event_key": event_key,
            "vehicle_id": event.vehicle_id,
            "alert_id": str(alert.id),
            "alert_type": "excessive_idling",
            "duration_seconds": impact.duration_seconds,
            "fuel_wasted_litres": str(impact.fuel_wasted_litres),
            "cost_usd": str(impact.cost),
            "potential_savings_usd": str(savings),
            "calculation": impact.calculation,
            "recommendation": "Switch off the engine during extended stops; review recurring idle locations.",
        }


def persist_behavior_alert(event: TelemetryEvent, behavior: str) -> dict[str, object]:
    """Persist a deterministic coaching alert for a harsh driving event."""
    if behavior not in {"harsh_acceleration", "harsh_braking"}:
        raise ValueError("unsupported behavior alert")
    event_key = f"behavior:{event.vehicle_id}:{event.event_id}:{behavior}"
    fleet_id = uuid5(NAMESPACE_URL, "fleetguard/fleet/synthetic-demo")
    vehicle_id = uuid5(NAMESPACE_URL, f"fleetguard/vehicle/{event.vehicle_id}")
    alert_id = uuid5(NAMESPACE_URL, f"fleetguard/alert/{event_key}")
    recommendation_id = uuid5(NAMESPACE_URL, f"fleetguard/recommendation/{event_key}")
    action = ("Review the telematics context and coach for smoother acceleration."
              if behavior == "harsh_acceleration" else
              "Review route conditions and coach for greater following distance and smoother braking.")
    with SessionLocal() as session:
        if session.get(Fleet, fleet_id) is None:
            session.add(Fleet(id=fleet_id, name="Synthetic demo fleet", timezone="UTC"))
            session.flush()
        if session.get(Vehicle, vehicle_id) is None:
            session.add(Vehicle(id=vehicle_id, fleet_id=fleet_id, vehicle_code=event.vehicle_id,
                                make="Synthetic", model="Fleet Vehicle", status="active"))
            session.flush()
        alert = session.scalar(select(Alert).where(Alert.event_key == event_key))
        if alert is None:
            alert = Alert(id=alert_id, fleet_id=fleet_id, vehicle_id=vehicle_id,
                          event_key=event_key, alert_type=behavior,
                          severity="high" if behavior == "harsh_braking" else "medium",
                          description=f"Synthetic telemetry flagged {behavior.replace('_', ' ')}.")
            session.add(alert)
            session.flush()
        if session.scalar(select(Recommendation).where(Recommendation.event_key == event_key)) is None:
            session.add(Recommendation(id=recommendation_id, alert_id=alert.id, vehicle_id=vehicle_id,
                                       event_key=event_key, action=action, potential_savings=0, status="open"))
        session.commit()
    return {"event_key": event_key, "vehicle_id": event.vehicle_id, "alert_type": behavior,
            "severity": "high" if behavior == "harsh_braking" else "medium", "recommendation": action}
