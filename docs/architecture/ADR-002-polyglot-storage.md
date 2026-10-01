# ADR-002: PostgreSQL, MongoDB, and Redis by data shape

## Context

Fleet ownership and financial actions are relational; raw telemetry is event-shaped; current vehicle state needs fast access.

## Decision

Use PostgreSQL for normalized business records and aggregates, MongoDB for raw event documents, and Redis for expiring current state and atomic idle tracking.

## Alternatives

- Put all records in PostgreSQL.
- Put all records in a document database.
- Use Redis as durable event storage.

## Consequences

Each store fits its access pattern, but cross-store consistency relies on idempotent writes and Kafka redelivery rather than a distributed transaction. Retention and backup policies remain to be configured for production.
