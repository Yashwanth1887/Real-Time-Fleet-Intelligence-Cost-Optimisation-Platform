from uuid import uuid4

from app.core.config import get_settings
from app.security.auth import create_access_token
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_versioned_health_and_docs_are_available():
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/docs").status_code == 200


def test_openapi_contains_dashboard_analytics_and_fleet_routes():
    paths = client.get("/openapi.json").json()["paths"]
    for path in (
        "/api/v1/fleets",
        "/api/v1/vehicles",
        "/api/v1/dashboard/summary",
        "/api/v1/dashboard/live",
        "/api/v1/health/ready",
        "/api/v1/analytics/cost",
        "/api/v1/analytics/idle",
        "/api/v1/analytics/utilisation",
        "/api/v1/analytics/savings",
        "/api/v1/alerts",
        "/api/v1/recommendations",
    ):
        assert path in paths


def test_api_rejects_unbounded_pagination(monkeypatch):
    key = "unit-test-jwt-secret-value-that-is-long-enough"
    monkeypatch.setenv("JWT_SECRET_KEY", key)
    get_settings.cache_clear()
    token = create_access_token("user-id", "viewer@example.test", str(uuid4()), "VIEWER")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/vehicles?limit=5000", headers=headers).status_code == 422
    assert client.get("/api/v1/alerts?limit=0", headers=headers).status_code == 422
    get_settings.cache_clear()


def test_dashboard_requires_bearer_authentication():
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_viewer_cannot_change_alert_status(monkeypatch):
    key = "unit-test-jwt-secret-value-that-is-long-enough"
    monkeypatch.setenv("JWT_SECRET_KEY", key)
    get_settings.cache_clear()
    token = create_access_token("user-id", "viewer@example.test", str(uuid4()), "VIEWER")
    response = client.patch("/api/v1/alerts/00000000-0000-0000-0000-000000000001/status?status=resolved",
                            headers={"Authorization": f"Bearer {token}"})
    get_settings.cache_clear()
    assert response.status_code == 403


def test_http_responses_include_request_id_and_security_headers():
    response = client.get("/health", headers={"X-Request-ID": "request-test-123"})
    assert response.headers["x-request-id"] == "request-test-123"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_readiness_reports_all_dependencies_unavailable(monkeypatch):
    from app.api import system

    class BrokenConnection:
        def __enter__(self):
            raise OSError("simulated PostgreSQL outage")

        def __exit__(self, *_args):
            return False

    class BrokenMongo:
        admin = type("Admin", (), {"command": lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OSError("simulated MongoDB outage"))})()

        def close(self):
            pass

    class BrokenRedis:
        def ping(self):
            raise OSError("simulated Redis outage")

        def close(self):
            pass

    class BrokenProducer:
        def __init__(self, *_args, **_kwargs):
            pass

        def list_topics(self, **_kwargs):
            raise OSError("simulated Kafka outage")

        def flush(self, *_args):
            return 0

    monkeypatch.setattr(system.engine, "connect", lambda: BrokenConnection())
    monkeypatch.setattr(system, "MongoClient", lambda *_args, **_kwargs: BrokenMongo())
    monkeypatch.setattr(system, "Redis", type("RedisFactory", (), {"from_url": lambda *_args, **_kwargs: BrokenRedis()}))
    monkeypatch.setattr(system, "Producer", BrokenProducer)

    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "dependencies": {
            "postgres": "unavailable",
            "mongodb": "unavailable",
            "redis": "unavailable",
            "kafka": "unavailable",
        },
    }
