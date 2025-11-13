import sys
import types
from datetime import datetime, timezone
from typing import Any, Dict

import pytest


def _install_fake_swisseph() -> None:
    if "swisseph" in sys.modules:
        return

    module = types.ModuleType("swisseph")
    module.version = "test"
    module.SUN = 0
    module.MOON = 1
    module.MERCURY = 2
    module.VENUS = 3
    module.MARS = 4
    module.JUPITER = 5
    module.SATURN = 6
    module.URANUS = 7
    module.NEPTUNE = 8
    module.PLUTO = 9
    module.TRUE_NODE = 10
    module.MEAN_NODE = 11
    module.CHIRON = 12
    module.SIDM_LAHIRI = 0
    module.SIDM_KRISHNAMURTI = 1
    module.SIDM_RAMAN = 2
    module.FLG_MOSEPH = 1
    module.FLG_SWIEPH = 2
    module.FLG_SPEED = 4
    module.FLG_SIDEREAL = 8
    module.GREG_CAL = 0

    def _return_zero(*_args, **_kwargs):
        return ([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 0)

    module.julday = lambda *_args, **_kwargs: 0.0
    module.calc_ut = _return_zero
    module.set_ephe_path = lambda *_args, **_kwargs: None
    module.set_sid_mode = lambda *_args, **_kwargs: None
    module.set_topo = lambda *_args, **_kwargs: None

    def _houses(*_args, **_kwargs):
        cusps = [i * 30.0 for i in range(1, 13)]
        ascmc = (0.0, 90.0, 180.0, 270.0)
        return cusps, ascmc

    module.houses = _houses

    sys.modules["swisseph"] = module


_install_fake_swisseph()

import api.services.yearly_western as yearly_western
from api.services.forecast_builders import yearly_payload


@pytest.fixture(autouse=True)
def _stub_compute_transits(monkeypatch):
    def fake_compute(_chart_input, opts):
        return [
            {
                "date": opts["from_date"],
                "transit_body": "Sun",
                "natal_body": "Sun",
                "aspect": "conjunction",
                "orb": 0.5,
                "event_type": "transit",
                "note": "stub",
            }
        ]

    monkeypatch.setattr(yearly_western, "compute_transits", fake_compute)
    yearly_western._MONTH_CACHE.clear()
    yield
    yearly_western._MONTH_CACHE.clear()


def _chart_input_western():
    return {
        "system": "western",
        "zodiac": "tropical",
        "house_system": "WholeSign",
        "date": "1990-05-15",
        "time": "14:30:00",
        "time_known": True,
        "place": {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"},
    }


def _chart_input_vedic():
    data = _chart_input_western()
    data["system"] = "vedic"
    data["zodiac"] = "sidereal"
    data["house_system"] = "WholeSign"
    return data


def _options_full():
    return {
        "year": 2025,
        "timezone": "Asia/Kolkata",
        "transits": {
            "bodies": [
                "Sun",
                "Moon",
                "Mercury",
                "Venus",
                "Mars",
                "Jupiter",
                "Saturn",
            ],
            "bodies_extras": ["Ceres"],
            "include_ingresses": True,
            "include_retrogrades": True,
            "include_stations": True,
            "include_lunations": True,
            "include_eclipses": True,
        },
        "aspects": {
            "types": [
                "conjunction",
                "opposition",
                "square",
                "trine",
                "sextile",
                "quincunx",
            ],
            "orb": {"default": 3.0, "Sun": 4.0, "Moon": 5.0, "outer": 2.0},
            "angle_orbs": {"ASC": 3.0, "MC": 3.0, "DSC": 3.0, "IC": 3.0},
            "pair_overrides": {"Sun|Saturn": 3.5},
            "to_angles": ["ASC", "MC", "DSC", "IC"],
            "applying_only": False,
        },
        "detection": {
            "scan_step_hours": 6,
            "refine_exact": True,
            "min_strength": 0.2,
            "group_retrograde_campaigns": True,
        },
        "scoring": {
            "angle_bonus": 0.3,
            "progressed_bonus": 0.4,
            "eclipse_bonus": 0.6,
            "applying_bonus": 0.08,
            "separating_penalty": -0.04,
        },
        "outputs": {
            "sections": ["themes", "timeline", "windows", "cautions", "summary"],
            "raw_events": True,
            "debug": False,
        },
        "filters": {"exclude_void_moon_windows": True, "min_orb_strength": 0.1},
        "progressions": {"secondary": True, "solar_arc": True},
        "solar_return": {"enabled": True},
        "houses": {"track_entries": True, "track_exits": True},
        "versioning": {"ephemeris_version": "se-2.10", "algo_version": "yh-2025.11"},
    }


def test_western_pipeline_enables_extended_sections():
    data = yearly_payload(_chart_input_western(), _options_full())

    assert data["meta"]["western_enabled"] is True
    assert "timeline" in data and data["timeline"]
    assert "themes" in data
    assert all("summary" in item for item in data["themes"])

    # ensure canonical ids present on timeline entries
    assert all("event_id" in item for item in data["timeline"])

    # months remain compatible with legacy response shape
    assert data["months"], "months payload should not be empty"
    assert len(data["top_events"]) <= 20

    # timezone resolution metadata should include requested tz
    assert data["meta"]["timezone"]["input"] == "Asia/Kolkata"


def test_non_western_falls_back_to_legacy_pipeline():
    options = {"year": 2025}
    data = yearly_payload(_chart_input_vedic(), options)

    assert "timeline" not in data
    assert "themes" not in data
    assert set(data.keys()) == {"months", "top_events"}


def test_detection_step_hours_passed(monkeypatch):
    captured: Dict[str, Any] = {}

    def fake_compute(chart_input, opts):
        captured.update(opts)
        return []

    monkeypatch.setattr(yearly_western, "compute_transits", fake_compute)
    yearly_western._MONTH_CACHE.clear()

    options = _options_full()
    options["detection"]["scan_step_hours"] = 3
    yearly_payload(_chart_input_western(), options)

    assert captured["step_hours"] == 3
    assert captured["step_days"] == 1


def test_timezone_fallback_warning():
    options = _options_full()
    options.setdefault("time", {})["timezone"] = "Invalid/Zone"
    options["time"]["tz_resolution"] = "fallback"

    data = yearly_payload(_chart_input_western(), options)

    assert "timezone_fallback" in data["meta"]["warnings"]
    assert data["meta"]["timezone"]["resolved"] == "UTC"


def test_month_index_preserves_highest_scoring_events():
    chart = _chart_input_western()
    config = yearly_western._build_config(chart, _options_full())
    engine = yearly_western._WesternYearlyEngine(chart, config)
    engine.config.outputs.max_events_per_month = 2

    def make_event(day: int, score: float) -> yearly_western._Event:
        ev = yearly_western._Event(
            stream="transit",
            type="test",
            timestamp=datetime(2025, 1, day, tzinfo=timezone.utc),
            transit_body="Sun",
            natal_body="Moon",
            aspect="conjunction",
            orb=0.1,
            orb_limit=1.0,
            score=score,
            applying=True,
            tags=set(),
            info={
                "note": "test note",
                "transit_sign": "Capricorn",
                "natal_sign": "Capricorn",
                "zodiac": "tropical",
                "exact_hit_time_utc": None,
                "transit_motion": "direct",
                "natal_point_type": "planet",
            },
        )
        ev.event_id = f"ev-{day}"
        ev.canonical = {}
        return ev

    events = [make_event(1, 0.7), make_event(15, 0.95), make_event(20, 0.9)]
    months, _ = engine._build_month_index(events)

    assert months["2025-01"] == [
        {
            "date": "2025-01-15",
            "transit_body": "Sun",
            "natal_body": "Moon",
            "aspect": "conjunction",
            "orb": 0.1,
            "score": 0.95,
            "note": "test note",
            "transit_sign": "Capricorn",
            "natal_sign": "Capricorn",
            "zodiac": "tropical",
            "exact_hit_time_utc": None,
            "transit_motion": "direct",
            "natal_point_type": "planet",
            "event_id": "ev-15",
        },
        {
            "date": "2025-01-20",
            "transit_body": "Sun",
            "natal_body": "Moon",
            "aspect": "conjunction",
            "orb": 0.1,
            "score": 0.9,
            "note": "test note",
            "transit_sign": "Capricorn",
            "natal_sign": "Capricorn",
            "zodiac": "tropical",
            "exact_hit_time_utc": None,
            "transit_motion": "direct",
            "natal_point_type": "planet",
            "event_id": "ev-20",
        },
    ]
