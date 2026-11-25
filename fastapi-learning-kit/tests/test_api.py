from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from telemetry_api.main import app

PAYLOAD = {"device": "CHW01", "temperature_c": 7.25,
           "observed_at": "2026-11-25T17:00:00+08:00"}


@pytest.fixture
def client():
    # Context manager runs lifespan (startup and shutdown).
    with TestClient(app) as session:
        yield session


def test_create_and_read(client):
    created = client.post("/v1/readings", json=PAYLOAD)
    assert created.status_code == 201
    row = created.json()
    assert set(row) == set(PAYLOAD) | {"id"}
    assert row["observed_at"] == "2026-11-25T09:00:00Z"
    assert client.get(created.headers["Location"]).json() == row


def test_list_filter_pagination(client):
    client.post("/v1/readings", json=PAYLOAD)
    client.post("/v1/readings", json=PAYLOAD | {"device": "CHW02"})
    assert [r["device"] for r in client.get("/v1/readings?limit=1&offset=1").json()["items"]] == ["CHW02"]
    assert len(client.get("/v1/readings?device=CHW01").json()["items"]) == 1
    assert client.get("/v1/readings?limit=101").status_code == 422


@pytest.mark.parametrize("invalid", [{"temperature_c": "7.25"}, {"temperature_c": 201},
    {"observed_at": "2026-11-25T09:00:00"}, {"unexpected": True}, {"device": "bad device"}])
def test_reject_invalid_payload(client, invalid):
    assert client.post("/v1/readings", json=PAYLOAD | invalid).status_code == 422
    assert client.get("/v1/readings").json()["items"] == []


def test_status_and_openapi(client):
    assert client.get("/health/live").json() == {"status": "live"}
    assert client.get("/health/ready").json() == {"status": "ready"}
    assert client.get("/v1/readings/not-uuid").status_code == 422
    assert client.get(f"/v1/readings/{uuid4()}").status_code == 404
    schema = client.get("/openapi.json").json()
    assert "201" in schema["paths"]["/v1/readings"]["post"]["responses"]
