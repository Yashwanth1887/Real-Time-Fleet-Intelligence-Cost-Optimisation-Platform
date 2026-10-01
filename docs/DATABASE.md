# FleetGuard relational schema

The PostgreSQL schema is defined by SQLAlchemy models in `backend/app/db/models.py` and managed with Alembic. IDs are UUIDs. Fleet-owned records carry a fleet foreign key to support tenant scoping at query boundaries.

```mermaid
erDiagram
  FLEETS ||--o{ USERS : contains
  FLEETS ||--o{ VEHICLES : owns
  FLEETS ||--o{ DRIVERS : employs
  VEHICLES ||--o{ VEHICLE_DRIVER_ASSIGNMENTS : assigned
  DRIVERS ||--o{ VEHICLE_DRIVER_ASSIGNMENTS : assigned
  VEHICLES ||--o{ TRIPS : performs
  DRIVERS o|--o{ TRIPS : drives
  VEHICLES ||--o{ TELEMETRY_SUMMARIES : summarized
  FLEETS ||--o{ ALERTS : receives
  VEHICLES ||--o{ ALERTS : triggers
  ALERTS o|--o{ RECOMMENDATIONS : suggests
  VEHICLES ||--o{ RECOMMENDATIONS : targets
  FLEETS ||--o{ COST_EVENTS : incurs
  VEHICLES ||--o{ COST_EVENTS : incurs
  FLEETS ||--o{ FLEET_METRICS : aggregates
  FLEETS ||--o{ AUDIT_LOGS : records
  USERS o|--o{ AUDIT_LOGS : performs
```

Indexes cover fleet ownership/status, vehicle trip chronology, alert/cost chronology, summary windows, metric windows, and driver assignment periods. Unique constraints prevent duplicate vehicle codes within a fleet, duplicate summary/metric windows, duplicate user emails, and duplicate cost event keys.

Raw high-volume telemetry is intentionally not stored in these relational tables; it belongs in the event and document storage layers planned separately.
