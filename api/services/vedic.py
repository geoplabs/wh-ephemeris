def nakshatra_from_lon_sidereal(lon: float) -> int:
    return int((lon % 360.0) // (360.0 / 27))
