from datetime import UTC, datetime
import sys
import types

if "swisseph" not in sys.modules:
    swe_stub = types.SimpleNamespace(
        version="stub",
        SUN=0,
        MOON=1,
        MERCURY=2,
        VENUS=3,
        MARS=4,
        JUPITER=5,
        SATURN=6,
        URANUS=7,
        NEPTUNE=8,
        PLUTO=9,
        TRUE_NODE=10,
        CHIRON=11,
        SIDM_LAHIRI=0,
        SIDM_KRISHNAMURTI=1,
        SIDM_RAMAN=2,
        FLG_MOSEPH=0,
        FLG_SWIEPH=1,
        FLG_SPEED=2,
        FLG_SIDEREAL=4,
        GREG_CAL=0,
        CALC_RISE=0,
        CALC_SET=1,
        BIT_DISC_CENTER=0,
        Error=RuntimeError,
    )

    def _dummy_calc(*_args, **_kwargs):
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 0

    swe_stub.calc_ut = _dummy_calc
    swe_stub.julday = lambda *_args, **_kwargs: 0.0
    swe_stub.set_ephe_path = lambda *_args, **_kwargs: None
    swe_stub.set_sid_mode = lambda *_args, **_kwargs: None
    swe_stub.rise_trans = lambda *_args, **_kwargs: (0, [0.0, 0.0])
    swe_stub.houses = lambda *_args, **_kwargs: ([0.0] * 12, [0.0, 0.0, 0.0])
    swe_stub.set_topo = lambda *_args, **_kwargs: None
    sys.modules["swisseph"] = swe_stub

from api.services.yearly_western import _WesternYearlyEngine, _build_config


_DEF_OPTIONS = {
    "year": 2025,
    "timezone": "UTC",
    "detection": {"scan_step_hours": 24, "refine_exact": False},
    "filters": {"min_orb_strength": 0.0},
    "outputs": {"raw_events": False},
    "aspects": {"types": ["conjunction"], "orb": {"default": 3.0}},
}


def _chart_input() -> dict:
    return {
        "system": "western",
        "zodiac": "tropical",
        "house_system": "WholeSign",
        "date": "1990-01-01",
        "time": "12:00:00",
        "time_known": True,
        "place": {"lat": 0.0, "lon": 0.0, "tz": "UTC"},
    }


def _engine() -> _WesternYearlyEngine:
    chart_input = _chart_input()
    config = _build_config(chart_input, dict(_DEF_OPTIONS))
    engine = _WesternYearlyEngine(chart_input, config)
    # Prevent natal lookups from touching Swiss Ephemeris during the tests.
    engine._natal_cache = {"Chiron": {"lon": 10.0, "speed_lon": 0.0}}
    return engine


def test_transit_removed_when_precise_orb_exceeds_limit():
    engine = _engine()
    dt_key = datetime(2025, 10, 22, 12, tzinfo=UTC).isoformat()
    engine._precise_position_cache[dt_key] = {
        "Neptune": {"lon": 210.0, "speed_lon": 0.0},
    }
    raw_event = {
        "date": "2025-10-22",
        "transit_body": "Neptune",
        "natal_body": "Chiron",
        "aspect": "conjunction",
        "orb": 0.05,
        "applying": True,
        "phase": "applying",
        "transit_motion": "direct",
        "event_type": "transit",
        "note": "stale",
        "zodiac": "tropical",
    }

    event = engine._transform_transit(raw_event)

    assert event is None, "Event should be dropped once precise orb exceeds the limit"


def test_precise_orb_updates_note_and_tags():
    engine = _engine()
    # Natal position for Chiron near 0° Aries.
    engine._natal_cache["Chiron"] = {"lon": 0.6, "speed_lon": 0.0}
    dt_key = datetime(2025, 3, 30, 12, tzinfo=UTC).isoformat()
    engine._precise_position_cache[dt_key] = {
        "Neptune": {"lon": 359.8, "speed_lon": -0.5},
    }
    raw_event = {
        "date": "2025-03-30",
        "transit_body": "Neptune",
        "natal_body": "Chiron",
        "aspect": "conjunction",
        "orb": 0.3,
        "applying": False,
        "phase": "separating",
        "transit_motion": "direct",
        "event_type": "transit",
        "note": "stale",
        "zodiac": "tropical",
    }

    event = engine._transform_transit(raw_event)
    assert event is not None, "Event should remain once the precise geometry is within orb"

    bucket = event.for_month_bucket()
    phase_label = "Applying" if event.applying else "Separating"
    assert phase_label in event.info["note"]
    assert f"{event.orb:.2f}°" in event.info["note"]
    assert bucket["transit_motion"] == "retrograde"
    assert bucket["note"].endswith("[retrograde]")
    assert event.info["transit_sign"] == "Pisces"
    assert event.info["natal_sign"] == "Aries"
