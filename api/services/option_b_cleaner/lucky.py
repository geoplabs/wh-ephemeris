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


def _parse_window_times(time_window_str: str) -> tuple[int, int] | None:
    """Parse time window string like '12:35-16:35 UTC' into minute offsets from midnight."""
    import re
    match = re.search(r'(\d+):(\d+)[-–](\d+):(\d+)', time_window_str)
    if match:
        start_min = int(match.group(1)) * 60 + int(match.group(2))
        end_min = int(match.group(3)) * 60 + int(match.group(4))
        return (start_min, end_min)
    return None


def _windows_overlap(window1_str: str, window2_str: str) -> bool:
    """Check if two time windows overlap."""
    w1 = _parse_window_times(window1_str)
    w2 = _parse_window_times(window2_str)
    if not w1 or not w2:
        return False
    
    s1, e1 = w1
    s2, e2 = w2
    
    # Check for any overlap
    return (s1 <= s2 < e1) or (s1 < e2 <= e1) or (s2 <= s1 < e2) or (s2 < e1 <= e2)


def _generate_non_overlapping_window(caution_window_str: str) -> str:
    """Generate a safe lucky window that doesn't overlap with caution window.
    
    Args:
        caution_window_str: The caution window string (e.g., "12:35-16:35 UTC")
        
    Returns:
        A non-overlapping time window string
    """
    caution_times = _parse_window_times(caution_window_str)
    if not caution_times:
        return "10:30 AM - 12:00 PM"  # Fallback to default
    
    caution_start_min, caution_end_min = caution_times
    
    # Try to find a 2-3 hour window outside the caution period
    # Option 1: Early morning (4:00 AM - 6:30 AM) if caution starts after 6:30 AM
    early_start = 4 * 60  # 4:00 AM
    early_end = 6 * 60 + 30  # 6:30 AM
    if early_end <= caution_start_min:
        return f"{early_start // 60:02d}:{early_start % 60:02d}-{early_end // 60:02d}:{early_end % 60:02d} UTC"
    
    # Option 2: Late evening (18:00 - 20:30) if caution ends before 18:00
    evening_start = 18 * 60  # 6:00 PM
    evening_end = 20 * 60 + 30  # 8:30 PM
    if caution_end_min <= evening_start:
        return f"{evening_start // 60:02d}:{evening_start % 60:02d}-{evening_end // 60:02d}:{evening_end % 60:02d} UTC"
    
    # Option 3: Night (21:00 - 23:00) if caution ends before 21:00
    night_start = 21 * 60  # 9:00 PM
    night_end = 23 * 60  # 11:00 PM
    if caution_end_min <= night_start:
        return f"{night_start // 60:02d}:{night_start % 60:02d}-{night_end // 60:02d}:{night_end % 60:02d} UTC"
    
    # If caution spans most of the day, return early morning before caution starts
    if caution_start_min > 2 * 60:  # If caution starts after 2 AM
        safe_start = max(0, caution_start_min - 180)  # 3 hours before caution
        safe_end = max(safe_start + 90, caution_start_min - 30)  # 1.5-2.5 hours window
        return f"{safe_start // 60:02d}:{safe_start % 60:02d}-{safe_end // 60:02d}:{safe_end % 60:02d} UTC"
    
    # Last resort: use a small window right after caution ends
    safe_start = min(23 * 60, caution_end_min + 30)  # 30 min after caution
    safe_end = min(24 * 60 - 1, safe_start + 90)  # 1.5 hour window
    return f"{safe_start // 60:02d}:{safe_start % 60:02d}-{safe_end // 60:02d}:{safe_end % 60:02d} UTC"


def lucky_from_dominant(
    dominant_planet: str, 
    dominant_sign: str, 
    time_window: str | None = None,
    events: Sequence[Mapping[str, Any]] | None = None,
    caution_window_str: str | None = None
):
    """Calculate lucky attributes from dominant transit and events.
    
    Args:
        dominant_planet: The dominant transit planet
        dominant_sign: The dominant sign
        time_window: Optional pre-calculated time window
        events: Optional list of transit events to find exact lucky time
        caution_window_str: Optional caution window to avoid overlap with
        
    Returns:
        Dict with color, time_window, direction, and affirmation
    """
    color = COLOR_BY_SIGN.get(dominant_sign, "Gold")
    direction = DIR_BY_PLANET.get(dominant_planet, "East")
    
    # Calculate time window from supportive events if available
    calculated_window = None
    if events and not time_window:
        # Try all supportive events (score < 0), picking first that doesn't overlap with caution
        # Trust the score - it already accounts for aspect type, planets, orbs, phase, etc.
        
        candidates = []
        for event in events:
            if not isinstance(event, Mapping):
                continue
            
            exact_time = event.get("exact_hit_time_utc")
            if not exact_time or exact_time is None:
                continue
            
            score = float(event.get("score", 0))
            
            # Score < 0 means supportive (system already determined this)
            if score < 0:
                candidates.append((abs(score), event))
        
        # Sort by score and try each candidate
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        for _, event in candidates:
            exact_time = event.get("exact_hit_time_utc")
            transit_planet = event.get("transit_body", dominant_planet)
            test_window = _calculate_lucky_window_from_exact_time(exact_time, transit_planet)
            
            if test_window:
                # Check if it overlaps with caution window
                if caution_window_str and _windows_overlap(test_window, caution_window_str):
                    continue  # Try next candidate
                
                # Found a non-overlapping window!
                calculated_window = test_window
                break
    
    # Determine final window, but check default for overlap
    if time_window:
        window = time_window
    elif calculated_window:
        window = calculated_window
    else:
        # Using default - check if it overlaps with caution window
        if caution_window_str and _windows_overlap(DEFAULT_TIME_WINDOW, caution_window_str):
            # Default overlaps with caution - generate a safe non-overlapping window
            window = _generate_non_overlapping_window(caution_window_str)
        else:
            window = DEFAULT_TIME_WINDOW
    
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
