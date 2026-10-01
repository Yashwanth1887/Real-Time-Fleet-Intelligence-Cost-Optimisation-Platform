"""Opt-in integration checks for the Docker Compose dependencies."""

import os
import random
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from confluent_kafka import Producer
from pymongo import MongoClient
from redis import Redis
from sqlalchemy import text

from backend.app.core.config import get_settings
from backend.app.db.session import engine
from backend.app.repositories.telemetry import TelemetryStore
from simulator.main import make_event

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("FLEETGUARD_INTEGRATION") != "1",
                       reason="set FLEETGUARD_INTEGRATION=1 to run Docker-backed integration checks"),
]


def test_database_and_stream_services_are_reachable():
    settings = get_settings()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
    mongo = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=2000)
    try:
        assert mongo.admin.command("ping")["ok"] == 1.0
    finally:
        mongo.close()
    redis = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
    try:
        assert redis.ping()
    finally:
        redis.close()
    producer = Producer({"bootstrap.servers": settings.kafka_bootstrap_servers})
    assert producer.list_topics(timeout=3).brokers


def test_raw_event_dedup_and_redis_state():
    settings = get_settings()
    store = TelemetryStore(settings.mongo_url, settings.redis_url)
    event = make_event(999_999_999, 0, random.Random(17))
    # Reserve a test vehicle code in the same accepted synthetic namespace.
    payload = event.model_dump(mode="json")
    payload["vehicle_id"] = "FG-999999999"
    payload["event_id"] = str(uuid4())
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    try:
        assert store.persist(payload) is True
        assert store.persist(payload) is False
        assert store.collection.count_documents({"_id": payload["event_id"]}) == 1
        assert store.redis.hget(f"vehicle:{payload['vehicle_id']}", "event_id") == payload["event_id"]
    finally:
        store.collection.delete_one({"_id": payload["event_id"]})
        store.redis.delete(f"vehicle:{payload['vehicle_id']}")
        store.close()
