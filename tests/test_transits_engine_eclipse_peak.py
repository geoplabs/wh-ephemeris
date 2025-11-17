import datetime as dt

import pytest

from api.services import transits_engine


@pytest.mark.parametrize(
    "peak_iso, forecast_date",
    [
        ("2025-03-14T06:00:00Z", "2025-03-13"),
        ("2026-03-03T12:30:00Z", "2026-03-02"),
    ],
)
def test_eclipse_uses_peak_datetime(monkeypatch, peak_iso, forecast_date):

    def fake_natal_positions(_chart_input):
        return {
            "Sun": {"lon": 0.0, "speed_lon": 0.0},
            "Moon": {"lon": 180.0, "speed_lon": 0.0},
        }

    def fake_positions(_dt, _system, _ayan):
        return {
            "Sun": {"lon": 0.0, "speed_lon": 0.0, "lat": 0.0},
            "Moon": {"lon": 180.0, "speed_lon": 0.0, "lat": 0.0},
            "TrueNode": {"lon": 0.0, "speed_lon": 0.0, "lat": 0.0},
        }

    monkeypatch.setattr(transits_engine, "_natal_positions", fake_natal_positions)
    monkeypatch.setattr(transits_engine, "_transit_positions", fake_positions)
    monkeypatch.setattr(transits_engine.advanced_transits, "detect_lunar_phase", lambda *a, **k: None)
    monkeypatch.setattr(transits_engine.advanced_transits, "detect_void_of_course_moon", lambda *a, **k: None)
    monkeypatch.setattr(transits_engine.advanced_transits, "detect_out_of_bounds_moon", lambda *a, **k: None)
    monkeypatch.setattr(transits_engine.advanced_transits, "detect_station", lambda *a, **k: None)
    monkeypatch.setattr(
        transits_engine.advanced_transits,
        "detect_retrograde",
        lambda *a, **k: None,
        raising=False,
    )
    monkeypatch.setattr(
        transits_engine.advanced_transits,
        "detect_sign_ingress",
        lambda *a, **k: None,
        raising=False,
    )
    monkeypatch.setattr(transits_engine.advanced_transits, "calculate_lunar_phase_score", lambda *a, **k: 0.0)

    def fake_detect_eclipse(*_args, **_kwargs):
        return {
            "has_eclipse": True,
            "eclipse_category": "lunar",
            "eclipse_type": "partial",
            "base_weight": 1.0,
            "description": "Lunar eclipse",
            "banner": "Lunar Eclipse",
            "tone_line": "",
            "impact_level": "high",
            "keywords": [],
            "peak_datetime_utc": peak_iso,
        }

    monkeypatch.setattr(transits_engine.advanced_transits, "detect_eclipse", fake_detect_eclipse)
    monkeypatch.setattr(transits_engine.advanced_transits, "calculate_eclipse_score", lambda *_: 1.5)

    chart_input = {
        "system": "western",
        "place": {"tz": "UTC"},
        "date": "2000-01-01",
        "time": "00:00:00",
        "time_known": True,
    }
    opts = {"from_date": forecast_date, "to_date": forecast_date, "step_days": 1}

    events = transits_engine.compute_transits(chart_input, opts)

    eclipse_events = [ev for ev in events if ev.get("event_type") == "eclipse"]
    assert len(eclipse_events) == 1

    eclipse_event = eclipse_events[0]
    timestamp = dt.datetime.fromisoformat(peak_iso.replace("Z", "+00:00"))
    peak_date = timestamp.date().isoformat()

    assert eclipse_event["date"] == peak_date
    assert eclipse_event.get("exact_hit_time_utc") == peak_iso
