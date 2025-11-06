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
    
    Uses score-based filtering (score < 0 = supportive).
    
    Prioritizes:
    1. Score < 0 (supportive - trust the scoring system)
    2. Has exact_hit_time_utc field
    3. Highest absolute score
    """
    candidates = []
    for event in events:
        if not isinstance(event, Mapping):
            continue
        
        exact_time = event.get("exact_hit_time_utc")
        if not exact_time or exact_time is None:
            continue
        
        score = float(event.get("score", 0))
        
        # Score < 0 means supportive (trust the scoring system)
        if score < 0:
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


def _intervals(window: tuple[int, int]) -> list[tuple[int, int]]:
    """Split a window into intervals, handling midnight wrap-around.
    
    Args:
        window: (start_min, end_min) where minutes are from midnight [0, 1440)
        
    Returns:
        List of intervals. Non-wrapping: [(start, end)]. 
        Wrapping (e.g., 22:00-02:00): [(start, 1440), (0, end)]
    
    Example:
        (1320, 120) -> [(1320, 1440), (0, 120)]  # 22:00-02:00 wraps
        (300, 600)  -> [(300, 600)]              # 05:00-10:00 doesn't wrap
    """
    start, end = window
    if end >= start:
        # Normal case: no wrap-around
        return [(start, end)]
    else:
        # Wrap-around: split into [start, midnight) and [midnight, end)
        return [(start, 1440), (0, end)]


def _windows_overlap(window1_str: str, window2_str: str) -> bool:
    """Check if two time windows overlap, handling midnight wrap-around.
    
    Args:
        window1_str: Time window string like '22:00-02:00 UTC' or '12:35-16:35 UTC'
        window2_str: Time window string like '01:00-05:00 UTC'
        
    Returns:
        True if windows overlap, False otherwise
    """
    w1 = _parse_window_times(window1_str)
    w2 = _parse_window_times(window2_str)
    if not w1 or not w2:
        return False
    
    # Get intervals for each window (handles wrap-around)
    intervals1 = _intervals(w1)
    intervals2 = _intervals(w2)
    
    # Check if any pair of intervals overlap
    for (s1, e1) in intervals1:
        for (s2, e2) in intervals2:
            # Overlap exists if intervals intersect
            if s1 < e2 and s2 < e1:
                return True
    
    return False


def _is_all_day_caution(caution_window_str: str) -> bool:
    """Check if caution window is effectively all-day (>=12 hours or contains 'all day').
    
    Args:
        caution_window_str: Caution window string like "All day (general caution)" or "05:00-20:00 UTC"
        
    Returns:
        True if all-day or >= 12 hours
    """
    if not caution_window_str:
        return False
    
    # Check for explicit "all day" text
    if "all day" in caution_window_str.lower():
        return True
    
    # Parse and check duration
    parsed = _parse_window_times(caution_window_str)
    if not parsed:
        return False
    
    start, end = parsed
    # Handle wrap-around
    if end < start:
        duration = (1440 - start) + end
    else:
        duration = end - start
    
    # >= 12 hours (720 minutes) is considered all-day
    return duration >= 720


def _calculate_micro_window(exact_time_utc: str, planet: str, minutes: int = 45) -> str | None:
    """Calculate a micro lucky window (tighter than normal) around exact hit time.
    
    Used when caution window is all-day to find narrow supportive peaks.
    
    Args:
        exact_time_utc: ISO format UTC time like "2025-10-29T14:30:00Z"
        planet: Transit planet name (for labeling)
        minutes: Half-width of micro window (±minutes)
        
    Returns:
        Formatted micro window like "14:00-15:15 UTC (micro peak)"
    """
    try:
        from datetime import datetime, timedelta
        exact_time_str = exact_time_utc.replace("Z", "+00:00")
        exact_dt = datetime.fromisoformat(exact_time_str)
        
        # Create tight window around exact time
        start = exact_dt - timedelta(minutes=minutes)
        end = exact_dt + timedelta(minutes=minutes)
        
        # Format as UTC times
        start_str = start.strftime("%H:%M")
        end_str = end.strftime("%H:%M")
        return f"{start_str}–{end_str} UTC (micro peak)"
    except (ValueError, AttributeError):
        return None


def _generate_non_overlapping_window(caution_window_str: str) -> str:
    """Generate a safe lucky window that doesn't overlap with caution window.
    
    Handles midnight wrap-around caution windows correctly.
    
    Args:
        caution_window_str: The caution window string (e.g., "12:35-16:35 UTC" or "22:00-02:00 UTC")
        
    Returns:
        A non-overlapping time window string in 24-hour UTC format
    """
    parsed = _parse_window_times(caution_window_str)
    if not parsed:
        return "10:30-12:00 UTC"  # Fixed: consistent UTC format
    
    # Split caution into intervals (handles wrap-around)
    blocks = _intervals(parsed)
    blocked = []
    for s, e in blocks:
        blocked.append((s, e))
    
    # Build free intervals over [0, 1440) minutes
    cursor = 0
    free = []
    for (s, e) in sorted(blocked):
        if cursor < s:
            free.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < 1440:
        free.append((cursor, 1440))
    
    # Prefer daytime hours: 06:00–22:00 (360-1320 minutes)
    preferred = [(6 * 60, 22 * 60)]
    
    def pick_window(pools, min_len=90, target_len=120):
        """Find a window of target_len (or at least min_len) from available pools."""
        for (fs, fe) in pools:
            length = fe - fs
            if length >= min_len:
                # Center the window within the free block
                start = fs + max(0, (length - target_len) // 2)
                end = min(fe, start + target_len)
                if end - start >= min_len:
                    return f"{start // 60:02d}:{start % 60:02d}-{end // 60:02d}:{end % 60:02d} UTC"
        return None
    
    # Intersect free blocks with preferred daytime hours
    preferred_free = []
    for (fs, fe) in free:
        for (ps, pe) in preferred:
            s = max(fs, ps)
            e = min(fe, pe)
            if s < e:
                preferred_free.append((s, e))
    
    # Try preferred daytime first, then any free block
    win = pick_window(preferred_free) or pick_window(free)
    return win or "10:30-12:00 UTC"


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
    # Normalize planet and sign to Title case for consistent mapping lookups
    p_key = (dominant_planet or "").strip().title()
    s_key = (dominant_sign or "").strip().title()
    
    color = COLOR_BY_SIGN.get(s_key, "Gold")
    direction = DIR_BY_PLANET.get(p_key, "East")
    
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
    }.get(p_key, "I choose what strengthens me.")
    
    return {
        "color": color,
        "time_window": window,
        "direction": direction,
        "affirmation": affirmation,
    }
