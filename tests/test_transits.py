from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def _chart_input(time_known=True):
    return {"system":"western","date":"1990-08-18","time":"14:32:00","time_known":time_known,
            "place":{"lat":17.385,"lon":78.4867,"tz":"Asia/Kolkata"}}

def test_transits_moon_hits_asc_or_sun():
    # include Moon so we surely get some events in a short window
    payload = {
        "chart_input": _chart_input(time_known=True),
        "options": {
            "from_date": "1990-09-01",
            "to_date":   "1990-09-30",
            "step_days": 1,
            "transit_bodies": ["Moon"],
            "natal_targets": ["Ascendant","Sun"],
            "aspects": {"types":["conjunction","square","trine","sextile","opposition"], "orb_deg": 3.0}
        }
    }
    r = client.post("/v1/transits/compute", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "events" in data
    # expect at least some events in a month with Moon scanning quickly
    assert len(data["events"]) >= 3
    evt = data["events"][0]
    for k in ["date","transit_body","natal_body","aspect","orb","score"]:
        assert k in evt


def test_vedic_transit_sun_uses_sidereal_frame():
    payload = {
        "chart_input": {
            "system": "vedic",
            "date": "1984-01-24",
            "time": "06:06:00",
            "time_known": True,
            "place": {"lat": 26.1833, "lon": 91.8001, "tz": "Asia/Kolkata"},
        },
        "options": {
            "from_date": "2025-10-29",
            "to_date": "2025-10-29",
            "step_days": 1,
            "transit_bodies": ["Sun"],
            "natal_targets": ["Mars"],
            "aspects": {"types": ["conjunction"], "orb_deg": 3.0},
        },
    }
    response = client.post("/v1/transits/compute", json=payload)
    assert response.status_code == 200, response.text
    events = response.json().get("events", [])
    assert events, "expected at least one Sun transit event"
    event = events[0]
    assert event["transit_body"] == "Sun"
    assert event["natal_body"] == "Mars"
    assert event["transit_sign"] == "Libra"
    assert event["natal_sign"] == "Libra"
    assert event.get("zodiac") == "sidereal"
    note = event.get("note") or ""
    assert "Sun (transit, sidereal) in Libra" in note
    assert "Mars (natal, sidereal) in Libra" in note
