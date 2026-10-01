# Performance and scale

## Target versus observed

| Measure | Target | Tested/observed | Status |
| --- | --- | --- | --- |
| Vehicle identifiers | 100,000+ | Simulator accepts `--vehicle-count 100000`; this defines an ID pool and does not provision 100,000 records | Capability parameter only |
| Sustained telemetry | 100,000+ events/sec | Local producer runs targeted 100, 1,000, and 10,000 events/sec for 2,000 events each; observed rates were 100.0, 998.6, and 9,218.3 generated/delivered events/sec | Smoke measurements only; no 100K result |
| Burst | 3× sustained target for about five minutes | No five-minute 3× burst run | Target only |
| Progressive load steps | 100, 1,000, 10,000, then 100,000 events/sec if host allows | 100/1K/10K producer steps ran; 100K step not run | Partial; producer and broker only |
| API summary latency | Proposed target: p95 < 500 ms | No latency distribution collected | Target only |
| Bounded analytics latency | Proposed target: p95 < 2 s on demo dataset | No latency distribution collected | Target only |
| UI update interval | 5-second polling interval in frontend code | Browser verified API polling indicator; end-to-end interval not timed | Configured interval only |
| Error rate, CPU, memory | Measure during each load step | Simulator reported no Kafka delivery errors; consumer lag sampled at 0 after catch-up. Per-step resource and error distributions not collected. | Partial |

The 100K figures are capacity goals from the hackathon brief, not achieved performance. Each 2,000-event producer run completed its Kafka flush without reported delivery errors. After the 6,000-event run, Kafka consumer group offsets matched log-end offsets across all three partitions (lag 0). This is a bounded local smoke result; it does not establish sustained end-to-end throughput, API latency, or production capacity.

## Environment

- Windows workspace, Python 3.13.15, Docker Engine 29.6.2, Docker Compose 5.3.1.
- Hardware specifications and host CPU/memory limits were not recorded.
- PostgreSQL, MongoDB, Redis, and Kafka ran as single-node local containers.
- Each rate step used 2,000 synthetic events and the simulator's producer elapsed-time summary after Kafka flush. Consumer lag was sampled after the run; per-step lag/latency distributions and peak resource use were not captured.

## Load command

The simulator supports paced and unpaced runs. The completed local steps were:

```powershell
backend/.venv/Scripts/python.exe -m simulator.main --vehicle-count 100000 --events 2000 --rate 100 --seed 101 --bootstrap-servers localhost:19092
backend/.venv/Scripts/python.exe -m simulator.main --vehicle-count 100000 --events 2000 --rate 1000 --seed 102 --bootstrap-servers localhost:19092
backend/.venv/Scripts/python.exe -m simulator.main --vehicle-count 100000 --events 2000 --rate 10000 --seed 103 --bootstrap-servers localhost:19092
```

That producer summary measures the simulator's own run and broker delivery; it does not measure consumer processing latency or API latency. A 100K target run and a five-minute burst were not attempted on this single-broker, single-consumer workstation stack.

## Known bottlenecks and scaling direction

- Compose uses one Kafka broker and the consumer group starts with one worker; the topic has three partitions. Add brokers/partitions and consumer replicas only after measuring partition skew and idempotent PostgreSQL write load.
- Each event makes MongoDB, Redis, and sometimes PostgreSQL calls. Batch/group commits and an outbox or replayable alert state may be needed at higher rates.
- Redis hot state is one expiring key per active vehicle; Mongo raw event storage has no TTL policy yet.
- API database calls use synchronous SQLAlchemy and the dashboard polls five endpoints every five seconds. Measure request concurrency before adding API replicas or increasing polling frequency.
- Single-node Compose credentials and health checks are local demo configuration, not a cloud deployment.
