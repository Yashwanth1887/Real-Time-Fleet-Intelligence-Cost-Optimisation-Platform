# Security and privacy

## Implemented

- All fleet data routes require a signed JWT bearer token. Tokens expire after 30 minutes and use HS256 with a required `JWT_SECRET_KEY` of at least 32 characters.
- Login verifies a salted PBKDF2-HMAC-SHA256 hash (600,000 iterations). Demo passwords must be at least 12 characters.
- Roles are `ADMIN`, `FLEET_MANAGER`, `ANALYST`, and `VIEWER`. All roles can read their fleet; only administrators and fleet managers can resolve alerts or update recommendation status.
- Token fleet claims are applied to fleet, vehicle, alert, recommendation, cost, summary, telemetry, live-state, and analytics reads/actions. Cross-fleet resource IDs return 404.
- Successful login and manager status changes create audit records. Request IDs and important worker actions are logged.
- API validation uses Pydantic; collection and list endpoints have bounded limits. Basic browser security headers and explicit CORS origins are configured.
- PostgreSQL/MongoDB/Redis/Kafka credentials are environment values. `.env` files are ignored. The checked-in `.env.example` files contain obvious replacement values only.
- Simulator data is synthetic; no real driver identity or private vehicle feed is used.

## Planned or not implemented

- OAuth2/OIDC federation, MFA, refresh-token rotation, token revocation, login rate limiting, and lockout controls.
- TLS/mTLS certificates, cloud secret-manager integration, encryption-key rotation, and production network policies.
- Failed-login audit rows, broad administrative audit review endpoints, and a right-to-erasure workflow.
- Configurable raw-location retention and production backup/deletion policies.

## Tenant isolation

Each user is associated with one fleet; the JWT contains that fleet UUID. Read and update queries include the token's fleet ID. Admin users remain scoped to their assigned fleet in this demo. Production should also consider PostgreSQL row-level security, database roles with least privilege, and explicit authorization tests for every new query.

## Location and retention

Telemetry contains latitude and longitude, but the simulator samples synthetic coordinates only. MongoDB raw telemetry currently has no TTL index, so event retention is unbounded until an operator configures one. A production system needs purpose-based retention, access review, deletion propagation across stores/backups, and documented handling of privacy requests.

## STRIDE-style threat review

| Threat | Example | Current mitigation | Remaining work |
| --- | --- | --- | --- |
| Spoofing | Forged bearer token or password guessing | HMAC-signed short-lived JWT; salted slow password hash | MFA, rate limits, key rotation, refresh/revocation |
| Tampering | Change telemetry/cost payload | Pydantic validation, Kafka event IDs, unique keys, DB constraints | Producer identity/signing, schema registry, immutable audit export |
| Repudiation | Manager denies resolving an alert | Successful login and state-change audit rows; request IDs | Failed-login events, export/retention, audit-read API |
| Information disclosure | Read another fleet's vehicle/location | Fleet claim filters, bearer auth, synthetic-only demo data | Automated cross-tenant integration suite, field-level policy |
| Denial of service | Flood API/Kafka or expensive analytics | Bounded pagination, health checks, async durable buffer | Rate limiting, quotas, autoscaling and load verification |
| Elevation of privilege | Viewer changes alert status | Status changes require ADMIN/FLEET_MANAGER role | Full role matrix tests and least-privilege production IAM |

## Production recommendations

Use managed secret storage and TLS, rotate JWT signing keys, add OAuth/OIDC and MFA, enforce rate limits and request-size limits, configure MongoDB retention and backups, enable database row-level security, perform dependency/image scanning, and test tenant isolation and recovery before handling real vehicle data.
