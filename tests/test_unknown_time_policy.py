import os
os.environ.setdefault("EPHEMERIS_BACKEND", "moseph")
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_unknown_time_solar_whole_sign():
    payload = {"system":"western","date":"1990-08-18","time":"14:32:00","time_known":False,
               "place":{"lat":17.385,"lon":78.4867,"tz":"Asia/Kolkata"}}
    r = client.post("/v1/charts/compute", json=payload)
    j = r.json()
    assert j["angles"] is None
    assert j["houses"] is None
    assert j["meta"]["warnings"] and "solar whole-sign" in j["meta"]["warnings"][0].lower()
    # bodies still have house numbers assigned via solar whole-sign
    assert all(("house" in b and 1 <= b["house"] <= 12) for b in j["bodies"])
