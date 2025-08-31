import os
os.environ.setdefault("EPHEMERIS_BACKEND", "moseph")
import time
from fastapi.testclient import TestClient
from api.app import app

def test_perf_10_calls_under_1s():
    client = TestClient(app)
    payload = {"system":"western","date":"1990-08-18","time":"14:32:00","time_known":True,
               "place":{"lat":17.385,"lon":78.4867,"tz":"Asia/Kolkata"}}
    t0 = time.time()
    for _ in range(10):
        r = client.post("/v1/charts/compute", json=payload)
        assert r.status_code == 200
    assert time.time() - t0 < 1.0
