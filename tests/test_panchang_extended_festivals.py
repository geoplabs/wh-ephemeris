import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def test_observances_extended_when_enabled(monkeypatch):
    monkeypatch.setenv("PANCHANG_EXT_FESTIVALS_ENABLED", "true")
    response = client.get(
        "/v1/panchang/today",
        params={"lat": 19.076, "lon": 72.8777, "tz": "Asia/Kolkata"},
    )
    j = response.json()
    assert "observances" in j and isinstance(j["observances"], list)
