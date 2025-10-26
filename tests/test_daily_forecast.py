from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def _chart_input():
    return {
        "system": "western",
        "date": "1990-08-18",
        "time": "14:32:00",
        "time_known": True,
        "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
    }


def test_daily_forecast_api_returns_focus_areas():
    response = client.post(
        "/v1/forecasts/daily",
        json={
            "chart_input": _chart_input(),
            "options": {
                "date": "1990-09-15",
                "profile_name": "Asha",
                "areas": ["career", "love"],
                "window_days": 2,
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["date"] == "1990-09-15"
    assert payload["meta"]["areas"] == ["career", "love"]
    assert payload["summary"].startswith("Asha,")
    assert payload["mood"] in {"vibrant", "motivated", "steady", "reflective", "restorative"}
    assert len(payload["focus_areas"]) == 2
    for focus in payload["focus_areas"]:
        assert focus["area"] in {"career", "love"}
        assert "headline" in focus
        assert "guidance" in focus
    assert isinstance(payload["events"], list)
    assert isinstance(payload["top_events"], list)


def test_vedic_daily_forecast_uses_sidereal_labels():
    response = client.post(
        "/v1/forecasts/daily",
        json={
            "chart_input": {
                "system": "vedic",
                "date": "1984-01-24",
                "time": "06:06:00",
                "time_known": True,
                "place": {"lat": 26.1833, "lon": 91.8001, "tz": "Asia/Kolkata"},
            },
            "options": {
                "date": "2025-10-29",
                "profile_name": "Ethan",
                "transit_bodies": ["Sun", "Moon"],
                "natal_targets": ["Sun", "Mars"],
                "window_days": 0,
            },
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["meta"]["zodiac"] == "sidereal"
    events = payload["events"]
    assert events, "expected sidereal events in daily forecast"

    def _event(name: str) -> dict:
        for evt in events:
            if evt["transit_body"] == name:
                return evt
        raise AssertionError(f"missing {name} transit event")

    sun_event = _event("Sun")
    assert sun_event["transit_sign"] == "Libra"
    assert "Sun (transit, sidereal) in Libra" in sun_event.get("note", "")

    moon_event = _event("Moon")
    assert moon_event["transit_sign"] == "Capricorn"
    assert "Sun (natal, sidereal) in Capricorn" in moon_event.get("note", "")
