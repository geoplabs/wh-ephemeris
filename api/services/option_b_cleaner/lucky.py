from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence
from .mappings import COLOR_BY_SIGN, DIR_BY_PLANET, DEFAULT_TIME_WINDOW


def _calculate_lucky_window_from_exact_time(exact_time_utc: str, planet: str) -> str:
    """Calculate lucky time window around exact hit time for supportive aspects.
    
    Args:
        exact_time_utc: ISO format UTC time like "2025-10-29T14:30:00Z"
        planet: Transit planet name for context labels
        
    Returns:
        Formatted time window like "14:00-16:00 UTC (supportive peak)"
    """
    try:
        # Parse the ISO format time
        exact_time_str = exact_time_utc.replace("Z", "+00:00")
        exact_dt = datetime.fromisoformat(exact_time_str)
        
        # Calculate window around exact time based on planet
        if planet.lower() == "moon":
            # Moon moves fast: ±1 hour window
            start = exact_dt - timedelta(hours=1)
            end = exact_dt + timedelta(hours=1)
            label = "lunar peak"
        elif planet.lower() in {"mercury", "venus"}:
            # Mercury/Venus: ±1.5 hours
            start = exact_dt - timedelta(hours=1, minutes=30)
            end = exact_dt + timedelta(hours=1, minutes=30)
            label = "supportive peak"
        elif planet.lower() == "sun":
            # Sun: ±2 hours
            start = exact_dt - timedelta(hours=2)
            end = exact_dt + timedelta(hours=2)
            label = "solar peak"
        elif planet.lower() == "jupiter":
            # Jupiter: broader ±3 hours
            start = exact_dt - timedelta(hours=3)
            end = exact_dt + timedelta(hours=3)
            label = "expansive window"
        else:
            # Default: ±2 hours
            start = exact_dt - timedelta(hours=2)
            end = exact_dt + timedelta(hours=2)
            label = "fortunate window"
        
        # Format as UTC times
        start_str = start.strftime("%H:%M")
        end_str = end.strftime("%H:%M")
        return f"{start_str}–{end_str} UTC ({label})"
    except (ValueError, AttributeError):
        # If parsing fails, return None to use default
        return None


def _find_best_supportive_event(events: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    """Find the most supportive event with exact_hit_time_utc for lucky window calculation.
    
    Prioritizes:
    1. Supportive aspects (trine, sextile, benefic conjunctions)
    2. Has exact_hit_time_utc field
    3. Highest absolute score
    """
    supportive_aspects = {"trine", "sextile"}
    benefic_bodies = {"venus", "jupiter"}
    
    candidates = []
    for event in events:
        if not isinstance(event, Mapping):
            continue
        
        # Check if event has exact hit time
        exact_time = event.get("exact_hit_time_utc")
        if not exact_time or exact_time is None:
            continue
        
        aspect = (event.get("aspect") or "").lower()
        transit_body = (event.get("transit_body") or "").lower()
        score = float(event.get("score", 0))
        
        # Identify supportive events
        is_supportive = False
        if aspect in supportive_aspects:
            is_supportive = True
        elif aspect == "conjunction" and transit_body in benefic_bodies:
            is_supportive = True
        
        if is_supportive:
            candidates.append((abs(score), event))
    
    # Return highest scoring supportive event
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    
    return None


def lucky_from_dominant(
    dominant_planet: str, 
    dominant_sign: str, 
    time_window: str | None = None,
    events: Sequence[Mapping[str, Any]] | None = None
):
    """Calculate lucky attributes from dominant transit and events.
    
    Args:
        dominant_planet: The dominant transit planet
        dominant_sign: The dominant sign
        time_window: Optional pre-calculated time window
        events: Optional list of transit events to find exact lucky time
        
    Returns:
        Dict with color, time_window, direction, and affirmation
    """
    color = COLOR_BY_SIGN.get(dominant_sign, "Gold")
    direction = DIR_BY_PLANET.get(dominant_planet, "East")
    
    # Calculate time window from supportive events if available
    calculated_window = None
    if events and not time_window:
        best_event = _find_best_supportive_event(events)
        if best_event:
            exact_time = best_event.get("exact_hit_time_utc")
            transit_planet = best_event.get("transit_body", dominant_planet)
            if exact_time:
                calculated_window = _calculate_lucky_window_from_exact_time(exact_time, transit_planet)
    
    window = time_window or calculated_window or DEFAULT_TIME_WINDOW
    
    affirmation = {
        "Sun": "I act with clarity and purpose.",
        "Venus": "I attract harmony and support.",
        "Mars": "I move with courage and focus.",
        "Jupiter": "I welcome growth and opportunity.",
        "Saturn": "I honor structure and steady progress.",
        "Moon": "I listen to my feelings with care.",
        "Pluto": "My inner power is steady and calm.",
    }.get(dominant_planet, "I choose what strengthens me.")
    
    return {
        "color": color,
        "time_window": window,
        "direction": direction,
        "affirmation": affirmation,
    }
