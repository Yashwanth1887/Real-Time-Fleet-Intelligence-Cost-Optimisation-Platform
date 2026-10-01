# Failure handling and test status

## Implemented behavior and observed checks

| Failure or condition | Current behavior | Verification |
| --- | --- | --- |
| PostgreSQL/MongoDB/Redis write fails in the consumer | Worker raises before committing the Kafka offset; container restart policy is `unless-stopped` | Code reviewed; dependency outage not injected |
| Worker stops after Mongo insert but before Kafka commit | Redelivery hits Mongo's unique event ID; Redis latest-state update is retried | Duplicate event path tested; crash between writes not injected |
| Repeated Kafka message | Raw event stored once by event ID; SQL alert/cost/recommendation rows use unique event keys | Raw-event deduplication integration test passed; idle episode replay previously exercised |
| Out-of-order event | Redis Lua state ignores timestamps older than latest; Mongo retains the raw record | Simulator supports stale timestamps; high-volume behavior not separately asserted |
| Invalid telemetry schema | Worker logs and commits the bad offset so the partition can continue | Injected invalid JSON-shaped schema followed by a valid event on the same key/partition; worker logged validation error and persisted the following event |
| API dependency failure | Readiness returns HTTP 503 and lists unavailable dependency; SQLAlchemy API errors map to 503 | Unit test simulated all four dependency failures and asserted 503 plus per-service status; live service outage not injected |
| Backend and full-stack restart | Compose restarts containers and the API reruns migrations | Full stack restart completed; readiness returned healthy and PostgreSQL data persisted |

## Not verified

- Kafka, MongoDB, Redis, or PostgreSQL outage/recovery during active consumption.
- Worker crash between Mongo, Redis, PostgreSQL writes and Kafka offset commit.
- Broker leader loss, consumer rebalance under load, or durable dead-letter handling.
- Permanent database outage and replay of uncommitted data after recovery.

Attempts to stop individual Compose dependencies were rejected by the environment's automatic command policy. No workaround was attempted and no outage behavior is claimed. The implementation does not provide a dead-letter topic for malformed records; it logs and commits invalid-schema messages so one bad payload cannot block a partition. The four stores do not share a distributed transaction, so exactly-once behavior across all stores is not claimed.
