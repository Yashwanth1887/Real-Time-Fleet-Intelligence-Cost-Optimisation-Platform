# FleetGuard — Real-Time Fleet Intelligence & Cost Optimisation Platform

**Hackathon solution document**  
**Submission date:** 1 October 2026  
**Project repository:** [github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform)

## 1. Executive summary

FleetGuard is a local connected-vehicle intelligence demo focused on idle fuel waste. It converts synthetic telemetry into an operational explanation: detect an engine-on stationary episode, estimate fuel and currency cost, raise an alert, and recommend an action. A fleet manager can follow the result through authenticated APIs and a React dashboard.

The verified vertical slice runs with Kafka, MongoDB, Redis, PostgreSQL, FastAPI, and React. This is a demo implementation, not a deployed fleet service. Every vehicle and driver-like label in the demonstration is synthetic.

## 2. Problem statement and validation

Fuel use, idling, and vehicle utilisation affect fleet operating costs. Fleet managers need signals that connect observed behaviour to financial impact and a practical intervention. FleetGuard demonstrates the `WHY → COST → ACTION` product hypothesis.

No customer interviews, fleet-data study, or quantified market validation was performed. The problem framing is a product hypothesis for this hackathon, not a claim based on user research or customer results.

## 3. Solution description

The simulator emits validated synthetic vehicle events to Kafka. A consumer validates each event, stores raw telemetry, updates current vehicle state, applies deterministic rules, and records any alert, estimated cost, and recommendation. The dashboard reads fleet-scoped APIs and explains the cost assumptions.

For an idle event, the cost rule uses reported fuel rate, idle duration, and a configurable fuel price. The recommendation shows an explicitly assumed avoidable fraction. It does not predict an invoice or claim realized savings.

## 4. Feature list and implementation status

| Capability | Status |
| --- | --- |
| Synthetic telemetry schema and simulator, duplicate and out-of-order modes | Implemented; ID-pool option reaches 100,000 identifiers, but does not provision a fleet |
| Kafka event stream and consumer | Implemented for single-broker local Compose |
| Raw telemetry in MongoDB and current state in Redis | Implemented and integration-tested |
| Excessive-idle detection, cost estimate, alert, and recommendation | Implemented and exercised end to end |
| Harsh-braking and harsh-acceleration coaching alerts | Implemented; synthetic batch run generated behaviour alerts |
| Low-utilisation detection | Not implemented; scheduled availability and reliable trip baselines are absent |
| PostgreSQL schema and Alembic migrations | Implemented and applied in the local stack |
| JWT login, fleet-scoped API reads, role-gated actions, audit records | Implemented; API, integration, and browser login checks passed |
| React dashboard | Implemented; production build and authenticated browser views passed |
| Live updates | Implemented as bounded API snapshots polled every five seconds; no WebSocket/SSE stream |
| Daily batch analytics | Job and APIs implemented; current-day analytics APIs returned rows |
| Vector search and AI/ML | Not used; current explanations are deterministic and no semantic corpus or validated model exists |
| 100K active vehicles, 100K events/sec, 3× five-minute burst | Targets only; not demonstrated |

## 5. Solution architecture

```text
Synthetic simulator → Kafka topic → Telemetry worker
                                  ├─ MongoDB: raw event history
                                  ├─ Redis: latest state and idle episode
                                  └─ PostgreSQL: fleet records, alerts, costs, actions, metrics
                                              ↓
                                  FastAPI (JWT and fleet scope)
                                              ↓
                                  React dashboard (5-second polling)
```

Kafka buffers the telemetry stream between producer and consumer. PostgreSQL owns relational fleet and workflow records. MongoDB stores raw event documents by event ID. Redis holds expiring hot state and tracks idle episodes atomically. FastAPI serves the authenticated API; the browser dashboard requests bounded snapshots. More detailed diagrams and service rationale are in [the architecture notes](architecture/README.md).

## 6. Low-level design

- **Telemetry contract:** event and vehicle IDs, event and ingestion timestamps, coordinates, speed, engine state/RPM, fuel level/rate, odometer, battery, temperature, trip ID, and sequence number.
- **Validation:** Pydantic rejects unknown fields, invalid synthetic IDs, out-of-range values, and timezone-naive timestamps.
- **Event processing:** the Kafka consumer disables automatic commits. For valid telemetry, it persists raw state and derived intelligence before synchronously committing the message offset. Persistence exceptions leave the offset uncommitted.
- **Idempotency:** MongoDB uses the event UUID as `_id`. PostgreSQL alert, cost, and recommendation event keys prevent duplicate rule outputs.
- **Hot state:** Redis Lua scripts compare event timestamps, retain the newest vehicle state, track idle duration, and acknowledge one alert per idle episode.
- **Cost arithmetic:** `idle_fuel_litres = fuel_rate_lph × idle_seconds ÷ 3600`; `idle_cost = idle_fuel_litres × configured_price_per_litre`. Decimal arithmetic is used by the calculation service.
- **Example:** 2.4 L/h × 120 s ÷ 3600 = 0.080 L; at $1.50/L, estimated cost is $0.12. At the configured 75% avoidable-cost assumption, potential savings are $0.09.
- **Efficiency score:** a deterministic fleet-level indicator uses trip summaries, idle minutes, and a documented 30 km/h conversion assumption. It is not a validated industry benchmark.

## 7. Non-functional requirements and performance

The requested architecture targets 100,000+ vehicles, 100,000+ events/sec, and a 3× burst for approximately five minutes. These have not been achieved or verified.

Local producer smoke runs sent 2,000 events at each configured rate. The simulator reported 100.0, 998.6, and 9,218.3 generated/delivered events/sec for the 100, 1,000, and 10,000 events/sec target steps. Kafka flushes succeeded; consumer group lag was zero after catch-up on the three topic partitions. These are short local producer-and-broker measurements, not sustained full-pipeline throughput, latency, or capacity results. No 100K sustained run or five-minute burst was performed.

The local stack uses a single Kafka broker and one consumer. Per-event MongoDB and Redis operations, synchronous PostgreSQL work for alerts, and dashboard polling are likely scaling constraints. See [the performance record](PERFORMANCE.md) for test commands, limits, and scaling direction.

## 8. Security and compliance

Implemented controls include salted PBKDF2 password hashes, short-lived HS256 JWTs, four application roles, fleet-scoped API queries, role-gated workflow changes, audit records, request IDs, security headers, input validation, and local environment-based secrets. The dashboard has been checked through browser login and authenticated views.

This is not a production security certification. OIDC/MFA, rate limiting, TLS termination, cloud secret management, key rotation operations, cross-tenant penetration testing, formal retention enforcement, and right-to-erasure automation are not implemented. No real personal or private vehicle data is included. See [security controls and gaps](SECURITY.md).

## 9. Test strategy and results

The test suite covers telemetry contracts, deterministic cost arithmetic, password/JWT primitives, route contracts, pagination bounds, bearer enforcement, role denial, headers, and dependency-readiness failure reporting.

Final local checks recorded:

- Backend/unit/API suite: **14 passed**, with 2 opt-in Docker integration checks skipped in the default run; one upstream Starlette/AnyIO deprecation warning remains.
- Docker integration suite: **2 passed** (service connectivity and MongoDB deduplication/Redis state).
- Full-stack smoke: Compose services healthy; login and fleet-scoped API reads worked; idle Kafka scenario persisted an alert, cost event, and recommendation.
- Malformed schema smoke: worker logged and committed an invalid message, then persisted a valid message queued behind it on the same partition.
- Browser smoke: Chrome login and Overview, Vehicles, Alerts, Actions, and Analytics views completed without page errors.
- Frontend: TypeScript and Vite production build passed.
- Ruff selected checks (`E4`, `E7`, `E9`, `F`, `I`) and Python compile checks passed.

Live container outage injection was not run: the environment's automatic command policy blocked reversible service-stop commands. The readiness failure path was instead simulated in a unit test. See [final verification](FINAL_VERIFICATION.md) and [failure-test notes](FAILURE_TESTING.md).

## 10. Observability

Structured HTTP and worker logs, request IDs, dependency readiness checks, and container health checks are implemented. The consumer group offset was inspected after the bounded load run and showed zero lag after catch-up. Prometheus/OpenTelemetry export, distributed tracing, alerting, and continuous lag/resource dashboards are future work.

## 11. AI/ML

No AI/ML is used for operational decisions. Idle detection, cost estimates, severity, efficiency scoring, and recommendations use deterministic code and explicit assumptions. Predictive maintenance or learned driver scoring would require representative, consented, appropriately governed data and model evaluation; neither is part of this implementation.

## 12. Architecture decisions

Five ADRs record decisions about Kafka event delivery, PostgreSQL plus MongoDB, Redis hot state, deterministic cost/rules, and deferring vector/AI retrieval. They are linked from [the architecture index](architecture/README.md).

## 13. Risks

- Writes across Kafka, MongoDB, Redis, and PostgreSQL are not a distributed transaction; crash-window recovery is not proven.
- The Compose environment is single-node and for local demonstration, not highly available.
- Mongo raw telemetry has no configured retention TTL.
- Low-utilisation and driver-level scores lack the necessary availability and assignment baselines.
- High-throughput targets, sustained API latency, and burst behavior have not been benchmarked.
- The local `.env` contains development credentials and must not be reused in a shared deployment.
- The supplied GitHub repository was empty when checked; the project workspace has no Git history yet.

## 14. Future enhancements

Add a dead-letter topic, write reconciliation/outbox strategy, summary generation from raw events, availability baselines, stronger tenant-isolation testing, retention and erasure workflows, metrics/tracing, multi-node infrastructure, and representative progressive/burst load tests. Confirm the submission's official template and any team declarations before final upload.

## 15. Demo

Follow [the five-minute demo guide](DEMO_GUIDE.md). The idempotent seed creates synthetic fleet examples; run it shortly before presenting because current Redis state expires after 15 minutes. Then sign in, show the overview and actions, publish the idle scenario, and trace the alert through its cost and recommendation. All values remain labeled as synthetic or estimated.

## 16. Repository checklist

- [x] Backend, frontend, simulator, analytics job, schema, migrations, and Compose setup
- [x] Automated unit/API tests and opt-in integration tests
- [x] Architecture, ADR, security, performance, demo, progress, and verification documentation
- [x] Solution document with implementation status and honest performance results
- [x] Browser and full-stack smoke checks
- [ ] Publish project code and documentation to the supplied GitHub repository
- [ ] Upload the solution PDF to the hackathon submission portal
- [ ] Obtain and apply the official Solution Submission Template if it differs from this document structure
- [ ] Verify organizer-specific technical-artifact upload requirements

## 17. Conclusion

FleetGuard demonstrates the `WHY → COST → ACTION` workflow on a local synthetic telemetry stream. The working demo connects event ingestion to a stored alert, a transparent estimated fuel cost, and a suggested action. It does not claim complete utilisation analytics, production security, cloud deployment, or achievement of the 100K scale targets.

## 18. Declarations

- **Data:** synthetic vehicle data only; no real personal or private fleet data.
- **AI usage:** no AI/ML-generated operational decision or cost formula is used; rules are deterministic.
- **Performance:** 100K figures are targets. Only bounded local smoke measurements are reported.
- **Savings:** potential savings use the configured 75% avoidable-cost assumption and are not realized savings.

## 19. Appendix: key commands

From the project root in PowerShell:

```powershell
Copy-Item infra/.env.example infra/.env
# Edit infra/.env and replace local passwords and JWT_SECRET_KEY before startup.
docker compose --env-file infra/.env -f infra/docker-compose.yml up --build -d

$env:DEMO_ADMIN_EMAIL = 'manager@example.test'
$env:DEMO_ADMIN_PASSWORD = 'choose-a-local-password-with-12-chars'
docker compose --env-file infra/.env -f infra/docker-compose.yml exec -T `
  -e DEMO_ADMIN_EMAIL=$env:DEMO_ADMIN_EMAIL `
  -e DEMO_ADMIN_PASSWORD=$env:DEMO_ADMIN_PASSWORD backend python seed_demo.py
Remove-Item Env:DEMO_ADMIN_EMAIL,Env:DEMO_ADMIN_PASSWORD

backend/.venv/Scripts/python.exe -m simulator.main `
  --vehicle-count 100000 --events 6 --rate 0 --scenario idle `
  --bootstrap-servers localhost:19092
backend/.venv/Scripts/python.exe -m pytest -q
Push-Location frontend; npm ci; npm run build; Pop-Location
```

Dashboard: `http://localhost:4173`  
API: `http://localhost:8000`  
OpenAPI UI: `http://localhost:8000/docs`  
Readiness: `http://localhost:8000/api/v1/health/ready`
