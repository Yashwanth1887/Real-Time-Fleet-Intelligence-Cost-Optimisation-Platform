# Deterministic intelligence rules

All event rules use validated synthetic telemetry; no ML model is involved in alert decisions.

| Rule | Input and trigger | Output |
| --- | --- | --- |
| Excessive idling | Engine on, speed 0, event-time span at least `IDLE_THRESHOLD_SECONDS` (default 120) | One alert per idle episode, fuel estimate, cost, and recommendation |
| Harsh braking | `harsh_braking=true` | High-severity alert and safe-driving recommendation |
| Harsh acceleration | `harsh_acceleration=true` | Medium-severity alert and coaching recommendation |
| Fuel waste | Estimated from idle duration × reported fuel rate | Cost event and savings estimate |
| Low utilisation | Not emitted yet; scheduled availability and reliable trip aggregates are not present in this demo feed | Planned batch rule |

Redis Lua updates per-vehicle idle state atomically and ignores older event timestamps. MongoDB's unique event ID, SQL event keys, and synchronous Kafka offset commits make redelivery safe for persisted event/alert records. There is no distributed transaction across MongoDB, Redis, PostgreSQL, and Kafka; the worker retries failed storage by leaving the Kafka offset uncommitted.

## Fleet efficiency score

The score is a deterministic 0–100 fleet score and is `null` until telemetry summaries exist. Let `I` be total idle minutes, `D` be total summary distance in kilometres, `H` be harsh-behaviour alerts, and `N` be summarized telemetry event count.

```text
estimated_moving_minutes = D / 30 km/h × 60
idle_score = 100 × (1 − I / (I + estimated_moving_minutes))
behavior_score = 100 × (1 − min(H / N, 1))
fleet_score = round(0.70 × idle_score + 0.30 × behavior_score)
```

The 30 km/h conversion and weights are demo assumptions, not measured fleet benchmarks. Vehicle- and driver-level scores are not emitted because there is no complete assignment and driver-event baseline in the demo data.
