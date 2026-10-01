# Final verification

Recorded on 2026-09-30 in the local Windows development environment. **PASS** means the listed check ran successfully; **PARTIAL** means only the listed portion was verified; **NOT VERIFIED** means there is no supporting run. Synthetic fixture data and smoke runs are not production evidence.

| Requirement | Status | Evidence | Command |
| --- | --- | --- | --- |
| Compose configuration | PASS | Compose rendered without errors | `docker compose --env-file infra/.env -f infra/docker-compose.yml config --quiet` |
| Container build and startup | PASS | Backend, worker, frontend, PostgreSQL, MongoDB, Redis, and Kafka started; dependency health checks passed | `docker compose --env-file infra/.env -f infra/docker-compose.yml up --build -d` |
| Clean service restart | PASS | All containers restarted; readiness returned healthy; seeded PostgreSQL data survived | `docker compose --env-file infra/.env -f infra/docker-compose.yml restart` |
| Migrations | PASS | API image executes `alembic upgrade head`; API became healthy after startup and restart | Backend startup command in `backend/Dockerfile`; Compose health endpoint |
| Idempotent demo seed | PASS | Ran twice; both invocations completed with eight synthetic fixture vehicles, two sample alerts, and one fixture cost event | `docker compose --env-file infra/.env -f infra/docker-compose.yml exec -T -e DEMO_ADMIN_EMAIL=manager@example.test -e DEMO_ADMIN_PASSWORD=<local-password> backend python seed_demo.py` |
| API login and authenticated reads | PASS | Login succeeded; summary, alerts, recommendations, vehicle list, and live state returned data; recommendation reason/priority matched linked alert types | PowerShell `Invoke-RestMethod` against `/api/v1/auth/login`, `/api/v1/dashboard/summary`, `/api/v1/alerts`, `/api/v1/recommendations`, `/api/v1/vehicles`, `/api/v1/dashboard/live` |
| Dependency readiness | PASS | PostgreSQL, MongoDB, Redis, Kafka each reported `healthy`, including after restart | `Invoke-RestMethod http://localhost:8000/api/v1/health/ready` |
| Synthetic Kafka idle workflow | PASS (smoke) | Six messages published; consumer registered the generated synthetic vehicle and persisted one idle alert, cost event, and recommendation | `backend/.venv/Scripts/python.exe -m simulator.main --vehicle-count 100000 --events 6 --rate 0 --scenario idle --bootstrap-servers localhost:19092`; SQLAlchemy query in backend container |
| Malformed event handling | PASS (smoke) | Invalid schema event logged and committed; a valid event behind it on the same key/partition was persisted; temporary test data was deleted | Temporary producer check; `docker compose ... logs telemetry-worker` |
| Historical analytics APIs | PASS (smoke) | Current-day metrics, cost categories, and utilization summary returned rows | Authenticated GET `/api/v1/analytics/daily?days=1`, `/api/v1/analytics/cost?days=1`, `/api/v1/analytics/utilisation` |
| API documentation and dashboard serving | PASS (HTTP) | Swagger UI and frontend root each returned HTTP 200 | `Invoke-WebRequest http://localhost:8000/docs`; `Invoke-WebRequest http://localhost:4173` |
| Browser login and dashboard visual check | PASS (local Chrome) | Login succeeded; authenticated overview rendered populated fleet cards and live vehicles; Vehicles, Alerts, Actions, and Analytics views opened; no browser page errors | Temporary Playwright script with local Chrome; screenshot saved outside the repository |
| Backend tests | PASS | 14 passed; the 2 Docker-backed checks are skipped in default mode; one Starlette/AnyIO deprecation warning | `backend/.venv/Scripts/python.exe -m pytest -q` |
| Docker-backed integration tests | PASS | Both service reachability and raw event deduplication/Redis state tests passed | `FLEETGUARD_INTEGRATION=1 backend/.venv/Scripts/python.exe -m pytest tests/integration -q` |
| Simulated dependency failure | PASS (unit-level) | Readiness returned 503 and marked all four mocked dependencies unavailable; no real container was stopped | `backend/.venv/Scripts/python.exe -m pytest tests/test_api.py -q` |
| Python syntax compilation | PASS | Backend, simulator, analytics compiled successfully | `backend/.venv/Scripts/python.exe -m compileall -q backend simulator analytics` |
| Python lint | PASS (selected rules) | Ruff import, syntax-error, undefined-name, and pyflakes checks passed; FastAPI dependency defaults and intentional broad dependency-readiness catches are excluded from this isolated rule set | `backend/.venv/Scripts/python.exe -m ruff check --isolated --select E4,E7,E9,F,I backend simulator analytics tests` |
| Frontend production build | PASS | TypeScript and Vite build succeeded; Docker frontend image also built | `npm run build` from `frontend/` |
| Dependency outage injection | NOT VERIFIED | Attempts to stop individual Compose dependencies were blocked by automatic command policy. No outage was induced or claimed. | — |
| 100K active vehicle capacity | NOT VERIFIED | `--vehicle-count 100000` is an identifier-pool option; it does not provision or benchmark 100K active vehicles | — |
| Load steps | PARTIAL | 2,000 events each targeted 100, 1,000, and 10,000 events/sec; observed producer rates 100.0, 998.6, and 9,218.3 events/sec; producer flush succeeded; consumer lag later sampled at zero | See [performance notes](PERFORMANCE.md) |
| 100K events/sec sustained / 3× five-minute burst | NOT VERIFIED | No 100K run or five-minute burst run; no per-step full-pipeline latency/resource distribution | See [performance notes](PERFORMANCE.md) |
| Clean repository state | PARTIAL | Environment files, caches, build output, and logs are ignored; generated Alembic template files removed; no Git repository exists for tracked-file review/tagging | `git status` unavailable because the workspace is not a Git checkout |

## Limits

- Seeded records, vehicle locations, and simulator events are synthetic examples, not observed fleet results.
- The demo seed should be run shortly before presenting; Redis current-state examples expire after 15 minutes.
- The final Compose check used the existing local `infra/.env`; never reuse local demo credentials in a shared deployment.
- Dependency outage injection remains unverified. The automatic command policy blocked reversible container-stop commands, so no workaround was attempted.
- Remaining ignored cache/build artifacts and `infra/compose-up.log` could not be removed because the cleanup command was rejected by automatic command policy. No Git metadata exists for a tracked-file secret review.
