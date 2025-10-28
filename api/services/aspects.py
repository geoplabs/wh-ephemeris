
MAJOR = {
    "conjunction": 0,
    "opposition": 180,
    "square": 90,
    "trine": 120,
    "sextile": 60,
    "quincunx": 150,
}

ASPECT_ALIASES = {"inconjunct": "quincunx"}

DEFAULT_ORB = {"default": 5.0, "Sun": 8.0, "Moon": 8.0}


def canonical_aspect(name: str) -> str:
    return ASPECT_ALIASES.get(name, name)


def aspect_angle(name: str) -> float | None:
    canonical = canonical_aspect(name)
    return MAJOR.get(canonical)


def _angle_diff(a: float, b: float) -> float:
    """Return the minimal angular distance between two longitudes."""

    return abs((a - b + 180) % 360 - 180)

def find_aspects(positions: dict, policy: dict|None=None) -> list[dict]:
    policy = policy or {"types": list(MAJOR.keys()), "orbs": DEFAULT_ORB}
    res = []
    names = list(positions.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            p1, p2 = names[i], names[j]
            lon1, lon2 = positions[p1]["lon"], positions[p2]["lon"]
            d = _angle_diff(lon1, lon2)
            matched: set[str] = set()
            for t in policy["types"]:
                canonical = canonical_aspect(t)
                if canonical in matched:
                    continue
                exact = MAJOR.get(canonical)
                if exact is None:
                    continue
                orb_limit = max(policy["orbs"].get(p1, policy["orbs"]["default"]),
                                policy["orbs"].get(p2, policy["orbs"]["default"]))
                if abs(d - exact) <= orb_limit:
                    matched.add(canonical)
                    res.append({
                        "p1": p1,
                        "p2": p2,
                        "type": canonical,
                        "orb": round(abs(d-exact), 2),
                        "applying": positions[p1]["speed_lon"] > positions[p2]["speed_lon"],
                    })
    return sorted(res, key=lambda x: x["orb"])

