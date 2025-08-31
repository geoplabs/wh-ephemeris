from fastapi.testclient import TestClient
from api.app import app
import os

from fastapi.testclient import TestClient
from api.app import app


def test_reject_without_key(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post("/v1/charts/compute", json={})
    assert r.status_code == 401


def test_reject_with_invalid_key(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "valid123")
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post(
            "/v1/charts/compute",
            headers={"Authorization": "Bearer nope"},
            json={},
        )
    assert r.status_code == 403


def test_allow_with_valid_key(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "valid123")
    payload = {
        "system": "western",
        "date": "1990-08-18",
        "time": "14:32:00",
        "time_known": True,
        "place": {"lat": 17.3, "lon": 78.4, "tz": "Asia/Kolkata"},
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post(
            "/v1/charts/compute",
            headers={"Authorization": "Bearer valid123"},
            json=payload,
        )
    assert r.status_code == 200


def test_rate_limit(monkeypatch):
    from api.middleware.ratelimit import _counters

    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    _counters.clear()
    with TestClient(app, raise_server_exceptions=False) as client:
        for i in range(3):
            r = client.post(
                "/v1/charts/compute",
                json={
                    "system": "western",
                    "date": "1990-08-18",
                    "time": "14:32:00",
                    "time_known": True,
                    "place": {"lat": 17.3, "lon": 78.4, "tz": "Asia/Kolkata"},
                },
            )
            if i < 2:
                assert r.status_code == 200
    assert r.status_code == 429


def test_product_whitelist(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    payload = {
        "product": "unknown",
        "chart_input": {
            "system": "western",
            "date": "1990-08-18",
            "time": "14:32:00",
            "time_known": True,
            "place": {"lat": 17.3, "lon": 78.4, "tz": "Asia/Kolkata"},
        },
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post("/v1/reports", json=payload)
    assert r.status_code == 400
