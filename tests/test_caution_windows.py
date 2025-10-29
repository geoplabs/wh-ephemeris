from __future__ import annotations

from src.content.caution_windows import compute_caution_windows


def _base_event(**overrides):
    event = {
        "date": "2025-10-29",
        "transit_body": "Moon",
        "natal_body": "Mars",
        "aspect": "square",
        "orb": 1.5,
        "phase": "applying",
        "transit_sign": "Cancer",
        "natal_sign": "Aries",
        "exact_hit_time_utc": "2025-10-29T08:30:00Z",
        "natal_point_type": "planet",
        "transit_motion": "direct",
    }
    event.update(overrides)
    return event


def test_support_dominant_stack_outputs_support_window():
    events = [
        _base_event(
            transit_body="Mercury",
            natal_body="Chiron",
            aspect="trine",
            orb=0.04,
            phase="separating",
            exact_hit_time_utc="2025-10-29T06:00:00Z",
        )
    ]

    windows = compute_caution_windows(events)

    assert len(windows) == 1
    window = windows[0]
    assert window["severity"] == "Insight"
    assert window["score"] < 0
    assert "inner work" in window["note"].lower()


def test_friction_with_support_offsets_but_remains_caution():
    events = [
        _base_event(),
        _base_event(
            transit_body="Mercury",
            natal_body="Chiron",
            aspect="trine",
            orb=0.04,
            phase="separating",
            exact_hit_time_utc="2025-10-29T06:00:00Z",
        ),
    ]

    windows = compute_caution_windows(events)

    assert len(windows) == 1
    window = windows[0]
    assert window["severity"] == "Caution"
    assert window["score"] > 0
    assert "support" in window["pro_notes"].lower()
    assert len(window["drivers"]) == 2
    weights = [driver["weight"] for driver in window["drivers"]]
    assert weights[0] > 0
    assert weights[1] < 0


def test_slow_only_background_produces_no_window():
    events = [
        _base_event(
            transit_body="Saturn",
            natal_body="Sun",
            aspect="square",
            orb=1.0,
            exact_hit_time_utc="2025-10-29T03:00:00Z",
        )
    ]

    assert compute_caution_windows(events) == []


def test_phase_scaling_applies_to_separating_events():
    applying_event = _base_event(orb=1.0, phase="applying")
    separating_event = _base_event(
        orb=1.0,
        phase="separating",
        exact_hit_time_utc="2025-10-29T09:30:00Z",
    )

    windows = compute_caution_windows([applying_event, separating_event])
    assert len(windows) == 1
    drivers = windows[0]["drivers"]
    assert len(drivers) == 2
    # Applying event should carry more weight than the separating one.
    assert drivers[0]["weight"] > abs(drivers[1]["weight"]) * 1.2


def test_angle_square_requires_caution_even_with_support():
    friction = _base_event(
        transit_body="Mars",
        natal_body="ASC",
        natal_point_type="angle",
        aspect="square",
        orb=0.8,
        phase="applying",
        exact_hit_time_utc="2025-10-29T05:00:00Z",
    )
    supportive_one = _base_event(
        transit_body="Venus",
        natal_body="Moon",
        aspect="trine",
        orb=0.2,
        phase="applying",
        exact_hit_time_utc="2025-10-29T05:20:00Z",
    )
    supportive_two = _base_event(
        transit_body="Jupiter",
        natal_body="Sun",
        aspect="trine",
        orb=0.1,
        phase="applying",
        exact_hit_time_utc="2025-10-29T05:40:00Z",
    )

    windows = compute_caution_windows([friction, supportive_one, supportive_two])

    assert len(windows) == 1
    window = windows[0]
    assert window["severity"] == "Caution"
    assert "tension with support" in window["note"].lower()


def test_wide_moon_orb_downgrades_severity():
    tight = _base_event(orb=1.2)
    wide = _base_event(orb=3.4)

    caution_window = compute_caution_windows([tight])
    downgraded_window = compute_caution_windows([wide])

    assert caution_window and caution_window[0]["severity"] in {"Caution", "High Caution"}
    assert downgraded_window and downgraded_window[0]["severity"] == "Gentle Note"
