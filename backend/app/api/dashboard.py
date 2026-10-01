"""Fleet summary, live state, and historical analytics endpoints."""

from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from typing import Literal
from uuid import UUID
from uuid import UUID as UUIDType

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import get_principal, require_roles
from app.api.dependencies import get_db
from app.core.config import get_settings
from app.db.models import (
    Alert,
    AuditLog,
    CostEvent,
    Fleet,
    FleetMetric,
    Recommendation,
    TelemetrySummary,
    Vehicle,
)
from app.repositories.telemetry import TelemetryStore
from app.schemas.auth import Principal

router = APIRouter(tags=["dashboard", "analytics"], dependencies=[Depends(get_principal)])


@lru_cache
def _telemetry_store() -> TelemetryStore:
    settings = get_settings()
    return TelemetryStore(settings.mongo_url, settings.redis_url)


@router.get("/fleets")
def list_fleets(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    fleets = db.scalars(select(Fleet).where(Fleet.id == principal.fleet_id).order_by(Fleet.name)).all()
    return [{"id": str(row.id), "name": row.name, "timezone": row.timezone} for row in fleets]


@router.get("/fleets/{fleet_id}")
def get_fleet(fleet_id: UUID, principal: Principal = Depends(get_principal),
              db: Session = Depends(get_db)) -> dict[str, object]:
    if fleet_id != principal.fleet_id:
        raise HTTPException(404, "Fleet not found")
    fleet = db.get(Fleet, fleet_id)
    if fleet is None:
        raise HTTPException(404, "Fleet not found")
    return {"id": str(fleet.id), "name": fleet.name, "timezone": fleet.timezone}


@router.get("/vehicles")
def list_vehicles(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                  fleet_id: UUID | None = None, principal: Principal = Depends(get_principal),
                  db: Session = Depends(get_db)) -> dict[str, object]:
    if fleet_id is not None and fleet_id != principal.fleet_id:
        raise HTTPException(404, "Fleet not found")
    query = select(Vehicle).where(Vehicle.fleet_id == principal.fleet_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(Vehicle.vehicle_code).offset(offset).limit(limit)).all()
    return {"items": [_vehicle_dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}


def _vehicle_dict(row: Vehicle) -> dict[str, object]:
    return {"id": str(row.id), "vehicle_id": row.vehicle_code, "fleet_id": str(row.fleet_id),
            "make": row.make, "model": row.model, "status": row.status}


@router.get("/vehicles/{vehicle_id}")
def get_vehicle(vehicle_id: str, principal: Principal = Depends(get_principal),
                db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.scalar(select(Vehicle).where(Vehicle.vehicle_code == vehicle_id,
                                          Vehicle.fleet_id == principal.fleet_id))
    if row is None:
        raise HTTPException(404, "Vehicle not found")
    return _vehicle_dict(row)


@router.get("/vehicles/{vehicle_id}/telemetry")
def vehicle_telemetry(vehicle_id: str, limit: int = Query(50, ge=1, le=200),
                      principal: Principal = Depends(get_principal),
                      db: Session = Depends(get_db)) -> list[dict[str, object]]:
    try:
        exists = db.scalar(select(Vehicle.id).where(Vehicle.vehicle_code == vehicle_id,
                                                    Vehicle.fleet_id == principal.fleet_id))
        if exists is None:
            raise HTTPException(404, "Vehicle not found")
        records = _telemetry_store().collection.find({"vehicle_id": vehicle_id}, {"_id": 0}) \
            .sort("timestamp", -1).limit(limit)
        return list(records)
    except Exception as exc:
        raise HTTPException(503, "Telemetry storage is unavailable") from exc


@router.get("/vehicles/{vehicle_id}/alerts")
def vehicle_alerts(vehicle_id: str, limit: int = Query(50, ge=1, le=200),
                   principal: Principal = Depends(get_principal), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = db.scalars(select(Alert).join(Vehicle).where(Vehicle.vehicle_code == vehicle_id)
                      .where(Alert.fleet_id == principal.fleet_id)
                      .order_by(Alert.created_at.desc()).limit(limit)).all()
    return [_alert_dict(row, vehicle_id) for row in rows]


@router.get("/vehicles/{vehicle_id}/recommendations")
def vehicle_recommendations(vehicle_id: str, limit: int = Query(50, ge=1, le=200),
                            principal: Principal = Depends(get_principal),
                            db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = db.execute(select(Recommendation, Vehicle.vehicle_code, Alert.alert_type, Alert.severity)
                      .join(Vehicle, Recommendation.vehicle_id == Vehicle.id)
                      .outerjoin(Alert, Recommendation.alert_id == Alert.id)
                      .where(Vehicle.vehicle_code == vehicle_id)
                      .where(Vehicle.fleet_id == principal.fleet_id)
                      .order_by(Recommendation.created_at.desc()).limit(limit)).all()
    return [_recommendation_dict(row, code, alert_type, severity) for row, code, alert_type, severity in rows]


@router.get("/dashboard/summary")
def dashboard_summary(principal: Principal = Depends(get_principal),
                      db: Session = Depends(get_db)) -> dict[str, object]:
    fleet_id = principal.fleet_id
    vehicle_count = db.scalar(select(func.count(Vehicle.id)).where(Vehicle.fleet_id == fleet_id)) or 0
    active_count = db.scalar(select(func.count(Vehicle.id)).where(Vehicle.fleet_id == fleet_id, Vehicle.status == "active")) or 0
    alert_count = db.scalar(select(func.count(Alert.id)).where(Alert.fleet_id == fleet_id, Alert.status == "open")) or 0
    idle_cost = db.scalar(select(func.coalesce(func.sum(CostEvent.amount), 0)).where(CostEvent.fleet_id == fleet_id)) or 0
    savings = db.scalar(select(func.coalesce(func.sum(Recommendation.potential_savings), 0))
                         .join(Vehicle).where(Vehicle.fleet_id == fleet_id)) or 0
    efficiency = _efficiency_score(db, fleet_id)
    return {"vehicle_count": vehicle_count, "active_vehicle_count": active_count,
            "open_alert_count": alert_count, "idle_cost_usd": round(float(idle_cost), 2),
            "potential_savings_usd": round(float(savings), 2), "fleet_efficiency_score": efficiency,
            "currency": "USD", "as_of": datetime.now(timezone.utc).isoformat()}


@router.get("/dashboard/live")
def dashboard_live(limit: int = Query(30, ge=1, le=100), principal: Principal = Depends(get_principal),
                   db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        store = _telemetry_store()
        vehicle_codes = db.scalars(select(Vehicle.vehicle_code).where(Vehicle.fleet_id == principal.fleet_id)
                                    .limit(500)).all()
        states = []
        for vehicle_code in vehicle_codes:
            key = f"vehicle:{vehicle_code}"
            state = store.redis.hgetall(key)
            if state:
                states.append({"vehicle_id": vehicle_code, **state})
            if len(states) >= limit:
                break
        return {"items": states, "limit": limit}
    except Exception as exc:
        raise HTTPException(503, "Live state storage is unavailable") from exc


@router.get("/analytics/cost")
def cost_analytics(days: int = Query(30, ge=1, le=365), principal: Principal = Depends(get_principal),
                   db: Session = Depends(get_db)) -> dict[str, object]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(select(CostEvent.category, func.sum(CostEvent.amount))
                      .where(CostEvent.fleet_id == principal.fleet_id, CostEvent.created_at >= start)
                      .group_by(CostEvent.category)).all()
    return {"days": days, "currency": "USD", "items": [
        {"category": category, "cost_usd": round(float(amount), 2)} for category, amount in rows
    ]}


@router.get("/analytics/idle")
def idle_analytics(days: int = Query(30, ge=1, le=365), principal: Principal = Depends(get_principal),
                   db: Session = Depends(get_db)) -> list[dict[str, object]]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(select(func.date_trunc("day", Alert.created_at), func.count(Alert.id))
                      .where(Alert.fleet_id == principal.fleet_id, Alert.alert_type == "excessive_idling",
                             Alert.created_at >= start)
                      .group_by(func.date_trunc("day", Alert.created_at))
                      .order_by(func.date_trunc("day", Alert.created_at))).all()
    return [{"day": day.isoformat(), "idle_alerts": count} for day, count in rows]


@router.get("/analytics/utilisation")
def utilisation_analytics(principal: Principal = Depends(get_principal),
                           db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.execute(select(func.coalesce(func.sum(TelemetrySummary.distance_km), 0),
                            func.coalesce(func.sum(TelemetrySummary.idle_minutes), 0),
                            func.coalesce(func.sum(TelemetrySummary.event_count), 0))
                      .join(Vehicle, Vehicle.id == TelemetrySummary.vehicle_id)
                      .where(Vehicle.fleet_id == principal.fleet_id)).one()
    distance, idle_minutes, events = row
    return {"distance_km": round(float(distance), 2), "idle_minutes": round(float(idle_minutes), 2),
            "event_count": int(events), "utilisation_ratio": None,
            "note": "Utilisation ratio requires scheduled availability; it is not inferred without that input."}


@router.get("/analytics/savings")
def savings_analytics(principal: Principal = Depends(get_principal),
                      db: Session = Depends(get_db)) -> dict[str, object]:
    value = db.scalar(select(func.coalesce(func.sum(Recommendation.potential_savings), 0))
                      .join(Vehicle).where(Vehicle.fleet_id == principal.fleet_id)) or 0
    return {"currency": "USD", "potential_savings_usd": round(float(value), 2),
            "assumption": "75% of the estimated idle fuel cost is avoidable when the recommended behavior changes."}


@router.get("/analytics/daily")
def daily_analytics(days: int = Query(30, ge=1, le=365), principal: Principal = Depends(get_principal),
                    db: Session = Depends(get_db)) -> list[dict[str, object]]:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
    rows = db.scalars(select(FleetMetric).where(FleetMetric.fleet_id == principal.fleet_id,
                                                FleetMetric.window_start >= start)
                      .order_by(FleetMetric.window_start.desc(), FleetMetric.metric_name)).all()
    return [{"fleet_id": str(row.fleet_id), "metric": row.metric_name,
             "value": row.metric_value, "window_start": row.window_start.isoformat()} for row in rows]


@router.get("/alerts")
def list_alerts(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
               severity: str | None = None, alert_type: str | None = None,
               start: date | None = None, end: date | None = None,
               principal: Principal = Depends(get_principal),
               db: Session = Depends(get_db)) -> dict[str, object]:
    query = select(Alert, Vehicle.vehicle_code).join(Vehicle).where(Alert.fleet_id == principal.fleet_id)
    if severity:
        query = query.where(Alert.severity == severity)
    if alert_type:
        query = query.where(Alert.alert_type == alert_type)
    if start:
        query = query.where(Alert.created_at >= datetime.combine(start, time.min, timezone.utc))
    if end:
        query = query.where(Alert.created_at < datetime.combine(end + timedelta(days=1), time.min, timezone.utc))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.order_by(Alert.created_at.desc()).offset(offset).limit(limit)).all()
    return {"items": [_alert_dict(row, code) for row, code in rows], "total": total,
            "limit": limit, "offset": offset}


@router.patch("/alerts/{alert_id}/status")
def update_alert_status(alert_id: UUID, status: Literal["open", "resolved"],
                        principal: Principal = Depends(require_roles("ADMIN", "FLEET_MANAGER")),
                        db: Session = Depends(get_db)) -> dict[str, str]:
    alert = db.scalar(select(Alert).where(Alert.id == alert_id, Alert.fleet_id == principal.fleet_id))
    if alert is None:
        raise HTTPException(404, "Alert not found")
    alert.status = status
    db.add(AuditLog(fleet_id=principal.fleet_id, user_id=UUID(principal.user_id),
                    action=f"alert_status:{status}", entity_type="alert",
                    entity_id=str(alert.id), succeeded=True))
    db.commit()
    return {"id": str(alert.id), "status": alert.status}


def _alert_dict(row: Alert, vehicle_code: str) -> dict[str, object]:
    return {"id": str(row.id), "vehicle_id": vehicle_code, "alert_type": row.alert_type,
            "severity": row.severity, "description": row.description, "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None}


@router.get("/recommendations")
def list_recommendations(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                         principal: Principal = Depends(get_principal),
                         db: Session = Depends(get_db)) -> dict[str, object]:
    query = select(Recommendation, Vehicle.vehicle_code, Alert.alert_type, Alert.severity) \
        .join(Vehicle, Recommendation.vehicle_id == Vehicle.id) \
        .outerjoin(Alert, Recommendation.alert_id == Alert.id).where(Vehicle.fleet_id == principal.fleet_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.order_by(Recommendation.created_at.desc()).offset(offset).limit(limit)).all()
    return {"items": [_recommendation_dict(row, code, alert_type, severity) for row, code, alert_type, severity in rows],
            "total": total, "limit": limit, "offset": offset}


@router.patch("/recommendations/{recommendation_id}/status")
def update_recommendation_status(recommendation_id: UUID, status: Literal["open", "completed", "dismissed"],
                                 principal: Principal = Depends(require_roles("ADMIN", "FLEET_MANAGER")),
                                 db: Session = Depends(get_db)) -> dict[str, str]:
    recommendation = db.scalar(select(Recommendation).join(Vehicle, Recommendation.vehicle_id == Vehicle.id).where(
        Recommendation.id == recommendation_id, Vehicle.fleet_id == principal.fleet_id))
    if recommendation is None:
        raise HTTPException(404, "Recommendation not found")
    recommendation.status = status
    db.add(AuditLog(fleet_id=principal.fleet_id, user_id=UUID(principal.user_id),
                    action=f"recommendation_status:{status}", entity_type="recommendation",
                    entity_id=str(recommendation.id), succeeded=True))
    db.commit()
    return {"id": str(recommendation.id), "status": recommendation.status}


def _recommendation_dict(row: Recommendation, vehicle_code: str, alert_type: str | None,
                         severity: str | None) -> dict[str, object]:
    return {"id": str(row.id), "vehicle_id": vehicle_code,
            "reason": alert_type.replace("_", " ").capitalize() if alert_type else "Fleet recommendation",
            "recommended_action": row.action, "estimated_savings_usd": row.potential_savings,
            "priority": severity or "medium", "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None}


def _efficiency_score(db: Session, fleet_id: UUIDType) -> int | None:
    summary_scope = select(TelemetrySummary).join(Vehicle, Vehicle.id == TelemetrySummary.vehicle_id) \
        .where(Vehicle.fleet_id == fleet_id).subquery()
    event_count = db.scalar(select(func.coalesce(func.sum(summary_scope.c.event_count), 0))) or 0
    if not event_count:
        return None
    idle = db.scalar(select(func.coalesce(func.sum(summary_scope.c.idle_minutes), 0))) or 0
    harsh = db.scalar(select(func.count(Alert.id)).where(
        Alert.fleet_id == fleet_id, Alert.alert_type.in_(["harsh_acceleration", "harsh_braking"]))) or 0
    distance_km = db.scalar(select(func.coalesce(func.sum(summary_scope.c.distance_km), 0))) or 0
    # A documented 30 km/h baseline converts distance to estimated moving time.
    moving_minutes = float(distance_km) / 30.0 * 60.0
    idle_score = 100.0 if idle + moving_minutes <= 0 else max(
        0.0, 100.0 * (1 - float(idle) / (float(idle) + moving_minutes))
    )
    behavior_score = max(0.0, 100.0 * (1 - float(harsh) / float(event_count)))
    return round(0.7 * idle_score + 0.3 * behavior_score)
