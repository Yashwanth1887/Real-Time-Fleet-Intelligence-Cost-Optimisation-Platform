# ADR-003: Redis for current state and idle episode tracking

## Context

The UI needs current vehicle state and the idle detector needs per-vehicle time-window state with out-of-order protection.

## Decision

Use Redis hashes with expirations for hot state and short Lua scripts for atomic timestamp comparisons, idle windows, and acknowledgments.

## Alternatives

- Query MongoDB on every dashboard poll.
- Keep state only in worker memory.
- Store every transient state update in PostgreSQL.

## Consequences

Reads and state transitions are fast; Redis loss requires state reconstruction from replayed telemetry. Raw events stay durable in MongoDB/Kafka.
