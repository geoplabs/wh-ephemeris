import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def _names(seq):
    return [p["name"] for p in seq]


def test_karana_sequence_has_vishti_before_shakuni_on_2025_09_19_ist():
    response = client.post(
        "/v1/panchang/compute",
        json={
            "system": "vedic",
            "date": "2025-09-19",
            "place": {
                "lat": 17.385,
                "lon": 78.4867,
                "tz": "Asia/Kolkata",
                "query": "Hyderabad",
            },
            "options": {
                "ayanamsha": "lahiri",
                "include_muhurta": True,
                "lang": "en",
                "script": "latin",
            },
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    names = _names(payload["changes"]["karana_periods"])
    joined = ",".join(names)
    assert "Garaja" in joined
    assert "Vanija" in joined
    assert any(label.startswith("Vishti") for label in names)
    assert "Shakuni" in joined


def test_karana_periods_cover_window_without_gaps():
    response = client.post(
        "/v1/panchang/compute",
        json={
            "system": "vedic",
            "date": "2025-09-19",
            "place": {
                "lat": 28.6139,
                "lon": 77.2090,
                "tz": "Asia/Kolkata",
                "query": "New Delhi",
            },
            "options": {"ayanamsha": "lahiri"},
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    periods = payload["changes"]["karana_periods"]
    assert len(periods) >= 2
    for left, right in zip(periods, periods[1:]):
        assert left["end_ts"] <= right["start_ts"]
