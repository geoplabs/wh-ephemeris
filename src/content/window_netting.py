"""Window overlap detection and netting logic for caution/lucky windows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence


@dataclass
class TimeWindow:
    """Represents a time window with score and contributors."""
    start_utc: datetime
    end_utc: datetime
    score: float  # Positive = caution/friction, Negative = support/lucky
    contributors: list[Mapping[str, Any]]
    window_type: str  # "caution" or "support"
    
    @property
    def start_minutes(self) -> int:
        """Minutes from midnight UTC."""
        return self.start_utc.hour * 60 + self.start_utc.minute
    
    @property
    def end_minutes(self) -> int:
        """Minutes from midnight UTC."""
        return self.end_utc.hour * 60 + self.end_utc.minute


def compute_overlap(w1: TimeWindow, w2: TimeWindow) -> int:
    """Compute overlap in minutes between two windows.
    
    Returns:
        Number of overlapping minutes (0 if no overlap)
    """
    overlap_start = max(w1.start_minutes, w2.start_minutes)
    overlap_end = min(w1.end_minutes, w2.end_minutes)
    return max(0, overlap_end - overlap_start)


def has_tight_angle_aspect(contributors: Sequence[Mapping[str, Any]]) -> bool:
    """Check if any contributor is a tight applying aspect to an angle."""
    angle_names = {"ascendant", "midheaven", "descendant", "ic", "asc", "mc", "dc"}
    hard_aspects = {"square", "opposition"}
    
    for contrib in contributors:
        natal_body = str(contrib.get("natal_body", "")).lower()
        aspect = str(contrib.get("aspect", "")).lower()
        orb = float(contrib.get("orb", 999))
        phase = str(contrib.get("phase", "")).lower()
        
        if natal_body in angle_names and aspect in hard_aspects and orb <= 1.0 and "applying" in phase:
            return True
    
    return False


def has_wide_moon_orb(contributors: Sequence[Mapping[str, Any]]) -> bool:
    """Check if primary friction driver is Moon with wide orb."""
    if not contributors:
        return False
    
    top = contributors[0]
    transit_body = str(top.get("transit_body", "")).lower()
    orb = float(top.get("orb", 0))
    
    return transit_body == "moon" and orb > 3.0


def apply_netting_strategy(
    caution_windows: list[TimeWindow],
    support_windows: list[TimeWindow],
    threshold: float = 0.5
) -> list[dict[str, Any]]:
    """Apply netting strategy to resolve overlapping windows.
    
    Args:
        caution_windows: Windows with friction (positive scores)
        support_windows: Windows with support (negative scores)
        threshold: Threshold for determining mixed/neutral windows
        
    Returns:
        List of final windows with proper labels
    """
    final_windows: list[dict[str, Any]] = []
    processed_support: set[int] = set()
    
    # Process each caution window
    for c_idx, caution in enumerate(caution_windows):
        overlapping_support: list[tuple[TimeWindow, int]] = []
        
        # Find overlapping support windows
        for s_idx, support in enumerate(support_windows):
            if s_idx in processed_support:
                continue
            
            overlap_minutes = compute_overlap(caution, support)
            if overlap_minutes > 0:
                overlapping_support.append((support, overlap_minutes))
        
        if not overlapping_support:
            # No overlap - add caution window as-is
            final_windows.append(_format_window(caution, "Caution"))
        else:
            # Handle overlap with netting
            total_support_score = sum(s[0].score for s in overlapping_support)  # negative values
            net_score = caution.score + total_support_score  # friction + support
            
            # Calculate support ratio
            friction_magnitude = abs(caution.score)
            support_magnitude = abs(total_support_score)
            
            if friction_magnitude > 0:
                support_ratio = support_magnitude / friction_magnitude
            else:
                support_ratio = 1.0
            
            # Determine label based on net score and support ratio
            if abs(net_score) <= threshold:
                # Mixed/Neutral
                label = "Mixed"
                note = "Support within tension—clarify, proceed in small steps."
            elif net_score > threshold:
                # Still caution, but check ratios
                if support_ratio >= 0.70:
                    label = "Gentle Note"
                    note = "Light friction with strong support—proceed thoughtfully."
                elif support_ratio >= 0.35:
                    label = "Caution"
                    note = "Tension with support—clarify, proceed small."
                else:
                    # Check special conditions
                    if has_tight_angle_aspect(caution.contributors):
                        label = "Caution"
                        note = "Expect bumps in this window—clarify, pause, then decide."
                    elif has_wide_moon_orb(caution.contributors):
                        label = "Gentle Note"
                        note = "Minor friction—stay alert but proceed."
                    else:
                        label = "Caution"
                        note = "Expect bumps in this window—clarify, pause, then decide."
            else:
                # Net score is negative - support wins
                label = "Support"
                note = "Supportive window with minor friction—trust your momentum."
            
            # Merge contributors
            all_contributors = list(caution.contributors) + [s[0].contributors[0] for s in overlapping_support]
            
            final_windows.append({
                "start_utc": caution.start_utc.isoformat().replace("+00:00", "Z"),
                "end_utc": caution.end_utc.isoformat().replace("+00:00", "Z"),
                "time_window": f"{caution.start_utc.strftime('%H:%M')}-{caution.end_utc.strftime('%H:%M')} UTC",
                "label": label,
                "net_score": round(net_score, 2),
                "friction_score": round(caution.score, 2),
                "support_score": round(total_support_score, 2),
                "support_ratio": round(support_ratio, 2),
                "note": note,
                "drivers": all_contributors[:3]
            })
            
            # Mark overlapping support windows as processed
            for support, _ in overlapping_support:
                idx = support_windows.index(support)
                processed_support.add(idx)
    
    # Add non-overlapping support windows as "lucky"
    for s_idx, support in enumerate(support_windows):
        if s_idx not in processed_support:
            final_windows.append(_format_window(support, "Support"))
    
    # Sort by absolute net score and return top 2
    final_windows.sort(key=lambda w: abs(w.get("net_score", w.get("score", 0))), reverse=True)
    return final_windows[:2]


def _format_window(window: TimeWindow, label: str) -> dict[str, Any]:
    """Format a window without netting."""
    if label == "Caution":
        note = "Expect bumps in this window—clarify, pause, then decide."
    else:
        note = "Supportive window—trust your momentum and take action."
    
    return {
        "start_utc": window.start_utc.isoformat().replace("+00:00", "Z"),
        "end_utc": window.end_utc.isoformat().replace("+00:00", "Z"),
        "time_window": f"{window.start_utc.strftime('%H:%M')}-{window.end_utc.strftime('%H:%M')} UTC",
        "label": label,
        "score": round(window.score, 2),
        "net_score": round(window.score, 2),
        "note": note,
        "drivers": window.contributors[:3]
    }


__all__ = ["TimeWindow", "apply_netting_strategy", "compute_overlap"]

