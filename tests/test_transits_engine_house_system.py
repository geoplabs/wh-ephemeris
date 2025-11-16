import sys
import types

import pytest

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
        Error=RuntimeError,
    )

    swe_stub.calc_ut = lambda *_args, **_kwargs: ([0.0] * 6, 0)
    swe_stub.julday = lambda *_args, **_kwargs: 0.0
    swe_stub.set_ephe_path = lambda *_args, **_kwargs: None
    swe_stub.set_sid_mode = lambda *_args, **_kwargs: None
    swe_stub.rise_trans = lambda *_args, **_kwargs: (0, [0.0, 0.0])
    swe_stub.houses = lambda *_args, **_kwargs: ([0.0] * 12, [0.0, 0.0, 0.0])
    swe_stub.set_topo = lambda *_args, **_kwargs: None

    sys.modules["swisseph"] = swe_stub

from api.services import transits_engine as te


class DummyEphem:
    @staticmethod
    def to_jd_utc(*_args, **_kwargs):
        return 0.0

    @staticmethod
    def positions_ecliptic(*_args, **_kwargs):
        return {"Sun": {"lon": 0.0, "speed_lon": 0.0}}


def _chart_input(**overrides):
    data = {
        "system": "western",
        "zodiac": "tropical",
        "date": "1990-01-01",
        "time": "12:00:00",
        "time_known": True,
        "place": {"lat": 0.0, "lon": 0.0, "tz": "UTC"},
    }
    data.update(overrides)
    return data


def _install_stubs(monkeypatch):
    dummy_ephem = DummyEphem()
    monkeypatch.setattr(te, "ephem", dummy_ephem, raising=False)


class _HouseRecorder:
    def __init__(self):
        self.called_with = None

    def houses(self, *_args, **_kwargs):
        if _args:
            self.called_with = _args[-1]
        else:
            self.called_with = _kwargs.get("system")
        return {"asc": 0.0, "mc": 90.0, "cusps": [i * 30.0 for i in range(12)]}


def test_natal_positions_use_whole_sign_when_requested(monkeypatch):
    _install_stubs(monkeypatch)
    recorder = _HouseRecorder()
    monkeypatch.setattr(te, "houses_svc", recorder, raising=False)

    chart_input = _chart_input(house_system="WholeSign")

    te._natal_positions(chart_input)

    assert recorder.called_with == "whole_sign"


def test_natal_positions_fall_back_to_placidus(monkeypatch):
    _install_stubs(monkeypatch)
    recorder = _HouseRecorder()
    monkeypatch.setattr(te, "houses_svc", recorder, raising=False)

    chart_input = _chart_input()

    te._natal_positions(chart_input)

    assert recorder.called_with == "placidus"


def test_natal_positions_honour_option_house_system(monkeypatch):
    _install_stubs(monkeypatch)
    recorder = _HouseRecorder()
    monkeypatch.setattr(te, "houses_svc", recorder, raising=False)

    chart_input = _chart_input()
    chart_input.setdefault("options", {})["house_system"] = "Placidus"

    te._natal_positions(chart_input)

    assert recorder.called_with == "placidus"


def test_vedic_defaults_to_whole_sign(monkeypatch):
    _install_stubs(monkeypatch)
    recorder = _HouseRecorder()
    monkeypatch.setattr(te, "houses_svc", recorder, raising=False)

    chart_input = _chart_input(system="vedic", zodiac="sidereal")
    chart_input.pop("house_system", None)
    chart_input.setdefault("options", {}).pop("house_system", None)

    te._natal_positions(chart_input)

    assert recorder.called_with == "whole_sign"
