"""MongoDB raw event store and Redis current-state cache."""

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError
from redis import Redis


class TelemetryStore:
    def __init__(self, mongo_url: str, redis_url: str) -> None:
        self.mongo = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)
        self.collection = self.mongo.fleetguard.telemetry
        self.collection.create_index([("vehicle_id", ASCENDING), ("timestamp", ASCENDING)])
        self.redis = Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=3)

    def persist(self, event: dict[str, Any]) -> bool:
        """Persist once by event ID and atomically retain the newest hot state."""
        document = {"_id": str(event["event_id"]), **event}
        for field in ("timestamp", "ingestion_timestamp"):
            value = document.get(field)
            if isinstance(value, str):
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                document[field] = parsed.astimezone(timezone.utc)
        inserted = True
        try:
            self.collection.insert_one(document)
        except DuplicateKeyError:
            inserted = False
        vehicle_key = f"vehicle:{event['vehicle_id']}"
        event_time = datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00")).timestamp()
        self.redis.eval(
            """local previous = tonumber(redis.call('HGET', KEYS[1], 'timestamp_epoch') or '-1')
               if tonumber(ARGV[1]) > previous then
                 redis.call('HSET', KEYS[1], 'timestamp_epoch', ARGV[1], 'event_id', ARGV[2],
                   'timestamp', ARGV[3], 'speed_kph', ARGV[4], 'engine_on', ARGV[5],
                   'fuel_level_litres', ARGV[6])
                 redis.call('EXPIRE', KEYS[1], 900)
                 return 1
               end
               return 0""",
            1, vehicle_key, event_time, str(event["event_id"]), str(event["timestamp"]),
            str(event["speed_kph"]), str(event["engine_on"]).lower(), str(event["fuel_level_litres"]),
        )
        return inserted

    def observe_idle(self, vehicle_id: str, event_epoch: float, engine_on: bool,
                     speed_kph: float, threshold_seconds: int) -> tuple[int, int, float]:
        """Track an idle episode atomically; return alert flag, duration, episode start."""
        result = self.redis.eval(
            """local event_time = tonumber(ARGV[1])
               local last_time = tonumber(redis.call('HGET', KEYS[1], 'last_event_epoch') or '-1')
               local idle_since = tonumber(redis.call('HGET', KEYS[1], 'idle_since_epoch') or '-1')
               if event_time < last_time then return {0, 0, 0} end
               if ARGV[2] ~= 'true' or tonumber(ARGV[3]) > 0 then
                 redis.call('HSET', KEYS[1], 'last_event_epoch', event_time)
                 redis.call('HDEL', KEYS[1], 'idle_since_epoch', 'alert_triggered')
                 redis.call('EXPIRE', KEYS[1], 86400)
                 return {0, 0, 0}
               end
               if idle_since < 0 then idle_since = math.floor(event_time) end
               redis.call('HSET', KEYS[1], 'last_event_epoch', event_time, 'idle_since_epoch', idle_since)
               redis.call('EXPIRE', KEYS[1], 86400)
               local duration = math.floor(event_time - idle_since)
               local alerted = redis.call('HGET', KEYS[1], 'alert_triggered')
               if duration >= tonumber(ARGV[4]) and not alerted then return {1, duration, idle_since} end
               return {0, duration, idle_since}""",
            1, f"idle:{vehicle_id}", event_epoch, str(engine_on).lower(), speed_kph, threshold_seconds,
        )
        return int(result[0]), int(result[1]), float(result[2])

    def acknowledge_idle(self, vehicle_id: str, episode_start: float) -> None:
        self.redis.eval(
            """if tonumber(redis.call('HGET', KEYS[1], 'idle_since_epoch') or '-1') == tonumber(ARGV[1]) then
                 redis.call('HSET', KEYS[1], 'alert_triggered', '1')
               end
               return 1""",
            1, f"idle:{vehicle_id}", episode_start,
        )

    def publish_alert(self, alert: dict[str, Any]) -> None:
        import json
        self.redis.publish("fleetguard.alerts.v1", json.dumps(alert))

    def close(self) -> None:
        self.mongo.close()
        self.redis.close()
