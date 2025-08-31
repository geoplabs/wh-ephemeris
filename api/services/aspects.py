
MAJOR = {
    "conjunction": 0,
    "opposition": 180,
    "square": 90,
    "trine": 120,
    "sextile": 60,
}


def _angle_diff(a: float, b: float) -> float:
    diff = (a - b) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff
    return diff

MAJOR = {"conjunction":0, "opposition":180, "trine":120, "square":90, "sextile":60}
DEFAULT_ORB = {"default": 5.0, "Sun": 8.0, "Moon": 8.0}

def _angle_diff(a,b):
    return abs((a-b+180) % 360 - 180)

def find_aspects(positions: dict, policy: dict|None=None) -> list[dict]:
    policy = policy or {"types": list(MAJOR.keys()), "orbs": DEFAULT_ORB}
    res = []
    names = list(positions.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            p1, p2 = names[i], names[j]
            lon1, lon2 = positions[p1]["lon"], positions[p2]["lon"]
            d = _angle_diff(lon1, lon2)
            for t in policy["types"]:
                exact = MAJOR[t]
                orb_limit = max(policy["orbs"].get(p1, policy["orbs"]["default"]),
                                policy["orbs"].get(p2, policy["orbs"]["default"]))
                if abs(d - exact) <= orb_limit:
                    res.append({
                        "p1": p1, "p2": p2, "type": t,
                        "orb": round(abs(d-exact), 2),
                        "applying": positions[p1]["speed_lon"] > positions[p2]["speed_lon"],
                    })
    return sorted(res, key=lambda x: x["orb"])

