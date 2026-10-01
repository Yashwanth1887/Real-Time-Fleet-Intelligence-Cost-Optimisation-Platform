"""Generate deterministic synthetic telemetry and optionally publish to Kafka."""

from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from confluent_kafka import Producer

from backend.app.schemas.telemetry import TelemetryEvent

TOPIC = "fleet.telemetry.v1"


def make_event(vehicle_number: int, sequence: int, rng: random.Random,
               out_of_order: bool = False, force_idle: bool = False,
               event_time: datetime | None = None) -> TelemetryEvent:
    now = datetime.now(timezone.utc)
    vehicle_id = f"FG-{vehicle_number:09d}"
    event_id = uuid5(NAMESPACE_URL, f"fleetguard/{vehicle_id}/{sequence}")
    engine_on = True if force_idle else rng.random() > 0.08
    idle = force_idle or (engine_on and rng.random() < 0.22)
    speed = 0.0 if idle or not engine_on else round(rng.uniform(5, 110), 1)
    return TelemetryEvent(
        event_id=event_id,
        vehicle_id=vehicle_id,
        timestamp=event_time or (now - timedelta(seconds=rng.randint(1, 30) if out_of_order else 0)),
        latitude=round(rng.uniform(25, 49), 6),
        longitude=round(rng.uniform(-124, -67), 6),
        speed_kph=0.0 if force_idle else speed,
        engine_on=engine_on,
        engine_rpm=800 if force_idle else (rng.randint(650, 900) if idle else (rng.randint(1000, 3500) if engine_on else 0)),
        fuel_level_litres=round(rng.uniform(5, 250), 2),
        fuel_rate_lph=2.4 if force_idle else round(rng.uniform(1.2, 3.8) if idle else (rng.uniform(3, 20) if engine_on else 0), 2),
        odometer_km=round(rng.uniform(100, 900000), 1),
        harsh_acceleration=rng.random() < 0.015,
        harsh_braking=rng.random() < 0.02,
        battery_voltage=round(rng.uniform(12.1, 14.6), 2),
        ambient_temperature_c=round(rng.uniform(-10, 38), 1),
        trip_id=uuid5(NAMESPACE_URL, f"fleetguard/trip/{vehicle_id}/{sequence // 100}") if engine_on else None,
        sequence_number=sequence,
    )


def run(vehicle_count: int, event_count: int, rate: float, seed: int,
        bootstrap_servers: str | None, duplicate_every: int, reorder_every: int,
        scenario: str = "normal") -> int:
    rng = random.Random(seed)
    delivery_errors: list[str] = []
    def on_delivery(error, message) -> None:
        if error:
            delivery_errors.append(str(error))
    producer = Producer({"bootstrap.servers": bootstrap_servers}) if bootstrap_servers else None
    produced = 0
    started = time.monotonic()
    scenario_start = datetime.now(timezone.utc) - timedelta(seconds=max(0, event_count - 1) * 30)
    idle_vehicle_number = (time.time_ns() // 1_000_000) % vehicle_count + 1
    for sequence in range(event_count):
        vehicle_number = idle_vehicle_number if scenario == "idle" else rng.randrange(1, vehicle_count + 1)
        event_time = scenario_start + timedelta(seconds=sequence * 30) if scenario == "idle" else None
        event = make_event(vehicle_number, sequence, rng, reorder_every > 0 and sequence % reorder_every == 0,
                           force_idle=scenario == "idle", event_time=event_time)
        payload = event.model_dump_json().encode("utf-8")
        if producer:
            while True:
                try:
                    producer.produce(TOPIC, key=event.vehicle_id.encode(), value=payload, callback=on_delivery)
                    break
                except BufferError:
                    producer.poll(0.5)
            producer.poll(0)
        else:
            print(payload.decode())
        produced += 1
        if duplicate_every > 0 and (sequence + 1) % duplicate_every == 0:
            if producer:
                while True:
                    try:
                        producer.produce(TOPIC, key=event.vehicle_id.encode(), value=payload, callback=on_delivery)
                        break
                    except BufferError:
                        producer.poll(0.5)
                producer.poll(0)
            else:
                print(payload.decode())
            produced += 1
        if rate > 0:
            target = (sequence + 1) / rate
            delay = target - (time.monotonic() - started)
            if delay > 0:
                time.sleep(delay)
    if producer:
        remaining = producer.flush(10)
        if remaining or delivery_errors:
            print(f"Kafka delivery failed: {remaining} messages remain; {len(delivery_errors)} delivery errors"
                  + (f" (first: {delivery_errors[0]})" if delivery_errors else ""), file=sys.stderr)
            return 1
    elapsed = max(time.monotonic() - started, 1e-9)
    suffix = f"; idle scenario vehicle FG-{idle_vehicle_number:09d}" if scenario == "idle" else ""
    print(f"Generated {produced} synthetic events for {vehicle_count:,} configured vehicles "
          f"in {elapsed:.3f}s ({produced / elapsed:.1f} generated events/s){suffix}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vehicle-count", type=int, default=100_000)
    parser.add_argument("--events", type=int, default=10)
    parser.add_argument("--rate", type=float, default=5.0, help="target events/second; 0 disables pacing")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap-servers", default=None, help="e.g. localhost:9092; omit for JSON stdout")
    parser.add_argument("--duplicate-every", type=int, default=0, help="repeat each Nth event")
    parser.add_argument("--reorder-every", type=int, default=0, help="emit a stale event timestamp every N events")
    parser.add_argument("--scenario", choices=("normal", "idle"), default="normal",
                        help="idle emits one vehicle stationary for 30 simulated seconds per event")
    args = parser.parse_args()
    if args.vehicle_count < 1 or args.events < 0 or args.rate < 0:
        parser.error("vehicle count must be positive; events and rate must be non-negative")
    return run(args.vehicle_count, args.events, args.rate, args.seed, args.bootstrap_servers,
               args.duplicate_every, args.reorder_every, args.scenario)


if __name__ == "__main__":
    raise SystemExit(main())
