"""Regression tests for precise orb calculations in the yearly pipeline."""

import pytest

pytest.importorskip("swisseph")

from api.services.transits_engine import compute_transits


def _chart_input() -> dict:
    return {
        "system": "western",
        "zodiac": "tropical",
        "house_system": "WholeSign",
        "date": "1990-05-15",
        "time": "14:30:00",
        "time_known": True,
        "place": {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"},
    }


def test_moon_angle_opposition_has_precise_orb():
    chart_input = _chart_input()
    opts = {
        "from_date": "2025-01-05",
        "to_date": "2025-01-05",
        "step_days": 1,
        "transit_bodies": ["Moon"],
        "aspects": {"types": ["opposition"], "orb_deg": 5.0},
    }

    events = compute_transits(chart_input, opts)
    moon_events = [
        e
        for e in events
        if e["transit_body"] == "Moon"
        and e["natal_body"] == "Ascendant"
        and e["aspect"] == "opposition"
    ]

    assert moon_events, "Expected at least one Moon-Asc opposition"
    precise = moon_events[0]
    # With the precision fix in place, the orb should collapse near zero when
    # an exact hit time is available.
    assert precise["orb"] <= 0.05, precise
    assert precise.get("exact_hit_time_utc"), "Exact hit time should be present"
