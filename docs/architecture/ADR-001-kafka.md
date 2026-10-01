# ADR-001: Kafka for telemetry event streaming

## Context

Vehicle telemetry arrives independently from API dashboard reads and may be bursty, duplicated, or delayed.

## Decision

Publish telemetry to a versioned Kafka topic and consume it with a consumer group. Disable automatic offset commits and commit only after persistence succeeds.

## Alternatives

- Synchronous HTTP writes directly to the API/database.
- Redis Pub/Sub as the only event channel.
- A local in-process queue.

## Consequences

Kafka separates producer and consumer lifecycles and supports durable replay. It adds operational complexity. Local Compose uses one broker and does not prove high availability or target throughput.
