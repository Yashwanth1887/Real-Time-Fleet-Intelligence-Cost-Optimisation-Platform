# Architecture

## System context

```mermaid
flowchart LR
  manager[Fleet manager] -->|browser + JWT| ui[React dashboard]
  ui -->|versioned JSON API| api[FastAPI modular monolith]
  sim[Synthetic simulator] -->|durable events| kafka[(Kafka)]
  api --> pg[(PostgreSQL)]
  api --> mongo[(MongoDB)]
  api --> redis[(Redis)]
  kafka --> worker[Telemetry consumer]
  worker --> mongo
  worker --> redis
  worker --> pg
  batch[Daily analytics job] --> pg
```

## Containers and responsibilities

```mermaid
flowchart TB
  subgraph local[Local Docker Compose]
    browser[Browser]
    frontend[React + Vite build / Nginx]
    backend[FastAPI API]
    worker[Kafka consumer worker]
    simulator[Synthetic Python producer on host]
    kafka[(Kafka KRaft single broker)]
    postgres[(PostgreSQL 16)]
    mongo[(MongoDB 7)]
    redis[(Redis 7)]
    browser --> frontend --> backend
    simulator -->|localhost:19092| kafka
    kafka -->|kafka:9092| worker
    backend --> postgres
    backend --> mongo
    backend --> redis
    worker --> postgres
    worker --> mongo
    worker --> redis
  end
```

## Backend components

```mermaid
flowchart LR
  routes[API routers: auth, fleet, dashboard, analytics] --> schemas[Pydantic validation]
  routes --> auth[JWT + RBAC]
  routes --> sqlrepo[SQLAlchemy repositories]
  routes --> hotrepo[Mongo/Redis telemetry repository]
  consumer[Kafka consumer] --> schemas
  consumer --> rules[Deterministic idle and behavior rules]
  rules --> cost[Decimal cost engine]
  rules --> sqlrepo
  consumer --> hotrepo
  batch[Daily analytics job] --> sqlrepo
```

## Event sequence

```mermaid
sequenceDiagram
  participant S as Simulator
  participant K as Kafka
  participant W as Worker
  participant M as MongoDB
  participant R as Redis
  participant P as PostgreSQL
  participant A as Fleet manager UI/API
  S->>K: Publish validated telemetry with event ID
  K->>W: Deliver event to consumer group
  W->>M: Insert raw event (unique event ID)
  W->>R: Update current vehicle state and idle window
  alt threshold crossed
    W->>P: Insert alert, cost, recommendation (unique event key)
    W->>R: Acknowledge idle episode and publish alert notice
  end
  W->>K: Commit offset after successful writes
  A->>P: Read fleet summary, alerts, costs, recommendations
  A->>R: Read bounded current state
```

## Failure sequence

```mermaid
sequenceDiagram
  participant K as Kafka
  participant W as Worker
  participant M as MongoDB
  participant P as PostgreSQL
  K->>W: Deliver event
  W->>M: Insert raw document
  M-->>W: Inserted
  W->>P: Persist alert/cost and DB is unavailable
  P--xW: Storage error
  Note over W,K: Worker exits without committing the event offset
  W->>K: Restart and receive event again
  W->>M: Insert same event ID
  M-->>W: Duplicate key; continue idempotently
  W->>P: Retry relational writes
  P-->>W: Persisted
  W->>K: Commit offset
```

The diagram describes intended retry behavior. A distributed transaction is not used; crash windows still require failure-injection testing.

## Persistence map

| Store | Data | Why |
| --- | --- | --- |
| PostgreSQL | Fleet/user/vehicle relations, trips, summaries, alerts, recommendations, costs, metrics, audit events | Transactions, constraints, indexes, relational ownership |
| MongoDB | Raw telemetry event documents keyed by event ID | Flexible event records and high-volume event history |
| Redis | Current state, idle episode state, alert pub/sub notice | Low-latency expiring state and atomic Lua updates |
| Kafka | Durable telemetry topic and consumer offsets | Producer/consumer separation and replayable event delivery |
| Vector store | None | Current rule-based recommender has no semantic corpus to retrieve |

## Why these technologies

- **Kafka:** buffers telemetry independently of consumers and supports replay via offsets. The checked-in Compose broker is a single-node demo, not a production cluster.
- **PostgreSQL:** normalized fleet relationships, idempotency constraints, transactional alerts/costs, and analytics aggregates.
- **MongoDB:** event-shaped raw telemetry with a unique event key and vehicle/time index.
- **Redis:** hot current state and atomic idle-duration tracking; expiry bounds state growth.
- **FastAPI:** typed request validation, versioned endpoints, OpenAPI, and dependency injection.
- **React/TypeScript:** responsive role-aware dashboard; it polls bounded API snapshots every five seconds.
- **Vector capability:** deliberately omitted until semantic retrieval offers a measured benefit.

## Deployment architecture

The local layout is verified through Docker Compose when the engine is available. A cloud deployment would use managed PostgreSQL/MongoDB, a multi-broker Kafka cluster, Redis HA, private networking, TLS, managed secrets, and separately scaled API/consumer replicas. Cloud deployment is a target only; it has not been performed.
