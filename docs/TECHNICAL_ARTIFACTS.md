# Technical Artifact Register

**Project:** FleetGuard — Real-Time Fleet Intelligence & Cost Optimisation Platform  
**Purpose:** Navigation guide to the implementation, architecture, operational evidence, and submission materials in this repository.  
**Repository:** [Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform)

## 1. Submission package

| Artifact | Location | Description |
| --- | --- | --- |
| Solution document | [PDF](../submission/FleetGuard_Solution_Document.pdf) | Completed using the supplied hackathon template. |
| Editable solution document | [DOCX](../submission/FleetGuard_Solution_Document.docx) | Editable source for the submitted PDF. |
| Product screenshot | [Dashboard image](../submission/images/fleetguard-dashboard.png) | Screenshot captured during the local browser verification. |
| Submission index | [Submission README](../submission/README.md) | Short guide to the submission bundle. |

## 2. Product and implementation

| Area | Primary location | Contents |
| --- | --- | --- |
| Product overview and setup | [Root README](../README.md) | Scope, architecture summary, local setup, test commands, and known limitations. |
| Backend API | [`backend/app/api/`](../backend/app/api/) | Authentication, dashboard, routing, dependency, and system endpoints. |
| Business rules and persistence | [`backend/app/services/`](../backend/app/services/), [`backend/app/repositories/`](../backend/app/repositories/) | Idle-cost logic and telemetry persistence boundary. |
| Event processing | [`backend/app/workers/`](../backend/app/workers/), [`simulator/`](../simulator/) | Kafka consumer and synthetic telemetry producer. |
| Frontend | [`frontend/src/`](../frontend/src/) | React and TypeScript fleet dashboard. |
| Database schema | [`backend/app/db/`](../backend/app/db/), [`backend/migrations/`](../backend/migrations/) | SQLAlchemy models and Alembic migrations. |
| Local deployment | [`infra/docker-compose.yml`](../infra/docker-compose.yml) | Docker Compose services and health checks. |
| Automated checks | [`tests/`](../tests/) | Unit/API tests and opt-in service integration tests. |

## 3. Architecture and design records

- [Architecture index and diagrams](architecture/README.md)
- [ADR-001: Kafka event streaming](architecture/ADR-001-kafka.md)
- [ADR-002: Polyglot storage](architecture/ADR-002-polyglot-storage.md)
- [ADR-003: Redis hot state](architecture/ADR-003-redis-hot-state.md)
- [ADR-004: Deterministic cost estimates](architecture/ADR-004-deterministic-costs.md)
- [ADR-005: Vector search and AI deferral](architecture/ADR-005-vector-and-ai.md)
- [Database model](DATABASE.md)

## 4. Verification and operating evidence

| Record | Purpose |
| --- | --- |
| [Final verification](FINAL_VERIFICATION.md) | Results and limits of the documented application, integration, browser, build, and load checks. |
| [Performance and scale](PERFORMANCE.md) | Load-step setup, measured producer rates, and unmeasured performance targets. |
| [Failure testing](FAILURE_TESTING.md) | Tested malformed-event/readiness behavior and unverified outage scenarios. |
| [Implementation progress](IMPLEMENTATION_PROGRESS.md) | Feature implementation and completion tracking. |
| [Observability](OBSERVABILITY.md) | Current health/logging facilities and proposed monitoring work. |

## 5. Security, data, and demonstration

- [Security controls and known gaps](SECURITY.md)
- [Synthetic data declaration](DEMO_DATA.md)
- [Demonstration runbook](DEMO_GUIDE.md)
- [Cost model assumptions](COST_MODEL.md)
- [Intelligence rules](INTELLIGENCE.md)

## 6. Reproduce the local demonstration

From the repository root in PowerShell, with Docker Desktop running:

```powershell
Copy-Item infra/.env.example infra/.env
# Replace demo credentials and JWT_SECRET_KEY in infra/.env before shared use.
docker compose --env-file infra/.env -f infra/docker-compose.yml up --build -d
docker compose --env-file infra/.env -f infra/docker-compose.yml ps
```

Use the account-seeding and synthetic-event commands in the [root README](../README.md) and [demo guide](DEMO_GUIDE.md). Do not use real vehicle or driver data in this demo configuration.

## 7. Evidence boundaries and outstanding submission items

- All bundled vehicle and telemetry examples are synthetic.
- The recorded 100, 1,000, and 10,000 events/sec runs measured simulator/broker delivery for 2,000 events per step. They do not establish end-to-end service capacity.
- 100,000 active vehicles, 100,000 events/sec, sustained operation, p95/p99 latency, and a five-minute 3× burst remain unverified targets.
- The project does not include a production observability dashboard, an SBOM, a CI workflow, or a recorded demo video. The solution document identifies these limits; add the video before portal submission.
