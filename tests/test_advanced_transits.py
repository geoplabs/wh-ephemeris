from datetime import datetime
import sys
import types


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
    module.CHIRON = 11
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

    sys.modules["swisseph"] = module


_install_fake_swisseph()

from api.services import advanced_transits


def _ts() -> datetime:
    """Helper timestamp for eclipse calculations."""

    return datetime(2024, 4, 8, 18, 0)


def test_detect_total_lunar_eclipse_marks_blood_moon():
    info = advanced_transits.detect_eclipse(
        moon_lon=0.0,
        sun_lon=180.0,
        moon_lat=0.1,
        forecast_datetime=_ts(),
    )

    assert info is not None
    assert info["eclipse_category"] == "lunar"
    assert info["eclipse_type"] == "total"
    assert "Blood Moon" in info.get("banner", "")
    assert "Blood Moon" in info.get("tone_line", "")
    assert "Blood Moon" in info.get("aliases", [])


def test_detect_penumbral_lunar_eclipse_classification():
    info = advanced_transits.detect_eclipse(
        moon_lon=0.0,
        sun_lon=180.0,
        moon_lat=1.1,
        forecast_datetime=_ts(),
    )

    assert info is not None
    assert info["eclipse_category"] == "lunar"
    assert info["eclipse_type"] == "penumbral"
    assert info["base_weight"] == 0.8
    assert "Penumbral" in info.get("banner", "")


def test_detect_partial_solar_eclipse_grazing():
    info = advanced_transits.detect_eclipse(
        moon_lon=0.0,
        sun_lon=0.0,
        moon_lat=1.4,
        forecast_datetime=_ts(),
    )

    assert info is not None
    assert info["eclipse_category"] == "solar"
    assert info["eclipse_type"] == "partial"
    assert info["base_weight"] == 1.1
    assert "Solar Eclipse" in info.get("banner", "")


def test_detect_eclipse_returns_none_when_latitude_too_high():
    info = advanced_transits.detect_eclipse(
        moon_lon=0.0,
        sun_lon=180.0,
        moon_lat=1.6,
        forecast_datetime=_ts(),
    )

    assert info is None
