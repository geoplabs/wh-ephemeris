"""High-level window resolution with netting strategy."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .caution_windows import compute_caution_windows


def resolve_windows_with_netting(
    events: Sequence[Mapping[str, Any]],
    netting_threshold: float = 0.5,
    support_threshold_soft: float = 0.35,
    support_threshold_strong: float = 0.70
) -> dict[str, dict[str, Any] | None]:
    """Resolve caution and lucky windows using netting strategy.
    
    Strategy:
    1. Compute all windows (friction + support) from events
    2. Separate friction (positive scores) from support (negative scores)
    3. Check for overlaps
    4. Apply netting in overlapping regions
    5. Return top 2 windows by |score|
    
    Args:
        events: Transit events
        netting_threshold: Threshold for mixed/neutral classification
        support_threshold_soft: Support ratio for softening caution (35%)
        support_threshold_strong: Support ratio for downgrading to gentle note (70%)
        
    Returns:
        Dict with 'caution_window' and 'lucky_window' (either can be None)
    """
    # Get all windows from compute_caution_windows
    all_windows = compute_caution_windows(events)
    
    if not all_windows:
        return {"caution_window": None, "lucky_window": None}
    
    # Separate friction and support windows
    friction_windows = []
    support_windows = []
    
    for window in all_windows:
        score = window.get("score", 0)
        severity = window.get("severity", "")
        
        if score > 0 or severity in {"Caution", "High Caution", "Gentle Note"}:
            friction_windows.append(window)
        elif score < 0 or severity in {"Support", "Insight"}:
            support_windows.append(window)
    
    # Process overlaps with netting
    result_windows: list[dict[str, Any]] = []
    processed_support: set[int] = set()
    
    for friction in friction_windows:
        f_start, f_end = _parse_time_window(friction.get("time_window_utc", ""))
        if f_start is None or f_end is None:
            # Can't process - add as-is
            result_windows.append(friction)
            continue
        
        # Find overlapping support windows
        overlapping_support = []
        for s_idx, support in enumerate(support_windows):
            if s_idx in processed_support:
                continue
            
            s_start, s_end = _parse_time_window(support.get("time_window_utc", ""))
            if s_start is None or s_end is None:
                continue
            
            overlap_minutes = _compute_overlap_minutes(f_start, f_end, s_start, s_end)
            if overlap_minutes > 0:
                overlapping_support.append((support, s_idx, overlap_minutes))
        
        if not overlapping_support:
            # No overlap - add friction as caution
            result_windows.append(_format_as_caution(friction))
        else:
            # Apply netting
            friction_score = abs(friction.get("score", 0))
            support_score = sum(abs(s[0].get("score", 0)) for s in overlapping_support)
            net_score = friction.get("score", 0) + sum(s[0].get("score", 0) for s in overlapping_support)
            
            support_ratio = support_score / friction_score if friction_score > 0 else 1.0
            
            # Determine label based on netting
            if abs(net_score) <= netting_threshold:
                label = "Mixed"
                note = "Support within tension—clarify, proceed in small steps."
            elif net_score > netting_threshold:
                # Still friction, but check support ratio
                if support_ratio >= support_threshold_strong:
                    label = "Gentle Note"
                    note = "Light friction with strong support—proceed thoughtfully."
                elif support_ratio >= support_threshold_soft:
                    label = "Caution"
                    note = "Tension with support—clarify, proceed small."
                else:
                    # Check for tight angle aspects
                    drivers = friction.get("drivers", [])
                    if _has_tight_angle_aspect(drivers):
                        label = "Caution"
                        note = "Expect bumps in this window—clarify, pause, then decide."
                    elif _has_wide_moon_orb(drivers):
                        label = "Gentle Note"
                        note = "Minor friction—stay alert but proceed."
                    else:
                        label = "Caution"
                        note = friction.get("note", "Expect bumps in this window—clarify, pause, then decide.")
            else:
                # Support wins
                label = "Support"
                note = "Supportive window with minor friction—trust your momentum."
            
            # Create netted window
            netted = {
                "time_window": friction.get("time_window_utc", ""),
                "label": label,
                "note": note,
                "net_score": round(net_score, 2),
                "friction_score": round(friction.get("score", 0), 2),
                "support_score": round(-support_score, 2),
                "support_ratio": round(support_ratio, 2),
                "drivers": friction.get("drivers", []) + [s[0].get("drivers", [[]])[0] for s in overlapping_support if s[0].get("drivers")],
            }
            result_windows.append(netted)
            
            # Mark support windows as processed
            for _, s_idx, _ in overlapping_support:
                processed_support.add(s_idx)
    
    # Add non-overlapping support windows
    for s_idx, support in enumerate(support_windows):
        if s_idx not in processed_support:
            result_windows.append(_format_as_support(support))
    
    # Sort by absolute score and take top 2
    result_windows.sort(key=lambda w: abs(w.get("net_score", w.get("score", 0))), reverse=True)
    top_windows = result_windows[:2]
    
    # Assign to caution and lucky (MUST be different windows)
    caution_window = None
    lucky_window = None
    used_indices = set()
    
    # First pass: assign by preferred labels
    for idx, window in enumerate(top_windows):
        label = window.get("label", "")
        score = window.get("net_score", window.get("score", 0))
        
        # Assign caution windows
        if caution_window is None and label in {"Caution", "High Caution", "Gentle Note"}:
            caution_window = {
                "time_window": window.get("time_window", ""),
                "note": window.get("note", ""),
            }
            used_indices.add(idx)
        # Assign support windows
        elif lucky_window is None and label in {"Support", "Insight"}:
            lucky_window = {
                "time_window": window.get("time_window", ""),
                "note": window.get("note", ""),
            }
            used_indices.add(idx)
    
    # Second pass: fill remaining slots with unused windows
    for idx, window in enumerate(top_windows):
        if idx in used_indices:
            continue  # Already used
            
        label = window.get("label", "")
        score = window.get("net_score", window.get("score", 0))
        
        if caution_window is None and score >= 0:
            caution_window = {
                "time_window": window.get("time_window", ""),
                "note": window.get("note", ""),
            }
            used_indices.add(idx)
        elif lucky_window is None and score < 0:
            lucky_window = {
                "time_window": window.get("time_window", ""),
                "note": window.get("note", ""),
            }
            used_indices.add(idx)
    
    return {
        "caution_window": caution_window,
        "lucky_window": lucky_window,
        "all_windows": top_windows  # For debugging/advanced use
    }


def _parse_time_window(time_str: str) -> tuple[int | None, int | None]:
    """Parse time window like '12:35-16:35 UTC' into minute offsets."""
    import re
    match = re.search(r'(\d+):(\d+)[-–](\d+):(\d+)', time_str)
    if match:
        start_min = int(match.group(1)) * 60 + int(match.group(2))
        end_min = int(match.group(3)) * 60 + int(match.group(4))
        return (start_min, end_min)
    return (None, None)


def _compute_overlap_minutes(start1: int, end1: int, start2: int, end2: int) -> int:
    """Compute overlap in minutes."""
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    return max(0, overlap_end - overlap_start)


def _has_tight_angle_aspect(drivers: list[dict[str, Any]]) -> bool:
    """Check if any driver is tight applying aspect to an angle."""
    angle_names = {"ascendant", "midheaven", "descendant", "ic", "asc", "mc", "dc"}
    hard_aspects = {"square", "opposition"}
    
    for driver in drivers:
        natal_body = str(driver.get("natal_body", "")).lower()
        aspect = str(driver.get("aspect", "")).lower()
        orb = float(driver.get("orb", 999))
        phase = str(driver.get("phase", "")).lower()
        
        if natal_body in angle_names and aspect in hard_aspects and orb <= 1.0 and "applying" in phase:
            return True
    
    return False


def _has_wide_moon_orb(drivers: list[dict[str, Any]]) -> bool:
    """Check if primary driver is Moon with wide orb."""
    if not drivers:
        return False
    
    top = drivers[0]
    transit_body = str(top.get("transit_body", "")).lower()
    orb = float(top.get("orb", 0))
    
    return transit_body == "moon" and orb > 3.0


def _format_as_caution(window: dict[str, Any]) -> dict[str, Any]:
    """Format window as caution."""
    return {
        "time_window": window.get("time_window_utc", ""),
        "label": window.get("severity", "Caution"),
        "note": window.get("note", "Expect bumps in this window—clarify, pause, then decide."),
        "net_score": window.get("score", 0),
        "score": window.get("score", 0),
        "drivers": window.get("drivers", []),
    }


def _format_as_support(window: dict[str, Any]) -> dict[str, Any]:
    """Format window as support/lucky."""
    return {
        "time_window": window.get("time_window_utc", ""),
        "label": "Support",
        "note": window.get("note", "Supportive window—trust your momentum and take action."),
        "net_score": window.get("score", 0),
        "score": window.get("score", 0),
        "drivers": window.get("drivers", []),
    }


__all__ = ["resolve_windows_with_netting"]

