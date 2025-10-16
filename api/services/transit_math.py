"""Mathematical helpers for transit calculations.

These utilities are intentionally kept free of heavy runtime dependencies so
they can be unit-tested without requiring the Swiss Ephemeris bindings.
"""

from __future__ import annotations


def signed_delta(transit_lon: float, natal_lon: float, aspect_angle: float) -> float:
    """Return the signed difference from the exact aspect in degrees.

    The result is in the range [-180, 180]. Positive values mean the transit
    body has moved past the exact aspect, while negative values indicate the
    aspect is still approaching.
    """

    return ((transit_lon - natal_lon) - aspect_angle + 540.0) % 360.0 - 180.0


def is_applying(
    transit_lon: float,
    transit_speed: float,
    natal_lon: float,
    natal_speed: float,
    aspect_angle: float,
) -> bool:
    """Determine whether a transit aspect is applying.

    A transit is considered *applying* when the angular separation between the
    transit body and the natal body is decreasing toward the exact aspect.
    Conversely, when the separation is growing the transit is *separating*.

    Parameters
    ----------
    transit_lon
        The current ecliptic longitude of the transiting body.
    transit_speed
        The longitudinal speed (degrees per day) of the transiting body.
    natal_lon
        The ecliptic longitude of the natal body.
    natal_speed
        The longitudinal speed of the natal body. This is typically zero for
        natal placements but is included for completeness.
    aspect_angle
        The exact angular difference for the aspect (e.g. 0° for conjunction,
        90° for a square).
    """

    delta = signed_delta(transit_lon, natal_lon, aspect_angle)
    # If already exact (within floating point tolerance), treat as applying so
    # the narrative emphasises the build-up rather than the dissipation.
    if abs(delta) < 1e-6:
        return True

    rate = transit_speed - natal_speed
    if abs(rate) < 1e-6:
        # Bodies moving at an effectively identical pace are not converging.
        return False

    return (delta > 0 and rate < 0) or (delta < 0 and rate > 0)


__all__ = ["is_applying", "signed_delta"]

