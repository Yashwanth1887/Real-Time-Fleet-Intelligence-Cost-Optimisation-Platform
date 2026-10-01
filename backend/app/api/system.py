"""Service readiness and dependency checks."""

import logging

from confluent_kafka import Producer
from fastapi import APIRouter, Response
from pymongo import MongoClient
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine

logger = logging.getLogger("fleetguard.readiness")
router = APIRouter(tags=["system"])


@router.get("/health/ready")
def readiness(response: Response) -> dict[str, object]:
    settings = get_settings()
    checks: dict[str, str] = {}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["postgres"] = "healthy"
    except Exception as exc:
        checks["postgres"] = "unavailable"
        logger.warning("readiness dependency=postgres error=%s", type(exc).__name__)
    mongo = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=1500)
    try:
        mongo.admin.command("ping")
        checks["mongodb"] = "healthy"
    except Exception as exc:
        checks["mongodb"] = "unavailable"
        logger.warning("readiness dependency=mongodb error=%s", type(exc).__name__)
    finally:
        mongo.close()
    redis = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
    try:
        redis.ping()
        checks["redis"] = "healthy"
    except Exception as exc:
        checks["redis"] = "unavailable"
        logger.warning("readiness dependency=redis error=%s", type(exc).__name__)
    finally:
        redis.close()
    producer = Producer({"bootstrap.servers": settings.kafka_bootstrap_servers})
    try:
        producer.list_topics(timeout=2)
        checks["kafka"] = "healthy"
    except Exception as exc:
        checks["kafka"] = "unavailable"
        logger.warning("readiness dependency=kafka error=%s", type(exc).__name__)
    finally:
        producer.flush(1)
    healthy = all(value == "healthy" for value in checks.values())
    response.status_code = 200 if healthy else 503
    return {"status": "healthy" if healthy else "degraded", "dependencies": checks}
