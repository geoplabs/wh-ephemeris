from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime


ECLIPSE_SCAN_SAMPLES_2025 = [
    {
        "timestamp": "2025-01-13T12:00:00Z",
        "moon_lon": 108.105423693,
        "moon_lat": 4.783583978,
        "sun_lon": 293.55250857,
        "node_lon": 359.703870673,
    },
    {
        "timestamp": "2025-01-13T18:00:00Z",
        "moon_lon": 111.494476032,
        "moon_lat": 4.681467222,
        "sun_lon": 293.807098585,
        "node_lon": 359.655426578,
    },
    {
        "timestamp": "2025-01-14T00:00:00Z",
        "moon_lon": 114.865809476,
        "moon_lat": 4.56340871,
        "sun_lon": 294.061680752,
        "node_lon": 359.608054968,
    },
    {
        "timestamp": "2025-01-14T06:00:00Z",
        "moon_lon": 118.218703332,
        "moon_lat": 4.430086575,
        "sun_lon": 294.316255127,
        "node_lon": 359.56206758,
    },
    {
        "timestamp": "2025-01-29T06:00:00Z",
        "moon_lon": 306.030300394,
        "moon_lat": -4.057909665,
        "sun_lon": 309.577404611,
        "node_lon": 358.389496027,
    },
    {
        "timestamp": "2025-01-29T12:00:00Z",
        "moon_lon": 309.508161999,
        "moon_lat": -3.861085391,
        "sun_lon": 309.831447996,
        "node_lon": 358.35754343,
    },
    {
        "timestamp": "2025-01-29T18:00:00Z",
        "moon_lon": 313.001988694,
        "moon_lat": -3.648759907,
        "sun_lon": 310.085473815,
        "node_lon": 358.327665181,
    },
    {
        "timestamp": "2025-02-12T06:00:00Z",
        "moon_lon": 139.924751624,
        "moon_lat": 3.184485214,
        "sun_lon": 323.768944498,
        "node_lon": 357.689033737,
    },
    {
        "timestamp": "2025-02-12T12:00:00Z",
        "moon_lon": 143.102995704,
        "moon_lat": 2.952029244,
        "sun_lon": 324.021648115,
        "node_lon": 357.670406773,
    },
    {
        "timestamp": "2025-02-12T18:00:00Z",
        "moon_lon": 146.266142227,
        "moon_lat": 2.711417556,
        "sun_lon": 324.274326753,
        "node_lon": 357.653258891,
    },
    {
        "timestamp": "2025-02-13T00:00:00Z",
        "moon_lon": 149.414260944,
        "moon_lat": 2.463501634,
        "sun_lon": 324.526980593,
        "node_lon": 357.637618088,
    },
    {
        "timestamp": "2025-02-27T18:00:00Z",
        "moon_lon": 335.574525686,
        "moon_lat": -1.962742774,
        "sun_lon": 339.392594603,
        "node_lon": 357.416607924,
    },
    {
        "timestamp": "2025-02-28T00:00:00Z",
        "moon_lon": 339.220256891,
        "moon_lat": -1.647544105,
        "sun_lon": 339.643796068,
        "node_lon": 357.411290083,
    },
    {
        "timestamp": "2025-02-28T06:00:00Z",
        "moon_lon": 342.879649527,
        "moon_lat": -1.324271741,
        "sun_lon": 339.894966429,
        "node_lon": 357.407066612,
    },
    {
        "timestamp": "2025-03-13T18:00:00Z",
        "moon_lon": 167.423832308,
        "moon_lat": 0.917829342,
        "sun_lon": 353.406109808,
        "node_lon": 357.389449742,
    },
    {
        "timestamp": "2025-03-14T00:00:00Z",
        "moon_lon": 170.458252657,
        "moon_lat": 0.640044922,
        "sun_lon": 353.655311219,
        "node_lon": 357.388854235,
    },
    {
        "timestamp": "2025-03-14T06:00:00Z",
        "moon_lon": 173.48359057,
        "moon_lat": 0.361255002,
        "sun_lon": 353.904478252,
        "node_lon": 357.388484826,
    },
    {
        "timestamp": "2025-03-14T12:00:00Z",
        "moon_lon": 176.500282143,
        "moon_lat": 0.082222826,
        "sun_lon": 354.15361117,
        "node_lon": 357.388327927,
    },
    {
        "timestamp": "2025-03-14T18:00:00Z",
        "moon_lon": 179.508779211,
        "moon_lat": -0.196300472,
        "sun_lon": 354.402710236,
        "node_lon": 357.388363585,
    },
    {
        "timestamp": "2025-03-29T06:00:00Z",
        "moon_lon": 5.883303657,
        "moon_lat": 0.778876668,
        "sun_lon": 8.796974698,
        "node_lon": 357.426689014,
    },
    {
        "timestamp": "2025-03-29T12:00:00Z",
        "moon_lon": 9.652916749,
        "moon_lat": 1.121498394,
        "sun_lon": 9.044209722,
        "node_lon": 357.424493959,
    },
    {
        "timestamp": "2025-03-29T18:00:00Z",
        "moon_lon": 13.430631119,
        "moon_lat": 1.459834255,
        "sun_lon": 9.291409781,
        "node_lon": 357.421493951,
    },
    {
        "timestamp": "2025-04-12T12:00:00Z",
        "moon_lon": 197.23234991,
        "moon_lat": -1.783874518,
        "sun_lon": 22.828010026,
        "node_lon": 357.358650655,
    },
    {
        "timestamp": "2025-04-12T18:00:00Z",
        "moon_lon": 200.192291641,
        "moon_lat": -2.036062156,
        "sun_lon": 23.073054175,
        "node_lon": 357.348724914,
    },
    {
        "timestamp": "2025-04-13T00:00:00Z",
        "moon_lon": 203.150453568,
        "moon_lat": -2.282467792,
        "sun_lon": 23.318064092,
        "node_lon": 357.337232771,
    },
    {
        "timestamp": "2025-04-13T06:00:00Z",
        "moon_lon": 206.107355223,
        "moon_lat": -2.522481012,
        "sun_lon": 23.563040076,
        "node_lon": 357.324211608,
    },
    {
        "timestamp": "2025-04-13T12:00:00Z",
        "moon_lon": 209.063509614,
        "moon_lat": -2.755507532,
        "sun_lon": 23.807982421,
        "node_lon": 357.309737407,
    },
    {
        "timestamp": "2025-04-27T12:00:00Z",
        "moon_lon": 32.998513832,
        "moon_lat": 3.055000925,
        "sun_lon": 37.476452291,
        "node_lon": 356.823261928,
    },
    {
        "timestamp": "2025-04-27T18:00:00Z",
        "moon_lon": 36.814237283,
        "moon_lat": 3.325574934,
        "sun_lon": 37.719703447,
        "node_lon": 356.802785304,
    },
    {
        "timestamp": "2025-04-28T00:00:00Z",
        "moon_lon": 40.6312993,
        "moon_lat": 3.581187357,
        "sun_lon": 37.962924575,
        "node_lon": 356.781014967,
    },
    {
        "timestamp": "2025-05-12T06:00:00Z",
        "moon_lon": 226.790317132,
        "moon_lat": -3.942081594,
        "sun_lon": 51.771200475,
        "node_lon": 356.02595398,
    },
    {
        "timestamp": "2025-05-12T12:00:00Z",
        "moon_lon": 229.76339769,
        "moon_lat": -4.103084839,
        "sun_lon": 52.012536254,
        "node_lon": 355.985782451,
    },
    {
        "timestamp": "2025-05-12T18:00:00Z",
        "moon_lon": 232.741400118,
        "moon_lat": -4.253025891,
        "sun_lon": 52.253845916,
        "node_lon": 355.944288908,
    },
    {
        "timestamp": "2025-05-13T00:00:00Z",
        "moon_lon": 235.724722475,
        "moon_lat": -4.391473884,
        "sun_lon": 52.495129764,
        "node_lon": 355.901788492,
    },
    {
        "timestamp": "2025-05-13T06:00:00Z",
        "moon_lon": 238.713745222,
        "moon_lat": -4.518019759,
        "sun_lon": 52.736388096,
        "node_lon": 355.858570964,
    },
    {
        "timestamp": "2025-05-26T18:00:00Z",
        "moon_lon": 60.404635919,
        "moon_lat": 4.590797637,
        "sun_lon": 65.732547511,
        "node_lon": 354.715580658,
    },
    {
        "timestamp": "2025-05-27T00:00:00Z",
        "moon_lon": 64.182876118,
        "moon_lat": 4.716786682,
        "sun_lon": 65.972703039,
        "node_lon": 354.674943789,
    },
    {
        "timestamp": "2025-05-27T06:00:00Z",
        "moon_lon": 67.95361283,
        "moon_lat": 4.821884578,
        "sun_lon": 66.212839165,
        "node_lon": 354.633390383,
    },
    {
        "timestamp": "2025-05-27T12:00:00Z",
        "moon_lon": 71.714178108,
        "moon_lat": 4.905727254,
        "sun_lon": 66.452955499,
        "node_lon": 354.591147765,
    },
    {
        "timestamp": "2025-06-11T00:00:00Z",
        "moon_lon": 256.703635527,
        "moon_lat": -4.964035079,
        "sun_lon": 80.342357218,
        "node_lon": 353.148660435,
    },
    {
        "timestamp": "2025-06-11T06:00:00Z",
        "moon_lon": 259.765210955,
        "moon_lat": -4.986655352,
        "sun_lon": 80.581286538,
        "node_lon": 353.093261948,
    },
    {
        "timestamp": "2025-06-11T12:00:00Z",
        "moon_lon": 262.836939039,
        "moon_lat": -4.994858423,
        "sun_lon": 80.82020311,
        "node_lon": 353.037988453,
    },
    {
        "timestamp": "2025-06-11T18:00:00Z",
        "moon_lon": 265.918974127,
        "moon_lat": -4.988479528,
        "sun_lon": 81.059107219,
        "node_lon": 352.983052882,
    },
    {
        "timestamp": "2025-06-25T00:00:00Z",
        "moon_lon": 87.722858666,
        "moon_lat": 4.986348321,
        "sun_lon": 93.710489054,
        "node_lon": 351.684020653,
    },
    {
        "timestamp": "2025-06-25T06:00:00Z",
        "moon_lon": 91.379818421,
        "moon_lat": 4.942637502,
        "sun_lon": 93.949088512,
        "node_lon": 351.637429871,
    },
    {
        "timestamp": "2025-06-25T12:00:00Z",
        "moon_lon": 95.021696673,
        "moon_lat": 4.878931296,
        "sun_lon": 94.187682523,
        "node_lon": 351.590923236,
    },
    {
        "timestamp": "2025-06-25T18:00:00Z",
        "moon_lon": 98.646569538,
        "moon_lat": 4.795770438,
        "sun_lon": 94.426270726,
        "node_lon": 351.544899048,
    },
    {
        "timestamp": "2025-07-10T12:00:00Z",
        "moon_lon": 284.244870291,
        "moon_lat": -4.618514523,
        "sun_lon": 108.492005658,
        "node_lon": 350.195597262,
    },
    {
        "timestamp": "2025-07-10T18:00:00Z",
        "moon_lon": 287.438666214,
        "moon_lat": -4.496902303,
        "sun_lon": 108.730330736,
        "node_lon": 350.152127895,
    },
    {
        "timestamp": "2025-07-11T00:00:00Z",
        "moon_lon": 290.646253016,
        "moon_lat": -4.36048046,
        "sun_lon": 108.968658395,
        "node_lon": 350.110026323,
    },
    {
        "timestamp": "2025-07-11T06:00:00Z",
        "moon_lon": 293.867488005,
        "moon_lat": -4.209489589,
        "sun_lon": 109.206988935,
        "node_lon": 350.069588338,
    },
    {
        "timestamp": "2025-07-24T12:00:00Z",
        "moon_lon": 117.993407918,
        "moon_lat": 3.997914149,
        "sun_lon": 121.851458449,
        "node_lon": 349.230097895,
    },
    {
        "timestamp": "2025-07-24T18:00:00Z",
        "moon_lon": 121.455281291,
        "moon_lat": 3.797277442,
        "sun_lon": 122.090357379,
        "node_lon": 349.20161899,
    },
    {
        "timestamp": "2025-07-25T00:00:00Z",
        "moon_lon": 124.897942357,
        "moon_lat": 3.583750326,
        "sun_lon": 122.32926605,
        "node_lon": 349.174867996,
    },
    {
        "timestamp": "2025-07-25T06:00:00Z",
        "moon_lon": 128.320558828,
        "moon_lat": 3.358374245,
        "sun_lon": 122.568184265,
        "node_lon": 349.150013352,
    },
    {
        "timestamp": "2025-08-09T00:00:00Z",
        "moon_lon": 312.55995018,
        "moon_lat": -3.061712956,
        "sun_lon": 136.682437838,
        "node_lon": 348.576122858,
    },
    {
        "timestamp": "2025-08-09T06:00:00Z",
        "moon_lon": 315.920873867,
        "moon_lat": -2.809886642,
        "sun_lon": 136.922053369,
        "node_lon": 348.559897394,
    },
    {
        "timestamp": "2025-08-09T12:00:00Z",
        "moon_lon": 319.298054911,
        "moon_lat": -2.546856698,
        "sun_lon": 137.161686461,
        "node_lon": 348.545336831,
    },
    {
        "timestamp": "2025-08-09T18:00:00Z",
        "moon_lon": 322.690931111,
        "moon_lat": -2.273447334,
        "sun_lon": 137.401337507,
        "node_lon": 348.532542974,
    },
    {
        "timestamp": "2025-08-23T00:00:00Z",
        "moon_lon": 147.065409888,
        "moon_lat": 1.908808416,
        "sun_lon": 150.137991542,
        "node_lon": 348.32866854,
    },
    {
        "timestamp": "2025-08-23T06:00:00Z",
        "moon_lon": 150.324103866,
        "moon_lat": 1.627018117,
        "sun_lon": 150.379013429,
        "node_lon": 348.323500705,
    },
    {
        "timestamp": "2025-08-23T12:00:00Z",
        "moon_lon": 153.56580417,
        "moon_lat": 1.34131879,
        "sun_lon": 150.620059401,
        "node_lon": 348.319197534,
    },
    {
        "timestamp": "2025-08-23T18:00:00Z",
        "moon_lon": 156.790470679,
        "moon_lat": 1.052715826,
        "sun_lon": 150.861129375,
        "node_lon": 348.315740298,
    },
    {
        "timestamp": "2025-09-07T12:00:00Z",
        "moon_lon": 341.741352675,
        "moon_lat": -0.608193057,
        "sun_lon": 165.126693471,
        "node_lon": 348.334517464,
    },
    {
        "timestamp": "2025-09-07T18:00:00Z",
        "moon_lon": 345.287602038,
        "moon_lat": -0.281551662,
        "sun_lon": 165.369241747,
        "node_lon": 348.334200352,
    },
    {
        "timestamp": "2025-09-08T00:00:00Z",
        "moon_lon": 348.850573201,
        "moon_lat": 0.047752474,
        "sun_lon": 165.611819804,
        "node_lon": 348.334125737,
    },
    {
        "timestamp": "2025-09-21T12:00:00Z",
        "moon_lon": 175.010145091,
        "moon_lat": -0.610868367,
        "sun_lon": 178.763816394,
        "node_lon": 348.374666661,
    },
    {
        "timestamp": "2025-09-21T18:00:00Z",
        "moon_lon": 178.106453627,
        "moon_lat": -0.893548064,
        "sun_lon": 179.008357267,
        "node_lon": 348.373208268,
    },
    {
        "timestamp": "2025-09-22T00:00:00Z",
        "moon_lon": 181.191307048,
        "moon_lat": -1.172495398,
        "sun_lon": 179.252931976,
        "node_lon": 348.371208165,
    },
    {
        "timestamp": "2025-09-22T06:00:00Z",
        "moon_lon": 184.265025467,
        "moon_lat": -1.446953039,
        "sun_lon": 179.49754042,
        "node_lon": 348.36867329,
    },
    {
        "timestamp": "2025-10-06T18:00:00Z",
        "moon_lon": 8.087065188,
        "moon_lat": 1.779495467,
        "sun_lon": 193.739081778,
        "node_lon": 348.237167994,
    },
    {
        "timestamp": "2025-10-07T00:00:00Z",
        "moon_lon": 11.791390951,
        "moon_lat": 2.093924482,
        "sun_lon": 193.985549902,
        "node_lon": 348.229360772,
    },
    {
        "timestamp": "2025-10-07T06:00:00Z",
        "moon_lon": 15.510859153,
        "moon_lat": 2.400593154,
        "sun_lon": 194.232053662,
        "node_lon": 348.220277072,
    },
    {
        "timestamp": "2025-10-07T12:00:00Z",
        "moon_lon": 19.243369648,
        "moon_lat": 2.697922093,
        "sun_lon": 194.47859358,
        "node_lon": 348.210002317,
    },
    {
        "timestamp": "2025-10-21T00:00:00Z",
        "moon_lon": 202.167137416,
        "moon_lat": -2.910872022,
        "sun_lon": 207.849994346,
        "node_lon": 347.865892545,
    },
    {
        "timestamp": "2025-10-21T06:00:00Z",
        "moon_lon": 205.164109791,
        "moon_lat": -3.129470028,
        "sun_lon": 208.098661985,
        "node_lon": 347.843057394,
    },
    {
        "timestamp": "2025-10-21T12:00:00Z",
        "moon_lon": 208.155784926,
        "moon_lat": -3.3388897,
        "sun_lon": 208.347365126,
        "node_lon": 347.818291946,
    },
    {
        "timestamp": "2025-10-21T18:00:00Z",
        "moon_lon": 211.142561529,
        "moon_lat": -3.538637619,
        "sun_lon": 208.596103555,
        "node_lon": 347.791652209,
    },
    {
        "timestamp": "2025-10-22T00:00:00Z",
        "moon_lon": 214.124835954,
        "moon_lat": -3.72824779,
        "sun_lon": 208.844877054,
        "node_lon": 347.763213111,
    },
    {
        "timestamp": "2025-11-05T06:00:00Z",
        "moon_lon": 38.71416652,
        "moon_lat": 4.002145597,
        "sun_lon": 223.075753186,
        "node_lon": 346.827036215,
    },
    {
        "timestamp": "2025-11-05T12:00:00Z",
        "moon_lon": 42.537731404,
        "moon_lat": 4.201776972,
        "sun_lon": 223.326263627,
        "node_lon": 346.795237098,
    },
    {
        "timestamp": "2025-11-05T18:00:00Z",
        "moon_lon": 46.367899307,
        "moon_lat": 4.382741737,
        "sun_lon": 223.576806831,
        "node_lon": 346.762371731,
    },
    {
        "timestamp": "2025-11-19T18:00:00Z",
        "moon_lon": 231.880579588,
        "moon_lat": -4.589774356,
        "sun_lon": 237.660493056,
        "node_lon": 345.556822954,
    },
    {
        "timestamp": "2025-11-20T00:00:00Z",
        "moon_lon": 234.844526753,
        "moon_lat": -4.687127652,
        "sun_lon": 237.91288117,
        "node_lon": 345.500775577,
    },
    {
        "timestamp": "2025-11-20T06:00:00Z",
        "moon_lon": 237.809144596,
        "moon_lat": -4.771717719,
        "sun_lon": 238.165296374,
        "node_lon": 345.443465969,
    },
    {
        "timestamp": "2025-11-20T12:00:00Z",
        "moon_lon": 240.774770284,
        "moon_lat": -4.84332567,
        "sun_lon": 238.417738311,
        "node_lon": 345.385175164,
    },
    {
        "timestamp": "2025-11-20T18:00:00Z",
        "moon_lon": 243.741732915,
        "moon_lat": -4.901760544,
        "sun_lon": 238.670206618,
        "node_lon": 345.326193117,
    },
    {
        "timestamp": "2025-12-04T18:00:00Z",
        "moon_lon": 69.716405934,
        "moon_lat": 4.983710681,
        "sun_lon": 252.840886913,
        "node_lon": 343.769563592,
    },
    {
        "timestamp": "2025-12-05T00:00:00Z",
        "moon_lon": 73.550588746,
        "moon_lat": 4.995970692,
        "sun_lon": 253.094447099,
        "node_lon": 343.722486813,
    },
    {
        "timestamp": "2025-12-05T06:00:00Z",
        "moon_lon": 77.379021278,
        "moon_lat": 4.985736592,
        "sun_lon": 253.348026657,
        "node_lon": 343.67496086,
    },
    {
        "timestamp": "2025-12-19T18:00:00Z",
        "moon_lon": 264.542969634,
        "moon_lat": -4.882992293,
        "sun_lon": 268.088013508,
        "node_lon": 342.012405894,
    },
    {
        "timestamp": "2025-12-20T00:00:00Z",
        "moon_lon": 267.550883866,
        "moon_lat": -4.819482487,
        "sun_lon": 268.34262499,
        "node_lon": 341.954281005,
    },
    {
        "timestamp": "2025-12-20T06:00:00Z",
        "moon_lon": 270.565019509,
        "moon_lat": -4.742294931,
        "sun_lon": 268.597246274,
        "node_lon": 341.897101546,
    },
    {
        "timestamp": "2025-12-20T12:00:00Z",
        "moon_lon": 273.585606747,
        "moon_lat": -4.651544713,
        "sun_lon": 268.8518769,
        "node_lon": 341.84109203,
    },
]


def test_detect_eclipse_matches_nasa_catalog_for_2025() -> None:
    payload_json = json.dumps(ECLIPSE_SCAN_SAMPLES_2025)
    expected_dates = ["2025-03-14", "2025-03-29", "2025-09-07", "2025-09-21"]

    script = """
import json
from datetime import datetime
from api.services import advanced_transits

samples = json.loads({payload})
expected_dates = {expected}
collected = {{date: set() for date in expected_dates}}
unexpected = []

for sample in samples:
    dt = datetime.fromisoformat(sample["timestamp"].replace("Z", "+00:00"))
    info = advanced_transits.detect_eclipse(
        moon_lon=sample["moon_lon"],
        sun_lon=sample["sun_lon"],
        moon_lat=sample["moon_lat"],
        forecast_datetime=dt,
        node_lon=sample["node_lon"],
    )
    if not info:
        continue

    peak_iso = info.get("peak_datetime_utc")
    peak_dt = datetime.fromisoformat(peak_iso.replace("Z", "+00:00")).date() if peak_iso else dt.date()

    matched = None
    for target in expected_dates:
        target_dt = datetime.fromisoformat(target + "T00:00:00").date()
        if abs((peak_dt - target_dt).days) <= 1:
            matched = target
            break

    if matched is None:
        unexpected.append(peak_dt.isoformat())
        continue

    collected.setdefault(matched, set()).add(info["eclipse_category"])

print(json.dumps({{
    "detections": {{k: sorted(list(v)) for k, v in collected.items()}},
    "unexpected": unexpected,
}}))
""".format(payload=repr(payload_json), expected=repr(expected_dates))

    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )

    result = json.loads(completed.stdout)
    assert result["unexpected"] == []
    assert result["detections"] == {
        "2025-03-14": ["lunar"],
        "2025-03-29": ["solar"],
        "2025-09-07": ["lunar"],
        "2025-09-21": ["solar"],
    }
