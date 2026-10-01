import random
from datetime import datetime, timezone
from uuid import UUID

import jwt
import pytest

from backend.app.schemas.telemetry import TelemetryEvent
from backend.app.security.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.services.idle_cost import calculate_idle_cost
from simulator.main import make_event


def test_simulator_emits_valid_synthetic_telemetry():
    event = make_event(71, 12, random.Random(7), out_of_order=True)
    assert event.vehicle_id == "FG-000000071"
    assert isinstance(event.event_id, UUID)
    assert event.timestamp.tzinfo == timezone.utc
    assert event.sequence_number == 12


def test_event_contract_rejects_out_of_range_location():
    values = make_event(1, 0, random.Random(1)).model_dump()
    values["latitude"] = 91
    with pytest.raises(ValueError):
        TelemetryEvent(**values)


def test_event_contract_rejects_naive_timestamp():
    values = make_event(1, 0, random.Random(1)).model_dump()
    values["timestamp"] = datetime(2026, 1, 1)
    with pytest.raises(ValueError):
        TelemetryEvent(**values)


def test_event_contract_rejects_unexpected_fields():
    values = make_event(1, 0, random.Random(1)).model_dump()
    values["driver_name"] = "private data is not part of this synthetic signal"
    with pytest.raises(ValueError):
        TelemetryEvent(**values)


def test_idle_cost_is_deterministic_and_explainable():
    impact = calculate_idle_cost(300, 2.4)
    assert str(impact.fuel_wasted_litres) == "0.200"
    assert str(impact.cost) == "0.30"
    assert "2.40 L/h × 300 s ÷ 3600" in impact.calculation


def test_idle_cost_rejects_negative_inputs():
    with pytest.raises(ValueError):
        calculate_idle_cost(-1, 2.4)


def test_password_hashing_and_jwt_claims():
    password = "synthetic-demo-secret"
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)
    key = "a" * 48
    token = create_access_token("user-1", "manager@example.test", "fleet-1", "FLEET_MANAGER", key)
    claims = jwt.decode(token, key, algorithms=["HS256"])
    assert claims["role"] == "FLEET_MANAGER"
    assert claims["fleet_id"] == "fleet-1"
