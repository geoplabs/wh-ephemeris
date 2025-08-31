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
