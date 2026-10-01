"""Kafka consumer that persists validated events before committing offsets."""

import logging
import signal
from decimal import Decimal

from confluent_kafka import Consumer, KafkaError
from pydantic import ValidationError

from app.core.config import get_settings
from app.repositories.telemetry import TelemetryStore
from app.schemas.telemetry import TelemetryEvent
from app.services.idle_cost import (
    calculate_idle_cost,
    persist_behavior_alert,
    persist_idle_impact,
)

logger = logging.getLogger("fleetguard.telemetry_consumer")
stopping = False


def request_stop(_signum: int, _frame: object) -> None:
    global stopping
    stopping = True


def main() -> None:
    settings = get_settings()
    consumer = Consumer({
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "group.id": "fleetguard-raw-storage-v1",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    store = TelemetryStore(settings.mongo_url, settings.redis_url)
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    consumer.subscribe(["fleet.telemetry.v1"])
    try:
        while not stopping:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                if message.error().code() != KafkaError._PARTITION_EOF:
                    logger.error("Kafka consume error: %s", message.error())
                continue
            try:
                event = TelemetryEvent.model_validate_json(message.value())
                store.persist(event.model_dump(mode="json"))
                alert, duration, episode_start = store.observe_idle(
                    event.vehicle_id, event.timestamp.timestamp(), event.engine_on,
                    event.speed_kph, settings.idle_threshold_seconds,
                )
                if alert:
                    impact = calculate_idle_cost(duration, event.fuel_rate_lph,
                                                 Decimal(settings.fuel_price_per_litre))
                    impact_record = persist_idle_impact(event, impact, settings.savings_assumption)
                    store.acknowledge_idle(event.vehicle_id, episode_start)
                    store.publish_alert(impact_record)
                    logger.info("Idle cost alert: %s", impact_record)
                for behavior, flagged in (("harsh_acceleration", event.harsh_acceleration),
                                          ("harsh_braking", event.harsh_braking)):
                    if flagged:
                        behavior_alert = persist_behavior_alert(event, behavior)
                        store.publish_alert(behavior_alert)
                        logger.info("Driver behavior alert: %s", behavior_alert)
                consumer.commit(message=message, asynchronous=False)
            except (ValidationError, ValueError) as exc:
                logger.error("Invalid telemetry at %s/%s: %s", message.topic(), message.offset(), exc)
                consumer.commit(message=message, asynchronous=False)
            except Exception:
                logger.exception("Telemetry persistence failed; offset remains uncommitted")
                raise
    finally:
        consumer.close()
        store.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    main()
