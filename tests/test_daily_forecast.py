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
