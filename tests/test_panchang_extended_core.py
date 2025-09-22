import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def test_extended_nodes_present():
    r = client.get(
        "/v1/panchang/today",
        params={
            "lat": 19.076,
            "lon": 72.8777,
            "tz": "Asia/Kolkata",
            "ayanamsha": "lahiri",
        },
    )
    j = r.json()
    assert "calendars_extended" in j
    assert "ritu_extended" in j
    assert "muhurtas_extra" in j and "auspicious_extra" in j["muhurtas_extra"]
    assert "yoga_extended" in j and "anandadi" in j["yoga_extended"]
    assert "nivas_and_shool" in j
    assert "balam" in j
    assert "panchaka_and_lagna" in j
    assert isinstance(j.get("ritual_notes", []), list)


def test_dinmana_ratrimana_format():
    j = client.get(
        "/v1/panchang/today",
        params={
            "lat": 28.6139,
            "lon": 77.2090,
            "tz": "Asia/Kolkata",
        },
    ).json()
    re_time = __import__("re").compile(r"^\d{2}:\d{2}:\d{2}$")
    assert re_time.match(j["ritu_extended"]["dinmana"])
    assert re_time.match(j["ritu_extended"]["ratrimana"])


def test_calendars_has_jd_mjd_and_samvatsara():
    j = client.get(
        "/v1/panchang/today",
        params={
            "lat": 12.9716,
            "lon": 77.5946,
            "tz": "Asia/Kolkata",
        },
    ).json()
    ce = j["calendars_extended"]
    assert isinstance(ce["julian_day"], float)
    assert isinstance(ce["modified_julian_day"], float)
    assert isinstance(ce["vikram_samvat"], int)
    assert isinstance(ce["shaka_samvat"], int)


def test_muhurta_extra_non_empty():
    j = client.get(
        "/v1/panchang/today",
        params={
            "lat": 22.5726,
            "lon": 88.3639,
            "tz": "Asia/Kolkata",
        },
    ).json()
    assert len(j["muhurtas_extra"]["auspicious_extra"]) >= 1
    assert len(j["muhurtas_extra"]["inauspicious_extra"]) >= 1
