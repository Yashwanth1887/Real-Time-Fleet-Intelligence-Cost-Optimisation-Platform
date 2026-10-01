# Observability

## Implemented

- API and worker logs use timestamps, severity, and component names.
- API request logs include a generated or caller-supplied request ID, method, path, status code, and elapsed milliseconds. Query strings and credentials are not logged.
- Responses include `X-Request-ID` and baseline browser security headers.
- `/health` reports process liveness. `/api/v1/health/ready` checks PostgreSQL, MongoDB, Redis, and Kafka and returns `503` with component names when dependencies are unavailable.
- Compose services define dependency health checks. The API readiness endpoint is also its container health check.

## Not implemented

- Prometheus/OpenTelemetry metrics export, traces, log aggregation, alerting, and production dashboards.
- Per-tenant service-level objectives and telemetry lag metrics.

The local readiness endpoint is diagnostic, not an external monitoring service. It performs a bounded check against each dependency when called.
